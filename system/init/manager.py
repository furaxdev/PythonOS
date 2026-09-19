"""Runtime service manager for PythonOS init.

Starts services in dependency order, reaps children, and restarts services
that die unexpectedly (up to restart_max). This is the logic used by
pyinit.py when running as PID 1; it is separated out so it can be unit
tested without a real process tree or root privileges.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from pathlib import Path

from system.init.service import Service, ServiceState, load_services, resolve_start_order

log = logging.getLogger("pythonos.init")


class ProcessLauncher:
    """Thin wrapper around fork/exec so tests can substitute a fake one."""

    def spawn(self, argv: list[str]) -> int:
        pid = os.fork()
        if pid == 0:
            try:
                os.execvp(argv[0], argv)
            except OSError as exc:
                os._exit(127 + (exc.errno or 0) % 100)
        return pid

    def waitpid_any(self, blocking: bool) -> tuple[int, int] | None:
        flags = 0 if blocking else os.WNOHANG
        try:
            pid, status = os.waitpid(-1, flags)
        except ChildProcessError:
            return None
        if pid == 0:
            return None
        return pid, status


class ServiceManager:
    def __init__(self, services_dir: Path, launcher: ProcessLauncher | None = None):
        self.services_dir = services_dir
        self.launcher = launcher or ProcessLauncher()
        self.services: dict[str, Service] = load_services(services_dir)
        self.start_order: list[str] = resolve_start_order(self.services)
        self._pid_to_name: dict[int, str] = {}

    def start_all(self) -> None:
        for name in self.start_order:
            self.start(name)

    def start(self, name: str) -> None:
        svc = self.services[name]
        for dep in svc.depends_on:
            if self.services[dep].state != ServiceState.RUNNING and not self.services[dep].oneshot:
                log.warning("starting %s before dependency %s is confirmed running", name, dep)
        svc.state = ServiceState.STARTING
        pid = self.launcher.spawn(svc.exec_start)
        svc.pid = pid
        self._pid_to_name[pid] = name
        svc.state = ServiceState.RUNNING
        log.info("started service %s (pid=%d)", name, pid)

    def handle_exit(self, pid: int, status: int) -> None:
        name = self._pid_to_name.pop(pid, None)
        if name is None:
            return
        svc = self.services[name]
        if svc.oneshot:
            svc.state = ServiceState.STOPPED
            log.info("oneshot service %s finished (status=%d)", name, status)
            return

        if not svc.restart or svc.restart_count >= svc.restart_max:
            svc.state = ServiceState.FAILED
            log.error("service %s exited (status=%d) and will not be restarted", name, status)
            return

        svc.restart_count += 1
        svc.state = ServiceState.RESTARTING
        log.warning(
            "service %s exited (status=%d), restarting (%d/%d)",
            name, status, svc.restart_count, svc.restart_max,
        )
        self.start(name)

    def reap_once(self, blocking: bool = False) -> bool:
        """Reap one dead child if available. Returns True if one was reaped."""
        result = self.launcher.waitpid_any(blocking)
        if result is None:
            return False
        pid, status = result
        self.handle_exit(pid, status)
        return True

    def running_services(self) -> list[str]:
        return [n for n, s in self.services.items() if s.state == ServiceState.RUNNING]

    def shutdown(self, sig: int = signal.SIGTERM, timeout: float = 5.0) -> None:
        for svc in self.services.values():
            if svc.pid is not None and svc.state == ServiceState.RUNNING:
                try:
                    os.kill(svc.pid, sig)
                except ProcessLookupError:
                    continue
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self._pid_to_name:
            if not self.reap_once(blocking=False):
                time.sleep(0.05)
