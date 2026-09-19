# PythonOS — Roadmap & Status

Legend: `IMPLEMENTED` (works, tested) · `PARTIAL` (works but incomplete) · `PLANNED` (not started) · `BLOCKED` (can't proceed, reason given)

This file is the single source of truth for what actually works. A UI element
without a working backend is never marked `IMPLEMENTED`.

## Phase 0 — Audit
`IMPLEMENTED` — Environment audited 2026-09-19: empty repo (no commits), Ubuntu
noble container, Python 3.11.15, network + apt access available, no qemu/xorriso/
grub-mkrescue/debootstrap preinstalled (installable via apt), no GPU/display.

## Phase 1 — Boot (kernel, initramfs, first QEMU boot)
`PARTIAL` — see `docs/BOOT.md` for the current boot chain and its proof log.

## Phase 2 — Init (Python)
`PARTIAL` — see `docs/ARCHITECTURE.md#init`. Service manager implemented and
unit-tested; not yet wired as real PID 1 inside the initramfs boot chain.

## Phase 3 — System services (users, network, audio, power, devices)
`PARTIAL` — users, network, and power are implemented and unit-tested (37
tests across the three). Audio and devices are `PLANNED`.

- `system/users/accounts.py` — `UserDatabase`: create/delete users, groups,
  PBKDF2-hashed passwords (never plaintext), lock/unlock, JSON persistence.
  CLI: `tools/pyos-user` (add/del/passwd/lock/unlock/list).
- `system/network/interfaces.py` — real interface enumeration via
  `/sys/class/net` + `/proc/net/dev` (no netlink lib, no shelling out to
  `ip`); `NetworkManager` configures interfaces (up/down, static IP) via
  raw ioctl on a socket, injectable for testing.
- `system/power/power.py` — battery/AC state via `/sys/class/power_supply`;
  `PowerManager` for poweroff/reboot/suspend, with an injectable
  `ActionRunner` for testing.

## Phase 4 — PythonOS Shell (pysh)
`PARTIAL` — see `docs/SHELL.md`.

## Phase 5 — Graphical session
`PLANNED` — blocked on no GPU/display in this container; needs a virtual
framebuffer (Xvfb/virtio-gpu under QEMU) to develop against. See BLOCKED notes
in ARCHITECTURE.md.

## Phase 6 — Desktop (panel, launcher, notifications, widgets, virtual desktops, search, settings)
`PLANNED`

## Phase 7 — Applications
`PLANNED`

## Phase 8 — Package manager
`PLANNED`

## Phase 9 — Installer
`PLANNED`

## Phase 10 — Final ISO
`PLANNED`

## Phase 11 — Polish
`PLANNED`

## Next up
1. Finish Phase 3: `system/audio`, `system/devices`.
2. Wire real service units (users/network/power) into the initramfs boot
   chain as actual PID-1-managed services, replacing the placeholder
   oneshot examples.
3. Start Phase 5 (graphical session) — needs a virtual framebuffer
   strategy decided first (see BLOCKED note above).
