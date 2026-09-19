#!/usr/bin/env python3
"""PythonOS init — PID 1.

Run as the first userspace process by the initramfs. Mounts the standard
kernel filesystems, starts services from /etc/pythonos/services (or a
directory passed as argv[1] for testing), reaps zombies, and handles
SIGTERM/SIGINT as shutdown/reboot requests.

This file is intentionally thin: all the logic that can be unit tested
without being PID 1 lives in system/init/manager.py and service.py.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from system.init.manager import ServiceManager  # noqa: E402

log = logging.getLogger("pythonos.init")

DEFAULT_SERVICES_DIR = Path("/etc/pythonos/services")

_shutdown_requested = False
_reboot_requested = False


def _mount_kernel_filesystems() -> None:
    """Mount /proc, /sys, /dev if not already mounted. No-ops (with a log
    line) when not actually running as PID 1, e.g. under a unit test."""
    if os.getpid() != 1:
        log.info("not PID 1 (pid=%d); skipping kernel filesystem mounts", os.getpid())
        return

    mounts = [
        ("proc", "/proc", "proc"),
        ("sysfs", "/sys", "sysfs"),
        ("devtmpfs", "/dev", "devtmpfs"),
    ]
    for source, target, fstype in mounts:
        Path(target).mkdir(parents=True, exist_ok=True)
        try:
            os.system(f"mount -t {fstype} {source} {target}")
        except OSError as exc:
            log.error("failed to mount %s on %s: %s", fstype, target, exc)


def _handle_term(signum, frame) -> None:
    global _shutdown_requested
    _shutdown_requested = True


def _handle_reboot(signum, frame) -> None:
    global _reboot_requested
    _reboot_requested = True


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="[pyinit] %(message)s")
    log.info("PythonOS init starting (pid=%d)", os.getpid())

    _mount_kernel_filesystems()

    services_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_SERVICES_DIR
    if not services_dir.exists():
        log.warning("services directory %s does not exist; nothing to start", services_dir)
        manager = None
    else:
        manager = ServiceManager(services_dir)
        manager.start_all()

    signal.signal(signal.SIGTERM, _handle_term)
    signal.signal(signal.SIGUSR1, _handle_reboot)

    while not _shutdown_requested and not _reboot_requested:
        if manager is not None:
            manager.reap_once(blocking=False)
        time.sleep(0.2)

    log.info("shutdown requested, stopping services")
    if manager is not None:
        manager.shutdown()

    if os.getpid() == 1:
        os.system("poweroff -f" if _shutdown_requested else "reboot -f")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
