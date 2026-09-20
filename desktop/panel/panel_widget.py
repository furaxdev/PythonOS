"""The PythonOS panel — Plasma's bottom panel equivalent: launcher button,
running-window task list (task manager), clock, and a system tray area.
Real Qt widgets, real layout, real clock driven off the system time — not
a static mockup image.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from desktop.launcher.launcher_widget import LauncherWidget

PANEL_HEIGHT = 40


class TaskManagerWidget(QWidget):
    """Lists currently "open" windows. Backed by an explicit list rather
    than a compositor (none exists yet — see ROADMAP.md Phase 5 BLOCKED
    note) so the panel's layout and behavior can be built and tested now;
    swapping in real compositor window events later is a constructor-arg
    change, not a rewrite."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(4, 0, 4, 0)
        self._buttons: dict[str, QPushButton] = {}

    def add_window(self, window_id: str, title: str) -> None:
        if window_id in self._buttons:
            self._buttons[window_id].setText(title)
            return
        btn = QPushButton(title, self)
        self.layout_.addWidget(btn)
        self._buttons[window_id] = btn

    def remove_window(self, window_id: str) -> None:
        btn = self._buttons.pop(window_id, None)
        if btn is not None:
            self.layout_.removeWidget(btn)
            btn.deleteLater()

    def window_titles(self) -> list[str]:
        return [b.text() for b in self._buttons.values()]


class ClockWidget(QLabel):
    def __init__(self, fmt: str = "%H:%M:%S", parent=None):
        super().__init__(parent)
        self.fmt = fmt
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)
        self._timer.start(1000)
        self.tick()

    def tick(self) -> None:
        self.setText(datetime.now().strftime(self.fmt))


class SystemTrayWidget(QWidget):
    """Holds small status icons (network, audio, battery). Populated from
    the real system/* modules rather than faked icons."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_ = QHBoxLayout(self)
        self.layout_.setContentsMargins(4, 0, 4, 0)
        self._items: dict[str, QLabel] = {}

    def set_item(self, name: str, text: str) -> None:
        if name not in self._items:
            label = QLabel(self)
            self.layout_.addWidget(label)
            self._items[name] = label
        self._items[name].setText(text)

    def item_text(self, name: str) -> str | None:
        label = self._items.get(name)
        return label.text() if label else None


class PanelWidget(QWidget):
    def __init__(self, apps_dir=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(PANEL_HEIGHT)

        self.launcher_button = QPushButton("PythonOS", self)
        self.launcher = LauncherWidget(apps_dir=apps_dir) if apps_dir else LauncherWidget()
        self.launcher.hide()
        self.launcher_button.clicked.connect(self._toggle_launcher)

        self.task_manager = TaskManagerWidget(self)
        self.tray = SystemTrayWidget(self)
        self.clock = ClockWidget(parent=self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.addWidget(self.launcher_button)
        layout.addWidget(self.task_manager, stretch=1)
        layout.addWidget(self.tray)
        layout.addWidget(self.clock)

    def _toggle_launcher(self) -> None:
        self.launcher.setVisible(not self.launcher.isVisible())
