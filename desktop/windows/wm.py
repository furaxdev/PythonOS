"""PythonOS window manager — the kwin-equivalent compositor/WM piece of
the desktop session.

Architecture decision (see docs/DESKTOP.md and docs/WINDOWS.md): writing
a Wayland compositor from scratch (buffer sharing, DRM/KMS, the full
wayland protocol) is out of reach for a from-scratch reimplementation in
reasonable time. Real X11 window management, via the plain X protocol
(python-xlib — pure Python, no C extension, fits the Python-first
principle), is a well-understood, tractable problem and gives PythonOS an
actually-working window manager today: it becomes the X server's
SubstructureRedirect client, gets MapRequest/UnmapNotify/DestroyNotify
events for every client window, and is the thing that decides whether and
where a window appears. This is genuinely how every X11 WM (including
KDE's own X11 mode, before kwin moved to being Wayland-first) is built.
A Wayland backend is future work, not faked here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from Xlib import X, display
from Xlib.error import BadWindow

TITLEBAR_HEIGHT = 26
BUTTON_SIZE = 14
BUTTON_MARGIN = 6
BUTTON_GAP = 6

TITLEBAR_BG = (0x31, 0x36, 0x3B)
TITLEBAR_TEXT = (0xEF, 0xF0, 0xF1)
CLOSE_COLOR = (0xED, 0x1C, 0x24)
MINIMIZE_COLOR = (0xF6, 0x74, 0x00)
MAXIMIZE_COLOR = (0x27, 0xAE, 0x60)


class WindowManagerError(Exception):
    pass


@dataclass
class ManagedWindow:
    client_id: int
    frame_id: int
    title: str
    minimized: bool = False
    maximized: bool = False
    normal_geometry: tuple[int, int, int, int] | None = None  # x, y, w, h (client size)


class WindowManager:
    """A real reparenting X11 window manager: every client window gets
    wrapped in a decorated frame (titlebar + close/minimize/maximize
    buttons), exactly like a traditional X11 WM (KDE's own kwin in X11
    mode works the same way — create a frame, reparent the client into
    it, draw decorations, forward button clicks to WM actions). Takes
    over SubstructureRedirect on the root window so it sees every
    client's map/unmap/destroy, and notifies callbacks so the panel's
    TaskManagerWidget can reflect real windows instead of manually-added
    ones.
    """

    def __init__(
        self,
        display_name: str | None = None,
        on_window_opened: Callable[[int, str], None] | None = None,
        on_window_closed: Callable[[int], None] | None = None,
    ):
        self.on_window_opened = on_window_opened or (lambda wid, title: None)
        self.on_window_closed = on_window_closed or (lambda wid: None)
        self.windows: dict[int, ManagedWindow] = {}
        self._frame_to_client: dict[int, int] = {}

        self._display = display.Display(display_name)
        self._screen = self._display.screen()
        self._root = self._screen.root
        self._colormap = self._screen.default_colormap

        self._pixel_cache: dict[tuple[int, int, int], int] = {}
        self._gc = None  # created lazily once we know the root's depth/visual

    def start(self) -> None:
        """Become the window manager. Raises WindowManagerError if another
        WM already owns SubstructureRedirect on this display (X allows
        only one). X delivers that as an asynchronous BadAccess error, not
        a Python exception from the call itself, so it's caught via the
        request's onerror callback."""
        errors: list[Exception] = []
        self._root.change_attributes(
            onerror=lambda err, req: errors.append(err),
            event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
        )
        self._display.sync()
        if errors:
            raise WindowManagerError(f"another window manager is already running: {errors[0]}")

    def _pixel(self, rgb: tuple[int, int, int]) -> int:
        if rgb not in self._pixel_cache:
            r, g, b = rgb
            color = self._colormap.alloc_color(r * 257, g * 257, b * 257)
            self._pixel_cache[rgb] = color.pixel
        return self._pixel_cache[rgb]

    def _window_title(self, window_id: int) -> str:
        try:
            win = self._display.create_resource_object("window", window_id)
            name = win.get_wm_name()
            return name or f"window-{window_id}"
        except (BadWindow, Exception):
            return f"window-{window_id}"

    def process_pending_events(self) -> int:
        """Drain and handle whatever X events are already queued. Returns
        the number handled. Non-blocking, so it can be called from a poll
        loop alongside system/init-style service supervision."""
        handled = 0
        while self._display.pending_events():
            event = self._display.next_event()
            self._handle_event(event)
            handled += 1
        return handled

    def _handle_event(self, event) -> None:
        if event.type == X.MapRequest:
            self._decorate_and_map(event.window)
        elif event.type in (X.UnmapNotify, X.DestroyNotify):
            self._handle_client_gone(event.window.id)
        elif event.type == X.Expose and event.window.id in self._frame_to_client_rev():
            self._draw_titlebar(event.window.id)
        elif event.type == X.ButtonPress:
            self._handle_button_press(event)

    def _frame_to_client_rev(self) -> dict[int, int]:
        return self._frame_to_client

    def _decorate_and_map(self, client) -> None:
        try:
            geom = client.get_geometry()
        except Exception:
            client.map()
            return

        width, height = max(geom.width, 1), max(geom.height, 1)
        x, y = geom.x, geom.y

        frame = self._root.create_window(
            x, y, width, height + TITLEBAR_HEIGHT, 0,
            self._screen.root_depth, X.InputOutput, X.CopyFromParent,
            background_pixel=self._pixel(TITLEBAR_BG),
            event_mask=(
                X.SubstructureNotifyMask | X.SubstructureRedirectMask
                | X.ButtonPressMask | X.ExposureMask
            ),
        )
        client.change_save_set(X.SetModeInsert)
        client.reparent(frame, 0, TITLEBAR_HEIGHT)
        frame.map()
        client.map()
        self._display.sync()

        title = self._window_title(client.id)
        managed = ManagedWindow(
            client_id=client.id, frame_id=frame.id, title=title,
            normal_geometry=(x, y, width, height),
        )
        self.windows[client.id] = managed
        self._frame_to_client[frame.id] = client.id

        self.on_window_opened(client.id, title)
        self._draw_titlebar(frame.id)

    def _handle_client_gone(self, client_id: int) -> None:
        managed = self.windows.pop(client_id, None)
        if managed is None:
            return
        self._frame_to_client.pop(managed.frame_id, None)
        try:
            frame = self._display.create_resource_object("window", managed.frame_id)
            frame.unmap()
            frame.destroy()
            self._display.sync()
        except (BadWindow, Exception):
            pass
        self.on_window_closed(client_id)

    def _button_rects(self, frame_width: int) -> dict[str, tuple[int, int, int, int]]:
        """Right-to-left: close, maximize, minimize — same order Breeze uses."""
        y = (TITLEBAR_HEIGHT - BUTTON_SIZE) // 2
        close_x = frame_width - BUTTON_MARGIN - BUTTON_SIZE
        maximize_x = close_x - BUTTON_GAP - BUTTON_SIZE
        minimize_x = maximize_x - BUTTON_GAP - BUTTON_SIZE
        return {
            "close": (close_x, y, BUTTON_SIZE, BUTTON_SIZE),
            "maximize": (maximize_x, y, BUTTON_SIZE, BUTTON_SIZE),
            "minimize": (minimize_x, y, BUTTON_SIZE, BUTTON_SIZE),
        }

    def _draw_titlebar(self, frame_id: int) -> None:
        client_id = self._frame_to_client.get(frame_id)
        if client_id is None:
            return
        managed = self.windows.get(client_id)
        if managed is None:
            return

        frame = self._display.create_resource_object("window", frame_id)
        frame_width = managed.normal_geometry[2] if managed.normal_geometry else 200

        gc = frame.create_gc(foreground=self._pixel(TITLEBAR_BG))
        gc.change(foreground=self._pixel(TITLEBAR_BG))
        frame.fill_rectangle(gc, 0, 0, frame_width, TITLEBAR_HEIGHT)

        text_gc = frame.create_gc(foreground=self._pixel(TITLEBAR_TEXT), background=self._pixel(TITLEBAR_BG))
        frame.draw_text(text_gc, 8, TITLEBAR_HEIGHT - 9, managed.title)

        colors = {"close": CLOSE_COLOR, "maximize": MAXIMIZE_COLOR, "minimize": MINIMIZE_COLOR}
        for name, (bx, by, bw, bh) in self._button_rects(frame_width).items():
            btn_gc = frame.create_gc(foreground=self._pixel(colors[name]))
            frame.fill_arc(btn_gc, bx, by, bw, bh, 0, 360 * 64)

        self._display.sync()

    def _handle_button_press(self, event) -> None:
        # ButtonPress's `window` field is the window ButtonPressMask was
        # selected on (the frame), unlike Unmap/DestroyNotify's `window`
        # (the client) + `event` (the frame) pair.
        frame_id = event.window.id
        client_id = self._frame_to_client.get(frame_id)
        if client_id is None:
            return
        managed = self.windows.get(client_id)
        if managed is None:
            return

        frame_width = managed.normal_geometry[2] if managed.normal_geometry else 200
        px, py = event.event_x, event.event_y

        for name, (bx, by, bw, bh) in self._button_rects(frame_width).items():
            if bx <= px <= bx + bw and by <= py <= by + bh:
                getattr(self, f"_action_{name}")(managed)
                return

    def _action_close(self, managed: ManagedWindow) -> None:
        client = self._display.create_resource_object("window", managed.client_id)
        try:
            client.destroy()
            self._display.sync()
        except (BadWindow, Exception):
            pass

    def _action_minimize(self, managed: ManagedWindow) -> None:
        frame = self._display.create_resource_object("window", managed.frame_id)
        frame.unmap()
        managed.minimized = True
        self._display.sync()

    def restore(self, client_id: int) -> None:
        managed = self.windows.get(client_id)
        if managed is None or not managed.minimized:
            return
        frame = self._display.create_resource_object("window", managed.frame_id)
        frame.map()
        managed.minimized = False
        self._display.sync()

    def _action_maximize(self, managed: ManagedWindow) -> None:
        frame = self._display.create_resource_object("window", managed.frame_id)
        client = self._display.create_resource_object("window", managed.client_id)

        if managed.maximized and managed.normal_geometry:
            x, y, w, h = managed.normal_geometry
        else:
            screen_w = self._screen.width_in_pixels
            screen_h = self._screen.height_in_pixels
            x, y, w, h = 0, 0, screen_w, screen_h - TITLEBAR_HEIGHT
            managed.maximized = True
            frame.configure(x=x, y=y, width=w, height=h + TITLEBAR_HEIGHT)
            client.configure(width=w, height=h)
            self._draw_titlebar(managed.frame_id)
            self._display.sync()
            return

        frame.configure(x=x, y=y, width=w, height=h + TITLEBAR_HEIGHT)
        client.configure(width=w, height=h)
        managed.maximized = False
        self._draw_titlebar(managed.frame_id)
        self._display.sync()

    def window_titles(self) -> list[str]:
        return [w.title for w in self.windows.values()]

    def close(self) -> None:
        self._display.close()
