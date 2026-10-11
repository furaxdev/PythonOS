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


class WindowManagerError(Exception):
    pass


@dataclass
class ManagedWindow:
    window_id: int
    title: str


class WindowManager:
    """A minimal but real reparenting-free X11 window manager: it does not
    draw decorations (no titlebars yet — see docs/WINDOWS.md PLANNED
    section), it just takes over SubstructureRedirect on the root window,
    maps/tracks/unmaps client windows, and notifies callbacks so the panel's
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

        self._display = display.Display(display_name)
        self._root = self._display.screen().root

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
            wid = event.window.id
            event.window.map()
            self._display.sync()
            title = self._window_title(wid)
            self.windows[wid] = ManagedWindow(window_id=wid, title=title)
            self.on_window_opened(wid, title)
        elif event.type in (X.UnmapNotify, X.DestroyNotify):
            wid = event.window.id
            if wid in self.windows:
                del self.windows[wid]
                self.on_window_closed(wid)

    def window_titles(self) -> list[str]:
        return [w.title for w in self.windows.values()]

    def close(self) -> None:
        self._display.close()
