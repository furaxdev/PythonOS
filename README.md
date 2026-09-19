# PythonOS

A real, bootable operating system: the Linux kernel underneath, a Python
user space on top. Init, services, shell, and (eventually) the desktop are
all Python. The kernel is the one deliberate exception — see
[ARCHITECTURE.md](docs/ARCHITECTURE.md) for why.

```
Linux kernel → initramfs → PythonOS init (Python) → services → shell / desktop
```

## Status

This project is under active, incremental development. Nothing here is a
mockup: every component marked `IMPLEMENTED` in [ROADMAP.md](ROADMAP.md) has
a real backend and a test proving it. Read that file for the honest current
state before assuming a feature works.

## Repository layout

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full layout and design
rationale.

## Quick start (development)

```bash
# Run the unit test suite
python3 -m pytest tests/unit -v

# Try the PythonOS shell locally (no boot required)
python3 shell/pysh.py

# Build and boot-test the minimal kernel + initramfs in QEMU
scripts/build_boot_test.sh
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design
- [BOOT.md](docs/BOOT.md) — kernel/initramfs boot chain and QEMU test
- [SHELL.md](docs/SHELL.md) — the `pysh` shell
- [ROADMAP.md](ROADMAP.md) — phase-by-phase honest status
