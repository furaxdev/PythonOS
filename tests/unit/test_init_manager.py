import json
from pathlib import Path

import pytest

from system.init.manager import ServiceManager
from system.init.service import DependencyError, Service, resolve_start_order


def write_service(dirpath: Path, name: str, depends_on=None, restart=True, restart_max=5, oneshot=False):
    data = {
        "name": name,
        "exec_start": ["/bin/true"],
        "depends_on": depends_on or [],
        "restart": restart,
        "restart_max": restart_max,
        "oneshot": oneshot,
    }
    (dirpath / f"{name}.json").write_text(json.dumps(data))


def test_resolve_start_order_respects_dependencies(tmp_path):
    write_service(tmp_path, "network")
    write_service(tmp_path, "logger")
    write_service(tmp_path, "desktop", depends_on=["network", "logger"])

    from system.init.service import load_services
    services = load_services(tmp_path)
    order = resolve_start_order(services)

    assert order.index("network") < order.index("desktop")
    assert order.index("logger") < order.index("desktop")


def test_resolve_start_order_detects_cycle(tmp_path):
    write_service(tmp_path, "a", depends_on=["b"])
    write_service(tmp_path, "b", depends_on=["a"])

    from system.init.service import load_services
    services = load_services(tmp_path)
    with pytest.raises(DependencyError):
        resolve_start_order(services)


def test_resolve_start_order_missing_dependency(tmp_path):
    write_service(tmp_path, "a", depends_on=["ghost"])

    from system.init.service import load_services
    services = load_services(tmp_path)
    with pytest.raises(DependencyError):
        resolve_start_order(services)


class FakeLauncher:
    """Simulates process spawning/reaping without real forking."""

    def __init__(self):
        self._next_pid = 100
        self.spawned: list[list[str]] = []
        self._dead_queue: list[tuple[int, int]] = []

    def spawn(self, argv):
        pid = self._next_pid
        self._next_pid += 1
        self.spawned.append(argv)
        return pid

    def kill_pid(self, pid: int, status: int = 1):
        self._dead_queue.append((pid, status))

    def waitpid_any(self, blocking: bool):
        if self._dead_queue:
            return self._dead_queue.pop(0)
        return None


def test_service_manager_starts_all_in_order(tmp_path):
    write_service(tmp_path, "network")
    write_service(tmp_path, "logger")
    write_service(tmp_path, "desktop", depends_on=["network", "logger"])

    launcher = FakeLauncher()
    manager = ServiceManager(tmp_path, launcher=launcher)
    manager.start_all()

    assert set(manager.running_services()) == {"network", "logger", "desktop"}
    assert len(launcher.spawned) == 3


def test_service_manager_restarts_on_unexpected_exit(tmp_path):
    write_service(tmp_path, "flaky", restart=True, restart_max=3)

    launcher = FakeLauncher()
    manager = ServiceManager(tmp_path, launcher=launcher)
    manager.start_all()

    first_pid = manager.services["flaky"].pid
    launcher.kill_pid(first_pid, status=1)
    manager.reap_once(blocking=False)

    assert manager.services["flaky"].state.value == "running"
    assert manager.services["flaky"].restart_count == 1
    assert manager.services["flaky"].pid != first_pid
    assert len(launcher.spawned) == 2


def test_service_manager_gives_up_after_restart_max(tmp_path):
    write_service(tmp_path, "doomed", restart=True, restart_max=2)

    launcher = FakeLauncher()
    manager = ServiceManager(tmp_path, launcher=launcher)
    manager.start_all()

    for _ in range(3):
        pid = manager.services["doomed"].pid
        launcher.kill_pid(pid, status=1)
        manager.reap_once(blocking=False)

    assert manager.services["doomed"].state.value == "failed"
    assert manager.services["doomed"].restart_count == 2


def test_oneshot_service_does_not_restart(tmp_path):
    write_service(tmp_path, "setup", oneshot=True, restart=False)

    launcher = FakeLauncher()
    manager = ServiceManager(tmp_path, launcher=launcher)
    manager.start_all()

    pid = manager.services["setup"].pid
    launcher.kill_pid(pid, status=0)
    manager.reap_once(blocking=False)

    assert manager.services["setup"].state.value == "stopped"
    assert len(launcher.spawned) == 1
