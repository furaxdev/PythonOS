# PythonOS Login & Session Management

Modeled on the real SDDM (display manager) + startplasma + ksmserver flow
in KDE Plasma — architecture studied from public documentation and source
layout (see sources below), reimplemented independently in Python; no KDE
code was copied.

```
LoginManager (system/session/login.py)      -- SDDM-equivalent
     |  authenticates via system.users.accounts.UserDatabase
     |  picks a SessionDescriptor (.session file, like a .desktop
     |  xsessions/wayland-sessions entry)
     |  builds the session environment (HOME, XDG_RUNTIME_DIR, ...)
     |  spawns the session's Exec command
     v
SessionManager (system/session/manager.py)  -- ksmserver-equivalent
     |  starts session Components in dependency order
     |  restarts non-primary components on crash
     |  ends the session when the primary component exits
     v
desktop/session/pythonos_shell_session.py   -- today's only real session:
                                                a headless pysh session,
                                                used as the primary
                                                component in place of a
                                                compositor
```

## Try it

```bash
python3 tools/pyos-user --db /tmp/db.json add myuser
mkdir -p /tmp/sessions
cp system/session/examples/pythonos-shell-dev.session /tmp/sessions/
python3 tools/pyos-login /tmp/db.json /tmp/sessions
```

This authenticates for real (PBKDF2-hashed password check) and forks +
execs the real session process — you land in a live `pysh` prompt.

## What's real vs. what's not

- Real: authentication, session-file parsing, environment construction,
  process spawn/supervision, dependency-ordered component startup,
  restart-on-crash for non-primary components, session-end detection.
- Not yet real: there is no graphical compositor or shell to spawn as the
  primary component — `desktop/session/pythonos_shell_session.py` stands
  in for one. Building an actual compositor needs a display (GPU or
  virtual framebuffer), which this development container doesn't have;
  see ROADMAP.md's Phase 5 BLOCKED note.
- Not yet real: no PAM integration — authentication is PythonOS's own
  `UserDatabase`, not pluggable auth modules. Reasonable for a
  from-scratch OS; worth revisiting if PythonOS ever needs to
  interoperate with existing Linux PAM stacks.

## Sources consulted for the architecture (not code)

- [SDDM — ArchWiki](https://wiki.archlinux.org/title/SDDM)
- [plasma-workspace/startkde — KDE GitHub mirror](https://github.com/KDE/plasma-workspace/tree/master/startkde)
- [ksmserver README — KDE GitHub mirror](https://github.com/KDE/plasma-workspace/blob/master/ksmserver/README)
