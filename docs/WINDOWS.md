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
  `SubstructureRedirect`, and for every client **reparents it into a
  decorated frame window** it creates and draws itself — a titlebar
  (`TITLEBAR_HEIGHT = 26px`) with the window's `WM_NAME` text and three
  Breeze-style round buttons (minimize/maximize/close, drawn with real X
  `fill_arc` calls, not icons yet). This is the standard X11 reparenting-WM
  technique — the same one kwin itself uses in X11 mode. Button clicks are
  hit-tested against real pointer coordinates from `ButtonPress` events
  and dispatch real actions:
  - **close** → destroys the actual client window (not yet graceful
    `WM_DELETE_WINDOW` — see below).
  - **minimize** → unmaps the frame; `WindowManager.restore()` maps it
    back.
  - **maximize** → resizes frame + client to the screen (toggles back to
    the saved geometry on a second click).
  Calls `on_window_opened`/`on_window_closed` callbacks keyed by the
  client's window id (decoration is transparent to callers). Refuses to
  start with a clear error if another WM already owns the display (X only
  allows one).
- `desktop/session/graphical_session.py` — `GraphicalSession`: wires the
  `WindowManager` to the real `PanelWidget`'s `TaskManagerWidget`. The
  session's own chrome (wallpaper, panel, launcher popup) sets Qt's
  `X11BypassWindowManagerHint` (override-redirect) so our own WM never
  decorates its own shell — the same technique every real desktop's
  panel/dock uses to stay undecorated and out of the task list.
- Proven three ways, all against a real Xvfb server and real X clients
  (`xclock`), not simulated:
  1. `tests/unit/test_wm.py` — open/close tracking, a second WM refused
     the display, **real reparenting verified via `query_tree()`** (the
     client's actual X-server-recorded parent becomes our frame), and
     **a synthetic click on the close button's real screen coordinates
     closes the real client process's window**.
  2. `tests/unit/test_graphical_session.py` — same idea end-to-end
     through the panel, run in a subprocess (an xcb-backed `QApplication`
     can't safely share a process with the offscreen one the other
     desktop tests use).
  3. A rendered screenshot of the assembled result —
     [window-decorations-proof.png](window-decorations-proof.png): the
     panel and launcher undecorated (no titlebar), and a real `xclock`
     window with a genuine titlebar and colored buttons.

## What's not real yet

- **Close is forceful, not graceful.** A well-behaved WM sends
  `WM_DELETE_WINDOW` via `ClientMessage` and lets the client choose to
  save work first; `_action_close` just destroys the X window. Fine for
  `xclock`; would lose unsaved state in a real app. `PLANNED`.
- No window dragging/moving by the titlebar, no resize handles, no
  snapping.
- No focus handling (click-to-focus, Alt-Tab), no keyboard shortcuts, no
  multi-monitor.
- `WindowManager.process_pending_events()` is polled on a `QTimer`
  (50 ms) rather than integrated into a single select/poll loop with
  Qt's own event loop — correct, but not the most efficient design; fine
  for now given PythonOS has no compositor-heavy workload yet.
- This window manager only matters once a real session uses it as the
  primary `SessionManager` component instead of the headless `pysh`
  session; that wiring is the next step (see ROADMAP.md).
