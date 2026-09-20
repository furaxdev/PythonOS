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
- `desktop/launcher/launcher_widget.py` — `LauncherWidget`: search box +
  filtered list, backed by the real registry, launches apps via an
  injectable function (real `subprocess.Popen` by default, fake in tests).
- `desktop/panel/panel_widget.py` — `PanelWidget`: launcher button,
  `TaskManagerWidget` (window list), `SystemTrayWidget` (status items),
  `ClockWidget` (live, driven by a real `QTimer` off system time).

All of the above are real Qt widgets with real behavior — not static
images — proven by:
1. Automated tests instantiating them under `offscreen` and asserting on
   actual widget state (visible items, text, geometry) — see
   `tests/unit/test_launcher.py`, `test_panel.py` (10 tests).
2. A rendered screenshot of the assembled panel: [panel-proof.png](panel-proof.png).

## What's not real yet

- **No compositor.** `TaskManagerWidget.add_window()` is called manually
  today; nothing yet feeds it real window-open/close events, because
  there's no compositor to emit them. This is the single biggest
  remaining gap before Phase 6 can be called done — see
  `system/session/manager.py`'s `Component(primary=True)` slot, which is
  where a compositor process will plug in once built.
- **No KRunner-equivalent global search**, no notification center, no
  widgets (plasmoids), no virtual desktops, no settings app yet — all
  `PLANNED`.
- The panel is not yet wired into a real session (`desktop/session/`) as
  the primary component; today's real session is still the headless
  `pysh` one (see docs/SESSION.md).

## Architecture reference

Studied (not copied — see spec section 6 on licensing) from public KDE
documentation on Plasma's panel/launcher/task-manager concepts:
- [Plasma Applets — KDE Community Wiki](https://community.kde.org/Plasma)
- [Kickoff (Application Launcher) — KDE UserBase](https://userbase.kde.org/Plasma/Application_Launcher)
