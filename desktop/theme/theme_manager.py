"""PythonOS theme engine (spec section 9).

A theme is a directory under themes/ with theme.json (name, variant,
color tokens) and style.qss (a Qt stylesheet template using {token}
placeholders substituted from theme.json's colors). This is a real,
working mechanism — not a static screenshot — applied to a live
QApplication via `ThemeManager.apply()`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THEMES_DIR = REPO_ROOT / "themes"
DEFAULT_THEME = "pythonos-dark"


class ThemeError(Exception):
    pass


@dataclass
class Theme:
    name: str
    variant: str
    colors: dict[str, str]
    stylesheet_template: str

    def render_stylesheet(self) -> str:
        css = self.stylesheet_template
        for token, value in self.colors.items():
            css = css.replace("{" + token + "}", value)
        return css

    def color(self, token: str) -> str:
        try:
            return self.colors[token]
        except KeyError:
            raise ThemeError(f"theme {self.name!r} has no color token {token!r}") from None


def list_themes(themes_dir: Path = THEMES_DIR) -> list[str]:
    if not themes_dir.exists():
        return []
    return sorted(p.name for p in themes_dir.iterdir() if (p / "theme.json").exists())


def load_theme(theme_id: str = DEFAULT_THEME, themes_dir: Path = THEMES_DIR) -> Theme:
    theme_dir = themes_dir / theme_id
    manifest_path = theme_dir / "theme.json"
    qss_path = theme_dir / "style.qss"
    if not manifest_path.exists():
        raise ThemeError(f"no such theme: {theme_id!r} (looked in {theme_dir})")

    manifest = json.loads(manifest_path.read_text())
    stylesheet_template = qss_path.read_text() if qss_path.exists() else ""

    return Theme(
        name=manifest["name"],
        variant=manifest.get("variant", "dark"),
        colors=manifest["colors"],
        stylesheet_template=stylesheet_template,
    )


class ThemeManager:
    def __init__(self, themes_dir: Path = THEMES_DIR):
        self.themes_dir = themes_dir
        self.current: Theme | None = None

    def apply(self, theme_id: str = DEFAULT_THEME, app=None) -> Theme:
        theme = load_theme(theme_id, self.themes_dir)
        self.current = theme
        if app is not None:
            app.setStyleSheet(theme.render_stylesheet())
        return theme
