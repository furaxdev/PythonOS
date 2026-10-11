# PythonOS Window Management

The compositor/window-manager gap identified in ROADMAP.md's Phase 6 is
now closed for X11: `desktop/windows/wm.py` is a real, working window
manager.

## Why X11 and not Wayland

Writing a Wayland compositor from scratch means implementing buffer
sharing, the core Wayland protocol, and either DRM/KMS or nested
compositing — a large native-leaning undertaking, not a reasonable target
for "Python first, reimplemented independently." X11 window management,
by contrast, is just protocol messages: become the `SubstructureRedirect`
client on the root window and the X server hands you every client's
map/unmap/destroy events. `python-xlib` implements the full protocol in
pure Python, so this stays entirely Python above libX11's C client
library (itself not something PythonOS reimplements, same spirit as not
reimplementing the kernel). A Wayland backend remains future work.

## What's real

- `desktop/windows/wm.py` — `WindowManager`: takes over
  `SubstructureRedirect`, maps client windows, reads their title via
  `WM_NAME`, and calls `on_window_opened`/`on_window_closed` callbacks.
  Refuses to start with a clear error if another WM already owns the
  display (X only allows one).
- `desktop/session/graphical_session.py` — `GraphicalSession`: wires the
  `WindowManager` to the real `PanelWidget`'s `TaskManagerWidget`, so the
  panel's task list reflects genuinely open windows.
- Proven two ways:
  1. `tests/unit/test_wm.py` — spawns a real Xvfb server and a real
     `xclock` client, asserts the WM sees the real `MapRequest`/
     `UnmapNotify` and reports the correct title; also proves a second
     WM is refused the display.
  2. `tests/unit/test_graphical_session.py` — same idea end-to-end
     through the panel, run in a subprocess (an xcb-backed `QApplication`
     can't safely share a process with the offscreen one the other
     desktop tests use). A rendered screenshot of the result is at
     [graphical-session-proof.png](graphical-session-proof.png): the
     panel's task manager showing `xclock` as an open window, driven
     entirely by real X11 events.

## What's not real yet

- No window decorations (titlebars, borders, snapping) — windows are
  mapped as-is. `ManagedWindow` has no geometry/decoration state.
- No focus handling, no keyboard shortcuts, no multi-monitor.
- `WindowManager.process_pending_events()` is polled on a `QTimer`
  (50 ms) rather than integrated into a single select/poll loop with
  Qt's own event loop — correct, but not the most efficient design; fine
  for now given PythonOS has no compositor-heavy workload yet.
- This window manager only matters once a real session uses it as the
  primary `SessionManager` component instead of the headless `pysh`
  session; that wiring is the next step (see ROADMAP.md).
