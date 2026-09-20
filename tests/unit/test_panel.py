from desktop.panel.panel_widget import ClockWidget, PanelWidget, SystemTrayWidget, TaskManagerWidget


def test_task_manager_add_remove_window(qapp):
    tm = TaskManagerWidget()
    tm.add_window("win1", "pysh — /home/furax")
    tm.add_window("win2", "Files")
    assert tm.window_titles() == ["pysh — /home/furax", "Files"]

    tm.add_window("win1", "pysh — /tmp")  # same id, updates title in place
    assert tm.window_titles() == ["pysh — /tmp", "Files"]

    tm.remove_window("win2")
    assert tm.window_titles() == ["pysh — /tmp"]


def test_clock_widget_shows_real_time(qapp):
    import re
    clock = ClockWidget()
    assert re.match(r"^\d{2}:\d{2}:\d{2}$", clock.text())


def test_system_tray_sets_and_reads_items(qapp):
    tray = SystemTrayWidget()
    tray.set_item("network", "eth0 connected")
    tray.set_item("battery", "80%")
    assert tray.item_text("network") == "eth0 connected"
    assert tray.item_text("battery") == "80%"
    assert tray.item_text("nonexistent") is None


def test_panel_widget_builds_with_launcher_and_clock(tmp_path, qapp):
    (tmp_path / "term.app").write_text("[App]\nName=Terminal\nExec=/usr/bin/pysh\n")
    panel = PanelWidget(apps_dir=tmp_path)

    assert panel.launcher.isHidden()
    panel.launcher_button.click()
    assert not panel.launcher.isHidden()
    panel.launcher_button.click()
    assert panel.launcher.isHidden()

    assert panel.height() == 40
