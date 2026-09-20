"""PythonOS session manager (ksmserver-equivalent).

Real ksmserver: started by startplasma inside the user session, launches
and supervises the session's components (compositor, shell, status
daemons), and ends the session when the compositor exits. We reimplement
that shape: SessionManager starts a list of session Components in order
(reusing the same dependency-ordered restart logic as system/init, since
it's the same problem at a smaller scope), and exposes `session_ended`
once the "primary" component (the compositor, conventionally first) has
exited.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from system.init.manager import ProcessLauncher
from system.init.service import Service, ServiceState, resolve_start_order


@dataclass
class Component:
    name: str
    exec_start: list[str]
    depends_on: list[str] = field(default_factory=list)
    primary: bool = False  # session ends when this one exits


class SessionManager:
    """Supervises a desktop session's components (compositor, shell,
    status bar daemons, ...). Distinct from system.init.manager.ServiceManager
    (which supervises system-wide services before any user is logged in):
    this one is scoped to a single user session and ends when the primary
    component (the compositor) exits, rather than restarting forever."""

    def __init__(self, components: list[Component], launcher: ProcessLauncher | None = None):
        self.components = {c.name: c for c in components}
        self.launcher = launcher or ProcessLauncher()
        self._services = {
            c.name: Service(name=c.name, exec_start=c.exec_start, depends_on=c.depends_on, restart=not c.primary)
            for c in components
        }
        self.start_order = resolve_start_order(self._services)
        self._pid_to_name: dict[int, str] = {}
        self.session_ended = False

    def start(self) -> None:
        for name in self.start_order:
            svc = self._services[name]
            pid = self.launcher.spawn(svc.exec_start)
            svc.pid = pid
            svc.state = ServiceState.RUNNING
            self._pid_to_name[pid] = name

    def handle_exit(self, pid: int, status: int) -> None:
        name = self._pid_to_name.pop(pid, None)
        if name is None:
            return
        svc = self._services[name]
        svc.state = ServiceState.STOPPED

        if self.components[name].primary:
            self.session_ended = True
            return

        if svc.restart:
            new_pid = self.launcher.spawn(svc.exec_start)
            svc.pid = new_pid
            svc.state = ServiceState.RUNNING
            self._pid_to_name[new_pid] = name

    def reap_once(self, blocking: bool = False) -> bool:
        result = self.launcher.waitpid_any(blocking)
        if result is None:
            return False
        pid, status = result
        self.handle_exit(pid, status)
        return True

    def running_components(self) -> list[str]:
        return [n for n, s in self._services.items() if s.state == ServiceState.RUNNING]
