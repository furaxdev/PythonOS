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
`PARTIAL` — the login/session-management architecture (the SDDM +
ksmserver equivalent) is implemented and unit-tested; a real compositor
and graphical shell are `BLOCKED` (no GPU/display in this container — see
below).

- `system/session/login.py` — `LoginManager`: authenticates against
  `UserDatabase`, parses session descriptors (`.session` files, same idea
  as `.desktop` xsessions/wayland-sessions entries), builds the session
  environment (`HOME`, `XDG_RUNTIME_DIR`, `XDG_SESSION_TYPE`, ...), and
  spawns the chosen session. CLI: `tools/pyos-login`.
- `system/session/manager.py` — `SessionManager`: supervises a session's
  components in dependency order (reusing the init system's dependency
  resolver), restarts non-primary components on crash, and ends the
  session when the primary component (the compositor, once it exists)
  exits — modeled on ksmserver's relationship to kwin.
- `desktop/session/pythonos_shell_session.py` — the one real working
  session today: a headless `pysh` session, used as the `SessionManager`
  primary component in place of a compositor. Proven end-to-end: login →
  authenticate → spawn → land in a live `pysh` prompt (manually verified;
  see docs/SESSION.md).
- `BLOCKED`: an actual graphical compositor + shell needs a display this
  development container does not have (no GPU, no framebuffer). Options
  researched: Xvfb (X11 virtual framebuffer) or QEMU's virtio-gpu console
  for a real, screenshot-able target. Next session should set one of
  these up before attempting Phase 6.

## Phase 6 — Desktop (panel, launcher, notifications, widgets, virtual desktops, search, settings)
`PARTIAL` — graphics stack decided and proven (PySide6/Qt, rendering
verified both under Xvfb and headless `offscreen`, see docs/DESKTOP.md).
Panel and launcher are real, working Qt widgets, now restyled to closely
match the KDE Plasma/Breeze look: a real theme engine
(`desktop/theme/theme_manager.py`, two themes — PythonOS Dark/Light,
palettes inspired by public Breeze color values, QSS written from
scratch), a Kickoff-style launcher (search bar + category sidebar + app
list, see `desktop/launcher/launcher_widget.py`), and a gradient desktop
background (`desktop/background/wallpaper_widget.py`). Window management
is real: `desktop/windows/wm.py` is a working X11 window manager
(python-xlib) proven against real X11 clients under Xvfb, wired to the
panel's task manager in `desktop/session/graphical_session.py` — see
docs/WINDOWS.md. **Window decorations are now real too**: every client is
reparented into a frame with a drawn titlebar and working
minimize/maximize/close buttons (verified via `query_tree()` reparenting
+ a synthetic click on the real close button's coordinates actually
closing the real client — see docs/WINDOWS.md). PythonOS's own shell
chrome (wallpaper/panel/launcher) is override-redirect so it stays
undecorated, same technique a real desktop's panel/dock uses. Full
assembled desktop proof (wallpaper + styled panel + open launcher + a
real window with a working titlebar) at
docs/window-decorations-proof.png. 77 unit tests pass in total (up from
64). No window dragging/resizing, no focus handling, no multi-monitor,
close is forceful (no WM_DELETE_WINDOW) yet. Notifications, widgets
(plasmoids), virtual desktops, global search, and settings app are
`PLANNED`.

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
1. Notifications center, KRunner-equivalent global search, settings app.
2. Make `GraphicalSession` an actual `SessionManager` component (today
   it's started directly for dev/test, not through `LoginManager` →
   `SessionManager` → primary component).
3. Finish Phase 3: `system/audio`, `system/devices`.
4. Wire real service units (users/network/power/login) into the
   initramfs boot chain, replacing the placeholder oneshot examples.
5. Phase 7 apps (file manager, text editor, calculator, system monitor),
   Phase 8 package manager, Phase 9 installer, Phase 10 bootable ISO
   (GRUB) so it can run in VirtualBox too, Phase 11 polish.
