"""Application registry for the PythonOS launcher — the .desktop-file
equivalent. Reads real app descriptors from a directory (INI-style, same
shape as system/session's .session files) instead of hardcoding a list,
so the launcher reflects what's actually installed.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path

DEFAULT_APPS_DIR = Path("/usr/share/pythonos-apps")


@dataclass
class AppEntry:
    name: str
    exec_command: list[str]
    icon: str = "application-x-executable"
    category: str = "Other"

    @classmethod
    def from_file(cls, path: Path) -> "AppEntry":
        parser = configparser.ConfigParser()
        parser.read(path)
        section = parser["App"]
        return cls(
            name=section.get("Name", path.stem),
            exec_command=section["Exec"].split(),
            icon=section.get("Icon", "application-x-executable"),
            category=section.get("Category", "Other"),
        )


def list_apps(apps_dir: Path | str = DEFAULT_APPS_DIR) -> list[AppEntry]:
    apps_dir = Path(apps_dir)
    if not apps_dir.exists():
        return []
    return [AppEntry.from_file(p) for p in sorted(apps_dir.glob("*.app"))]


def apps_by_category(apps_dir: Path = DEFAULT_APPS_DIR) -> dict[str, list[AppEntry]]:
    grouped: dict[str, list[AppEntry]] = {}
    for app in list_apps(apps_dir):
        grouped.setdefault(app.category, []).append(app)
    return grouped


def search_apps(query: str, apps_dir: Path = DEFAULT_APPS_DIR) -> list[AppEntry]:
    query = query.lower()
    return [a for a in list_apps(apps_dir) if query in a.name.lower()]
