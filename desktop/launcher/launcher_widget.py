"""The PythonOS application launcher — Plasma's "Application Launcher"
(Kickoff) equivalent: category sidebar + search + app list, backed by the
real AppEntry registry (desktop/launcher/apps_registry.py)."""

from __future__ import annotations

import subprocess

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop.launcher.apps_registry import AppEntry, DEFAULT_APPS_DIR, apps_by_category, list_apps

ALL_CATEGORY = "All Applications"


class LauncherWidget(QWidget):
    app_launched = Signal(str)  # app name

    def __init__(self, apps_dir=DEFAULT_APPS_DIR, launch_fn=None, parent=None):
        super().__init__(parent)
        self.setObjectName("Launcher")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.apps_dir = apps_dir
        self._launch_fn = launch_fn or self._default_launch

        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Type to search applications…")
        self.search_box.textChanged.connect(self.refresh)

        self.category_list = QListWidget(self)
        self.category_list.setObjectName("CategoryList")
        self.category_list.setFixedWidth(160)
        self.category_list.currentTextChanged.connect(self._on_category_changed)

        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("AppList")
        self.list_widget.itemActivated.connect(self._on_item_activated)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.addWidget(self.category_list)
        body.addWidget(self.list_widget, stretch=1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_box)
        layout.addLayout(body)

        self._refresh_categories()
        self.refresh()

    def _default_launch(self, app: AppEntry) -> None:
        subprocess.Popen(app.exec_command)

    def _refresh_categories(self) -> None:
        self.category_list.clear()
        self.category_list.addItem(ALL_CATEGORY)
        for category in sorted(apps_by_category(self.apps_dir)):
            self.category_list.addItem(category)
        self.category_list.setCurrentRow(0)

    def _on_category_changed(self, _text: str) -> None:
        self.refresh()

    def selected_category(self) -> str:
        item = self.category_list.currentItem()
        return item.text() if item else ALL_CATEGORY

    def refresh(self) -> None:
        query = self.search_box.text().strip().lower()
        apps = list_apps(self.apps_dir)

        category = self.selected_category()
        if category != ALL_CATEGORY:
            apps = [a for a in apps if a.category == category]
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
