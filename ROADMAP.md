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
`PLANNED`

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
1. Wire `system/init/pyinit.py` as actual PID 1 inside the initramfs (currently
   boot-tested standalone; integration into the initramfs init chain is next).
2. Expand `pysh` builtins (pipes/redirection are implemented; job control is not).
3. Start Phase 3 (system/users) once init integration is solid.
