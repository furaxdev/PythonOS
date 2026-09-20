from pathlib import Path

from desktop.launcher.apps_registry import apps_by_category, list_apps, search_apps


def write_app_file(path: Path, name: str, exec_cmd: str, category: str = "Other"):
    path.write_text(f"[App]\nName={name}\nExec={exec_cmd}\nCategory={category}\n")


def test_list_apps_missing_dir_returns_empty(tmp_path):
    assert list_apps(tmp_path / "nope") == []


def test_list_apps_parses_real_files(tmp_path):
    write_app_file(tmp_path / "term.app", "Terminal", "/usr/bin/pysh", category="System")
    write_app_file(tmp_path / "files.app", "Files", "/usr/bin/pyos-files", category="System")

    apps = list_apps(tmp_path)
    names = {a.name for a in apps}
    assert names == {"Terminal", "Files"}


def test_apps_by_category_groups_correctly(tmp_path):
    write_app_file(tmp_path / "term.app", "Terminal", "/usr/bin/pysh", category="System")
    write_app_file(tmp_path / "calc.app", "Calculator", "/usr/bin/pyos-calc", category="Utilities")

    grouped = apps_by_category(tmp_path)
    assert grouped["System"][0].name == "Terminal"
    assert grouped["Utilities"][0].name == "Calculator"


def test_search_apps_case_insensitive(tmp_path):
    write_app_file(tmp_path / "term.app", "Terminal", "/usr/bin/pysh")
    write_app_file(tmp_path / "files.app", "Files", "/usr/bin/pyos-files")

    results = search_apps("TERM", tmp_path)
    assert [a.name for a in results] == ["Terminal"]


def test_launcher_widget_lists_and_filters_apps(tmp_path, qapp):
    from desktop.launcher.launcher_widget import LauncherWidget

    write_app_file(tmp_path / "term.app", "Terminal", "/usr/bin/pysh")
    write_app_file(tmp_path / "files.app", "Files", "/usr/bin/pyos-files")

    widget = LauncherWidget(apps_dir=tmp_path)
    assert set(widget.visible_app_names()) == {"Terminal", "Files"}

    widget.search_box.setText("term")
    assert widget.visible_app_names() == ["Terminal"]


def test_launcher_widget_launches_app_via_injected_function(tmp_path, qapp):
    from desktop.launcher.launcher_widget import LauncherWidget

    write_app_file(tmp_path / "term.app", "Terminal", "/usr/bin/pysh")

    launched = []
    widget = LauncherWidget(apps_dir=tmp_path, launch_fn=lambda app: launched.append(app.name))

    item = widget.list_widget.item(0)
    widget._on_item_activated(item)

    assert launched == ["Terminal"]
