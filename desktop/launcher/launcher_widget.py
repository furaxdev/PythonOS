"""The PythonOS application launcher — Plasma's "Application Launcher"
(Kickoff) equivalent: a popup menu with search and categories, backed by
the real AppEntry registry (desktop/launcher/apps_registry.py)."""

from __future__ import annotations

import subprocess

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.launcher.apps_registry import AppEntry, DEFAULT_APPS_DIR, list_apps


class LauncherWidget(QWidget):
    app_launched = Signal(str)  # app name

    def __init__(self, apps_dir=DEFAULT_APPS_DIR, launch_fn=None, parent=None):
        super().__init__(parent)
        self.apps_dir = apps_dir
        self._launch_fn = launch_fn or self._default_launch

        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("Type to search applications…")
        self.search_box.textChanged.connect(self.refresh)

        self.list_widget = QListWidget(self)
        self.list_widget.itemActivated.connect(self._on_item_activated)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

        self.refresh()

    def _default_launch(self, app: AppEntry) -> None:
        subprocess.Popen(app.exec_command)

    def refresh(self) -> None:
        query = self.search_box.text().strip().lower()
        apps = list_apps(self.apps_dir)
        if query:
            apps = [a for a in apps if query in a.name.lower()]

        self.list_widget.clear()
        for app in apps:
            item = QListWidgetItem(app.name)
            item.setData(1000, app)
            self.list_widget.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        app: AppEntry = item.data(1000)
        self._launch_fn(app)
        self.app_launched.emit(app.name)

    def visible_app_names(self) -> list[str]:
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]
