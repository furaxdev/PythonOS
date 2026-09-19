"""PythonOS power management.

Battery/AC state is read straight from /sys/class/power_supply (pure
Python, no dependency on upower or any other daemon — PythonOS *is* the
daemon). Actions (suspend/poweroff/reboot) go through an injectable
`ActionRunner` so the logic that decides what to run is unit-testable
without actually rebooting the test machine.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_POWER_SUPPLY_PATH = Path("/sys/class/power_supply")
SYS_POWER_STATE = Path("/sys/power/state")


@dataclass
class PowerSupply:
    name: str
    type: str  # "Battery" or "Mains"
    online: bool | None = None       # for Mains (AC)
    capacity: int | None = None      # percent, for Battery
    status: str | None = None        # "Charging"/"Discharging"/"Full", for Battery


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def list_power_supplies(base_path: Path = DEFAULT_POWER_SUPPLY_PATH) -> list[PowerSupply]:
    if not base_path.exists():
        return []

    supplies = []
    for entry in sorted(base_path.iterdir()):
        supply_type = _read(entry / "type") or "Unknown"
        online_raw = _read(entry / "online")
        capacity_raw = _read(entry / "capacity")
        status = _read(entry / "status")
        supplies.append(PowerSupply(
            name=entry.name,
            type=supply_type,
            online=(online_raw == "1") if online_raw is not None else None,
            capacity=int(capacity_raw) if capacity_raw and capacity_raw.isdigit() else None,
            status=status,
        ))
    return supplies


def get_battery(base_path: Path = DEFAULT_POWER_SUPPLY_PATH) -> PowerSupply | None:
    for supply in list_power_supplies(base_path):
        if supply.type == "Battery":
            return supply
    return None


def on_ac_power(base_path: Path = DEFAULT_POWER_SUPPLY_PATH) -> bool | None:
    """True/False if a Mains supply is found, None if we can't tell
    (e.g. no power_supply class at all, as on most servers/containers)."""
    for supply in list_power_supplies(base_path):
        if supply.type == "Mains" and supply.online is not None:
            return supply.online
    return None


class ActionRunner:
    """Real actions. Substituted by a fake in tests."""

    def poweroff(self) -> None:
        subprocess.run(["poweroff"], check=False)

    def reboot(self) -> None:
        subprocess.run(["reboot"], check=False)

    def suspend(self) -> None:
        try:
            SYS_POWER_STATE.write_text("mem")
        except OSError:
            pass


class PowerManager:
    def __init__(self, runner: ActionRunner | None = None):
        self.runner = runner or ActionRunner()

    def poweroff(self) -> None:
        self.runner.poweroff()

    def reboot(self) -> None:
        self.runner.reboot()

    def suspend(self) -> None:
        self.runner.suspend()

    def should_warn_low_battery(self, threshold: int = 15) -> bool:
        battery = get_battery(DEFAULT_POWER_SUPPLY_PATH)
        if battery is None or battery.capacity is None:
            return False
        return battery.capacity <= threshold and battery.status == "Discharging"
