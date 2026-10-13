# PythonOS Desktop

Graphics stack decision (spec section 8): **PySide6** (official Qt for
Python, LGPL). Chosen because it's the closest match to KDE Plasma's own
stack (Qt/QtQuick) — Plasma's widget model, panel/launcher concepts, and
window management vocabulary map directly onto Qt — while staying entirely
Python above the toolkit's native bindings. No C++/QML build step is
required to develop against it, matching the Python-first principle.

Rendering is proven under two environments:
- `Xvfb` (real X virtual framebuffer) — for interactive testing.
- `QT_QPA_PLATFORM=offscreen` — for automated, CI-friendly tests and
  screenshots without any display server at all. This is what
  `tests/unit/test_panel.py` and `test_launcher.py` run under.

## Components implemented so far

- `desktop/launcher/apps_registry.py` — real app registry: `.app` files
  (INI format, same idea as `.desktop` entries) describing name, exec
  command, icon, category. `list_apps`, `apps_by_category`, `search_apps`.
  Examples in `apps/examples/*.app`.
- `desktop/launcher/launcher_widget.py` — `LauncherWidget`: a Kickoff-style
  layout (search box on top, category sidebar on the left, filtered app
  list on the right), backed by the real registry, launches apps via an
  injectable function (real `subprocess.Popen` by default, fake in tests).
- `desktop/panel/panel_widget.py` — `PanelWidget`: launcher button (with
  icon), `TaskManagerWidget` (real window list — see Window Management
  below), `SystemTrayWidget` (status items), `ClockWidget` (live, driven
  by a real `QTimer` off system time).
- `desktop/windows/wm.py` + `desktop/session/graphical_session.py` — a
  real X11 window manager wired to the panel's task manager. See
  docs/WINDOWS.md; this is what makes `TaskManagerWidget` show genuinely
  open windows instead of manually-added ones.
- `desktop/theme/theme_manager.py` + `themes/pythonos-dark`,
  `themes/pythonos-light` — a real theme engine (spec section 9):
  `theme.json` defines color tokens, `style.qss` is a Qt stylesheet
  template with `{token}` placeholders, `ThemeManager.apply()` renders
  and applies it to a live `QApplication`. Palettes are inspired by KDE's
  public Breeze/Breeze Dark color values (hex codes aren't copyrightable
  creative expression; the QSS itself is written from scratch).
- `desktop/background/wallpaper_widget.py` — `WallpaperWidget`: a real
  `paintEvent`-driven gradient background using the active theme's
  wallpaper colors (a Plasma-default-blue-style gradient today; picking
  an actual image file is `PLANNED`).

All of the above are real Qt widgets with real behavior — not static
images — proven by:
1. Automated tests instantiating them under `offscreen` (or real Xvfb for
   the window-manager integration) and asserting on actual widget state
   (visible items, text, geometry, stylesheet content) — 75 tests total
   across `test_launcher.py`, `test_panel.py`, `test_wm.py`,
   `test_graphical_session.py`, `test_theme.py`, `test_wallpaper.py`.
2. A rendered screenshot of the full assembled desktop — wallpaper, panel,
   an open Kickoff-style launcher, and a real `xclock` window being
   tracked by the real window manager — at
   [desktop-proof.png](desktop-proof.png).

## What's not real yet

- No window decorations (titlebars/borders/snapping), no focus handling,
  no multi-monitor — see docs/WINDOWS.md.
- **No KRunner-equivalent global search**, no notification center, no
  widgets (plasmoids), no virtual desktops, no settings app yet — all
  `PLANNED`.
- `GraphicalSession` is not yet wired through `LoginManager` →
  `SessionManager` as the real primary component; it's started directly
  today for development/testing. The installed default session is still
  the headless `pysh` one (see docs/SESSION.md) until that wiring lands.
- Only one wallpaper style (a gradient) and two themes exist; no
  user-facing theme switcher UI yet (the mechanism — `ThemeManager` — is
  real and tested, just not exposed in a settings app that doesn't exist
  yet either).

## Architecture reference

Studied (not copied — see spec section 6 on licensing) from public KDE
documentation on Plasma's panel/launcher/task-manager/theming concepts:
- [Plasma Applets — KDE Community Wiki](https://community.kde.org/Plasma)
- [Kickoff (Application Launcher) — KDE UserBase](https://userbase.kde.org/Plasma/Application_Launcher)
- [Breeze — KDE Community Wiki](https://community.kde.org/Plasma/Breeze) (palette reference only; QSS and code written independently)
