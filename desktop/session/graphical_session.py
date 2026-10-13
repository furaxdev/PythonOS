#!/usr/bin/env python3
"""The PythonOS graphical session — wires the real X11 WindowManager
(desktop/windows/wm.py) to the real panel (desktop/panel/panel_widget.py)
so the task manager reflects actual windows, not manually-added ones.

This is the session that will become the SessionManager's `primary`
component once it's solid enough to run full-time; today it's started
directly for development/testing against Xvfb, since the default
installed session is still the headless pysh one (see
desktop/session/pythonos_shell_session.py and docs/SESSION.md for why).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from desktop.background.wallpaper_widget import WallpaperWidget  # noqa: E402
from desktop.panel.panel_widget import PANEL_HEIGHT, PanelWidget  # noqa: E402
from desktop.theme.theme_manager import DEFAULT_THEME, ThemeManager  # noqa: E402
from desktop.windows.wm import WindowManager, WindowManagerError  # noqa: E402


class GraphicalSession:
    def __init__(self, display_name: str | None = None, apps_dir=None, theme_id: str = DEFAULT_THEME):
        self.app = QApplication.instance() or QApplication([])

        self.theme_manager = ThemeManager()
        self.theme = self.theme_manager.apply(theme_id, app=self.app)

        self.wallpaper = WallpaperWidget(theme=self.theme)
        self.panel = PanelWidget(apps_dir=apps_dir)
        self.wm = WindowManager(
            display_name=display_name,
            on_window_opened=self._on_window_opened,
            on_window_closed=self._on_window_closed,
        )
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self.wm.process_pending_events)
        self._own_window_ids: set[int] = set()

    _CHROME_TITLES = {"PythonOS Launcher"}

    def _on_window_opened(self, window_id: int, title: str) -> None:
        if window_id in self._own_window_ids or title in self._CHROME_TITLES:
            self._own_window_ids.add(window_id)
            return  # our own chrome (wallpaper, panel, launcher popup) isn't a task
        self.panel.task_manager.add_window(str(window_id), title)

    def _on_window_closed(self, window_id: int) -> None:
        self.panel.task_manager.remove_window(str(window_id))

    def start(self) -> None:
        try:
            self.wm.start()
        except WindowManagerError as exc:
            print(f"pythonos-graphical-session: {exc}", file=sys.stderr)
            raise

        screen = self.app.primaryScreen().geometry()
        self.wallpaper.setGeometry(0, 0, screen.width(), screen.height() - PANEL_HEIGHT)
        self.wallpaper.show()

        self.panel.setGeometry(0, screen.height() - PANEL_HEIGHT, screen.width(), PANEL_HEIGHT)
        self.panel.show()

        self._own_window_ids = {int(self.wallpaper.winId()), int(self.panel.winId())}
        self._poll_timer.start(50)

    def run(self) -> int:
        self.start()
        return self.app.exec()


def main(argv: list[str]) -> int:
    display_name = argv[1] if len(argv) > 1 else None
    session = GraphicalSession(display_name=display_name)
    return session.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
