from system.session.manager import Component, SessionManager


class FakeLauncher:
    def __init__(self):
        self._next_pid = 500
        self.spawned: list[list[str]] = []
        self._dead_queue: list[tuple[int, int]] = []

    def spawn(self, argv):
        pid = self._next_pid
        self._next_pid += 1
        self.spawned.append(argv)
        return pid

    def kill_pid(self, pid: int, status: int = 0):
        self._dead_queue.append((pid, status))

    def waitpid_any(self, blocking: bool):
        if self._dead_queue:
            return self._dead_queue.pop(0)
        return None


def make_components():
    return [
        Component(name="compositor", exec_start=["/bin/true"], primary=True),
        Component(name="shell", exec_start=["/bin/true"], depends_on=["compositor"]),
        Component(name="statusbar", exec_start=["/bin/true"], depends_on=["compositor"]),
    ]


def test_session_manager_starts_all_components_in_dependency_order():
    launcher = FakeLauncher()
    manager = SessionManager(make_components(), launcher=launcher)
    manager.start()

    assert set(manager.running_components()) == {"compositor", "shell", "statusbar"}
    assert manager.start_order.index("compositor") < manager.start_order.index("shell")


def test_session_ends_when_compositor_exits():
    launcher = FakeLauncher()
    manager = SessionManager(make_components(), launcher=launcher)
    manager.start()

    compositor_pid = manager._services["compositor"].pid
    launcher.kill_pid(compositor_pid)
    manager.reap_once()

    assert manager.session_ended is True


def test_non_primary_component_restarts_on_crash():
    launcher = FakeLauncher()
    manager = SessionManager(make_components(), launcher=launcher)
    manager.start()

    shell_pid = manager._services["shell"].pid
    launcher.kill_pid(shell_pid, status=1)
    manager.reap_once()

    assert manager.session_ended is False
    assert manager._services["shell"].state.value == "running"
    assert manager._services["shell"].pid != shell_pid
