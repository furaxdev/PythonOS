"""PythonOS desktop background — the "wallpaper" layer behind windows,
Plasma-equivalent. Renders a real gradient from the active theme's colors
(paintEvent-driven, not a static image) so it tracks theme changes; a
future PLANNED feature is picking an actual image file instead."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import QWidget

from desktop.theme.theme_manager import Theme


class WallpaperWidget(QWidget):
    def __init__(self, theme: Theme | None = None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        if self.theme is not None:
            start = QColor(self.theme.color("wallpaper_start"))
            end = QColor(self.theme.color("wallpaper_end"))
        else:
            start, end = QColor("#1d99f3"), QColor("#2a2e32")

        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, start)
        gradient.setColorAt(1, end)
        painter.fillRect(self.rect(), gradient)
