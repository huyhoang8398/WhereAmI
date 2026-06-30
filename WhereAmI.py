import sublime
import sublime_plugin

BAR_WIDTH = 15
ANIM_INTERVAL_MS = 90

FILLED_CHAR = "█"
EMPTY_CHAR = "░"
SHIMMER_CHARS = "█▓▒"  # leading edge bright, fading darker behind it
ANIM_STEPS = 22  # frames for the shimmer to sweep one full pass (start -> end)

# Default when no setting is present. Override per-user by creating
# Packages/User/WhereAmI.sublime-settings with
# { "animated": false } to fall back to the original plain, non-animated bar.
ANIMATED = True
SETTINGS_FILE = "WhereAmI.sublime-settings"
SETTINGS_KEY = "animated"


def is_animated():
    settings = sublime.load_settings(SETTINGS_FILE)
    return settings.get(SETTINGS_KEY, ANIMATED)


class CursorProgressBar(sublime_plugin.EventListener):
    active_views = {}  # view_id -> view
    anim_offset = {}  # view_id -> int (animation frame)

    def update_status(self, view):
        if not view or not view.sel():
            return
        sel = view.sel()[0]
        row, _ = view.rowcol(sel.b)
        total_lines = view.rowcol(view.size())[0] + 1
        progress = row / max(1, total_lines - 1)
        percent = int(progress * 100)
        filled = int(progress * BAR_WIDTH)

        vid = view.id()
        self.active_views[vid] = view

        if is_animated():
            self.render_animated(view, filled, percent, row, total_lines)
            if vid not in self.anim_offset:
                self.anim_offset[vid] = 0
                self.animate(vid)
        else:
            self.cleanup(vid)
            self.render_static(view, filled, percent, row, total_lines)

    def render_static(self, view, filled, percent, row, total_lines):
        bar = FILLED_CHAR * filled + EMPTY_CHAR * (BAR_WIDTH - filled)
        status = f"[{bar}] {percent}% • Ln {row + 1}/{total_lines}"
        view.set_status("cursor_progress", status)

    def render_animated(self, view, filled, percent, row, total_lines):
        vid = view.id()
        offset = self.anim_offset.get(vid, 0)

        # Shimmer head sweeps left->right across the *full* bar width in a
        # one-directional loop (wraps instantly at the end), trailing a short
        # fade behind it. Everything else in the filled region is solid.
        cycle = offset % ANIM_STEPS
        shimmer_pos = (cycle / ANIM_STEPS) * (BAR_WIDTH - 1)

        bar_chars = []
        for i in range(BAR_WIDTH):
            if i >= filled:
                bar_chars.append(EMPTY_CHAR)
                continue
            dist = shimmer_pos - i
            if 0 <= dist < len(SHIMMER_CHARS):
                bar_chars.append(SHIMMER_CHARS[int(dist)])
            else:
                bar_chars.append(FILLED_CHAR)
        bar = "".join(bar_chars)

        status = f"[{bar}] {percent}% • Ln {row + 1}/{total_lines}"
        view.set_status("cursor_progress", status)

    def animate(self, vid):
        if not is_animated():
            self.cleanup(vid)
            return

        view = self.active_views.get(vid)
        if not view or not view.is_valid():
            self.cleanup(vid)
            return

        self.anim_offset[vid] = (self.anim_offset.get(vid, 0) + 1) % ANIM_STEPS

        sel = view.sel()
        if sel:
            s = sel[0]
            row, _ = view.rowcol(s.b)
            total_lines = view.rowcol(view.size())[0] + 1
            progress = row / max(1, total_lines - 1)
            percent = int(progress * 100)
            filled = int(progress * BAR_WIDTH)
            self.render_animated(view, filled, percent, row, total_lines)

        sublime.set_timeout(lambda: self.animate(vid), ANIM_INTERVAL_MS)

    def cleanup(self, vid):
        self.anim_offset.pop(vid, None)
        self.active_views.pop(vid, None)

    def on_selection_modified_async(self, view):
        self.update_status(view)

    def on_activated_async(self, view):
        self.update_status(view)

    def on_modified_async(self, view):
        self.update_status(view)

    def on_close(self, view):
        self.cleanup(view.id())
