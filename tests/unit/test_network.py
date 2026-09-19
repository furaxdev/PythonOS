from system.network.interfaces import (
    Interface,
    InterfaceStats,
    NetworkError,
    NetworkManager,
    get_interface,
    list_interfaces,
)


def test_list_interfaces_reads_real_sysfs():
    """This runs against the real container's /sys/class/net, so it's an
    integration-flavored unit test: it proves we actually parse sysfs
    correctly, not a fixture we made up."""
    interfaces = list_interfaces()
    names = [i.name for i in interfaces]
    assert "lo" in names

    loopback = next(i for i in interfaces if i.name == "lo")
    assert isinstance(loopback, Interface)
    assert loopback.mac_address == "00:00:00:00:00:00"


def test_get_interface_found_and_not_found():
    lo = get_interface("lo")
    assert lo.name == "lo"

    try:
        get_interface("definitely-not-a-real-iface-xyz")
        assert False, "expected NetworkError"
    except NetworkError:
        pass


def test_interface_stats_parsed_from_proc_net_dev():
    lo = get_interface("lo")
    assert lo.stats is not None
    assert isinstance(lo.stats, InterfaceStats)
    assert lo.stats.rx_bytes >= 0


class FakeSyscalls:
    def __init__(self):
        self.calls: list[tuple] = []

    def set_flags_up(self, name, up):
        self.calls.append(("flags", name, up))

    def set_address(self, name, ip_address):
        self.calls.append(("address", name, ip_address))

    def set_netmask(self, name, netmask):
        self.calls.append(("netmask", name, netmask))


def test_network_manager_bring_up_down():
    fake = FakeSyscalls()
    manager = NetworkManager(syscalls=fake)

    manager.bring_up("eth0")
    manager.bring_down("eth0")

    assert fake.calls == [("flags", "eth0", True), ("flags", "eth0", False)]


def test_network_manager_configure_static():
    fake = FakeSyscalls()
    manager = NetworkManager(syscalls=fake)

    manager.configure_static("eth0", "192.168.1.50", "255.255.255.0")

    assert ("address", "eth0", "192.168.1.50") in fake.calls
    assert ("netmask", "eth0", "255.255.255.0") in fake.calls
    assert ("flags", "eth0", True) in fake.calls
