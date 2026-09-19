"""PythonOS network interface management.

Reads real interface state from sysfs/procfs (no netlink library dependency,
in keeping with the "Python first" philosophy: this is pure Python against
kernel-exposed files, not a shellout to `ip`). Configuration (up/down, IP
assignment) goes through raw ioctl calls on a socket, which is what
iproute2/net-tools do under the hood — wrapped behind a `Syscalls`
interface so it's unit-testable without root or real network devices.
"""

from __future__ import annotations

import fcntl
import socket
import struct
from dataclasses import dataclass
from pathlib import Path

SYS_CLASS_NET = Path("/sys/class/net")
PROC_NET_DEV = Path("/proc/net/dev")

SIOCGIFFLAGS = 0x8913
SIOCSIFFLAGS = 0x8914
SIOCSIFADDR = 0x8916
SIOCSIFNETMASK = 0x891B
IFF_UP = 0x1


class NetworkError(Exception):
    pass


@dataclass
class InterfaceStats:
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int


@dataclass
class Interface:
    name: str
    mac_address: str
    operstate: str
    mtu: int
    is_up: bool
    stats: InterfaceStats | None = None


def _read_stripped(path: Path, default: str = "") -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return default


def _parse_proc_net_dev() -> dict[str, InterfaceStats]:
    stats: dict[str, InterfaceStats] = {}
    if not PROC_NET_DEV.exists():
        return stats
    lines = PROC_NET_DEV.read_text().splitlines()[2:]
    for line in lines:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        fields = rest.split()
        stats[name.strip()] = InterfaceStats(
            rx_bytes=int(fields[0]), rx_packets=int(fields[1]),
            tx_bytes=int(fields[8]), tx_packets=int(fields[9]),
        )
    return stats


def list_interfaces() -> list[Interface]:
    """Real interface enumeration via /sys/class/net; returns [] if the
    directory doesn't exist (e.g. non-Linux dev host running the unit
    tests in isolation)."""
    if not SYS_CLASS_NET.exists():
        return []

    all_stats = _parse_proc_net_dev()
    interfaces = []
    for entry in sorted(SYS_CLASS_NET.iterdir()):
        name = entry.name
        operstate = _read_stripped(entry / "operstate", "unknown")
        mac = _read_stripped(entry / "address", "00:00:00:00:00:00")
        mtu_raw = _read_stripped(entry / "mtu", "0")
        flags_raw = _read_stripped(entry / "flags", "0x0")
        try:
            flags = int(flags_raw, 16)
        except ValueError:
            flags = 0
        interfaces.append(Interface(
            name=name,
            mac_address=mac,
            operstate=operstate,
            mtu=int(mtu_raw) if mtu_raw.isdigit() else 0,
            is_up=bool(flags & IFF_UP),
            stats=all_stats.get(name),
        ))
    return interfaces


def get_interface(name: str) -> Interface:
    for iface in list_interfaces():
        if iface.name == name:
            return iface
    raise NetworkError(f"no such interface: {name!r}")


class Syscalls:
    """Thin wrapper around the ioctl calls needed to configure an
    interface. Separated out so ServiceManager-style tests can substitute
    a fake without needing CAP_NET_ADMIN or real hardware."""

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def set_flags_up(self, name: str, up: bool) -> None:
        ifreq = struct.pack("16sh", name.encode(), 0)
        flags = struct.unpack("16sh", fcntl.ioctl(self._sock, SIOCGIFFLAGS, ifreq))[1]
        if up:
            flags |= IFF_UP
        else:
            flags &= ~IFF_UP
        ifreq = struct.pack("16sh", name.encode(), flags)
        fcntl.ioctl(self._sock, SIOCSIFFLAGS, ifreq)

    def set_address(self, name: str, ip_address: str) -> None:
        packed = socket.inet_aton(ip_address)
        ifreq = struct.pack("16sH2s4s8s", name.encode(), socket.AF_INET, b"\x00" * 2, packed, b"\x00" * 8)
        fcntl.ioctl(self._sock, SIOCSIFADDR, ifreq)

    def set_netmask(self, name: str, netmask: str) -> None:
        packed = socket.inet_aton(netmask)
        ifreq = struct.pack("16sH2s4s8s", name.encode(), socket.AF_INET, b"\x00" * 2, packed, b"\x00" * 8)
        fcntl.ioctl(self._sock, SIOCSIFNETMASK, ifreq)


class NetworkManager:
    """High-level operations used by the network service and settings UI.
    All state-changing calls go through `syscalls` so they can be tested
    without touching real interfaces."""

    def __init__(self, syscalls: Syscalls | None = None):
        self._syscalls = syscalls

    @property
    def syscalls(self) -> Syscalls:
        if self._syscalls is None:
            self._syscalls = Syscalls()
        return self._syscalls

    def bring_up(self, name: str) -> None:
        self.syscalls.set_flags_up(name, True)

    def bring_down(self, name: str) -> None:
        self.syscalls.set_flags_up(name, False)

    def configure_static(self, name: str, ip_address: str, netmask: str = "255.255.255.0") -> None:
        self.syscalls.set_address(name, ip_address)
        self.syscalls.set_netmask(name, netmask)
        self.bring_up(name)
