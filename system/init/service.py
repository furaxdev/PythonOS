"""Service definitions and dependency resolution for PythonOS init."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    RESTARTING = "restarting"


@dataclass
class Service:
    name: str
    exec_start: list[str]
    depends_on: list[str] = field(default_factory=list)
    restart: bool = True
    restart_max: int = 5
    oneshot: bool = False

    state: ServiceState = field(default=ServiceState.STOPPED, compare=False)
    pid: int | None = field(default=None, compare=False)
    restart_count: int = field(default=0, compare=False)

    @classmethod
    def from_file(cls, path: Path) -> "Service":
        data = json.loads(path.read_text())
        return cls(
            name=data["name"],
            exec_start=data["exec_start"],
            depends_on=data.get("depends_on", []),
            restart=data.get("restart", True),
            restart_max=data.get("restart_max", 5),
            oneshot=data.get("oneshot", False),
        )


class DependencyError(Exception):
    pass


def load_services(services_dir: Path) -> dict[str, Service]:
    """Load every *.json service unit in a directory."""
    services: dict[str, Service] = {}
    for path in sorted(services_dir.glob("*.json")):
        svc = Service.from_file(path)
        services[svc.name] = svc
    return services


def resolve_start_order(services: dict[str, Service]) -> list[str]:
    """Topologically sort services by depends_on. Raises DependencyError on
    missing dependencies or a dependency cycle."""
    for svc in services.values():
        for dep in svc.depends_on:
            if dep not in services:
                raise DependencyError(f"{svc.name} depends on unknown service {dep!r}")

    order: list[str] = []
    visited: dict[str, int] = {}  # 0 = in-progress, 1 = done

    def visit(name: str, stack: list[str]) -> None:
        state = visited.get(name)
        if state == 1:
            return
        if state == 0:
            cycle = " -> ".join(stack + [name])
            raise DependencyError(f"dependency cycle detected: {cycle}")
        visited[name] = 0
        for dep in services[name].depends_on:
            visit(dep, stack + [name])
        visited[name] = 1
        order.append(name)

    for name in services:
        visit(name, [])

    return order
