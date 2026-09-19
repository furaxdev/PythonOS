# PythonOS Boot Chain

```
QEMU / real hardware
     |
BIOS/UEFI -> SeaBIOS in our QEMU test
     |
Linux kernel (currently: distro linux-image-generic vmlinuz, unmodified)
     |
initramfs (build/initramfs.cpio.gz, built by scripts/build_initramfs.sh)
     |  contains: busybox (shell + core utils), a full python3 interpreter
     |  + stdlib, and the PythonOS system/ and shell/ source trees
     |
/init (a tiny busybox sh script): mounts /proc /sys /dev, then
     execs `python3 /pythonos/system/init/pyinit.py /etc/pythonos/services`
     |
PythonOS init (Python, PID 1) — system/init/pyinit.py
     |
ServiceManager starts services from system/services/examples/*.json
in dependency order (network, logger -> desktop-session)
```

## Building the initramfs

```bash
scripts/build_initramfs.sh
```

This copies busybox, a Python 3 interpreter and its shared-library closure,
a trimmed copy of the Python standard library, and the PythonOS `system/`
and `shell/` source trees into `build/initramfs-root/`, writes a `/init`
script, and packs everything into `build/initramfs.cpio.gz` (~18 MB).

## Boot-testing in QEMU

```bash
scripts/build_boot_test.sh          # rebuilds initramfs only if missing
scripts/build_boot_test.sh --rebuild # always rebuilds first
```

This boots `build/initramfs.cpio.gz` against the host's real Linux kernel
(`/boot/vmlinuz`, installed via `linux-image-generic`) under
`qemu-system-x86_64 -nographic`, with the serial console captured to
`build/boot.log`. The script fails (exit 1) unless the log contains
`PythonOS init starting`, i.e. unless a real Linux kernel actually handed
control to our Python init as PID 1.

An example successful run is checked in at
[boot-proof-example.log](boot-proof-example.log). Excerpt:

```
[initramfs] Linux kernel is up. Handing off to PythonOS init (Python).
[pyinit] PythonOS init starting (pid=1)
[pyinit] started service network (pid=87)
[pyinit] started service logger (pid=88)
network service placeholder
pythonos-logger alive
[pyinit] started service desktop-session (pid=89)
[pyinit] oneshot service network finished (status=0)
desktop session placeholder
[pyinit] oneshot service desktop-session finished (status=0)
pythonos-logger alive
```

`network` and `desktop-session` are currently placeholder oneshot services
(`system/services/examples/*.json`) exercising dependency ordering; they
are not yet the real network/desktop services described in the roadmap.

## Known issue

The kernel logs `mount: mounting sysfs on /sys failed: Device or resource
busy` and the same for `/dev` — this is because the busybox `/init` script
already mounts them before handing off to `pyinit.py`, which then tries
again defensively (so it also works if invoked directly as PID 1 without
that wrapper). Harmless, but noisy; a future pass should have `pyinit.py`
check `/proc/mounts` first.

## What's not yet real

- No bootloader (GRUB) stage — QEMU's `-kernel`/`-initrd` flags bypass it.
  Needed for Phase 10 (final bootable ISO).
- The kernel is the distro's stock `vmlinuz`, not a PythonOS-configured
  build.
- No disk-based root filesystem yet — everything currently runs from the
  initramfs (this is fine for a Live-style boot, which is one of the
  targets in section 19 of the spec, but the installer/Phase 9 needs a
  real root filesystem to install onto).
