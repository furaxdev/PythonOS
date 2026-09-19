from pathlib import Path

from system.power.power import (
    ActionRunner,
    PowerManager,
    PowerSupply,
    get_battery,
    list_power_supplies,
    on_ac_power,
)


def make_fake_power_supply_tree(tmp_path: Path, battery_capacity: int, status: str, ac_online: bool) -> Path:
    base = tmp_path / "power_supply"
    bat = base / "BAT0"
    bat.mkdir(parents=True)
    (bat / "type").write_text("Battery\n")
    (bat / "capacity").write_text(f"{battery_capacity}\n")
    (bat / "status").write_text(f"{status}\n")

    ac = base / "AC"
    ac.mkdir(parents=True)
    (ac / "type").write_text("Mains\n")
    (ac / "online").write_text("1\n" if ac_online else "0\n")

    return base


def test_list_power_supplies_missing_path_returns_empty(tmp_path):
    assert list_power_supplies(tmp_path / "nope") == []


def test_list_power_supplies_parses_real_looking_sysfs(tmp_path):
    base = make_fake_power_supply_tree(tmp_path, battery_capacity=42, status="Discharging", ac_online=False)
    supplies = list_power_supplies(base)
    names = {s.name for s in supplies}
    assert names == {"BAT0", "AC"}

    battery = next(s for s in supplies if s.name == "BAT0")
    assert battery.type == "Battery"
    assert battery.capacity == 42
    assert battery.status == "Discharging"

    ac = next(s for s in supplies if s.name == "AC")
    assert ac.type == "Mains"
    assert ac.online is False


def test_get_battery(tmp_path):
    base = make_fake_power_supply_tree(tmp_path, battery_capacity=80, status="Charging", ac_online=True)
    battery = get_battery(base)
    assert battery is not None
    assert battery.capacity == 80


def test_on_ac_power(tmp_path):
    base = make_fake_power_supply_tree(tmp_path, battery_capacity=80, status="Charging", ac_online=True)
    assert on_ac_power(base) is True


def test_on_ac_power_unknown_when_no_supplies(tmp_path):
    assert on_ac_power(tmp_path / "nope") is None


class FakeActionRunner(ActionRunner):
    def __init__(self):
        self.actions: list[str] = []

    def poweroff(self):
        self.actions.append("poweroff")

    def reboot(self):
        self.actions.append("reboot")

    def suspend(self):
        self.actions.append("suspend")


def test_power_manager_dispatches_actions():
    fake = FakeActionRunner()
    manager = PowerManager(runner=fake)

    manager.poweroff()
    manager.reboot()
    manager.suspend()

    assert fake.actions == ["poweroff", "reboot", "suspend"]


def test_should_warn_low_battery_logic(monkeypatch, tmp_path):
    base = make_fake_power_supply_tree(tmp_path, battery_capacity=10, status="Discharging", ac_online=False)
    monkeypatch.setattr("system.power.power.DEFAULT_POWER_SUPPLY_PATH", base)
    manager = PowerManager()
    assert manager.should_warn_low_battery(threshold=15) is True


def test_should_not_warn_when_charging(monkeypatch, tmp_path):
    base = make_fake_power_supply_tree(tmp_path, battery_capacity=10, status="Charging", ac_online=True)
    monkeypatch.setattr("system.power.power.DEFAULT_POWER_SUPPLY_PATH", base)
    manager = PowerManager()
    assert manager.should_warn_low_battery(threshold=15) is False
