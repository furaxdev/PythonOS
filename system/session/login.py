"""PythonOS login manager (SDDM-equivalent).

Architecture note: real SDDM is a greeter (QML UI) talking to a backend
that authenticates via PAM and then spawns the chosen session
(/usr/share/xsessions or wayland-sessions .desktop entries), tracked by
startplasma until the session's window manager exits. We studied that flow
(see docs/DESKTOP.md) and reimplemented the same shape independently in
Python:

  SessionDescriptor  -- like a .desktop session entry
  LoginManager        -- authenticates (via system.users.accounts) and
                          spawns the chosen session's exec command through
                          an injectable launcher, exactly like
                          system/init/manager.py does for services.

This is the auth + process-spawn logic only; the actual greeter UI and a
real compositor are separate (desktop/session, Phase 6+) and require a
display this development container doesn't have.
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from system.users.accounts import AuthenticationError, User, UserDatabase

DEFAULT_SESSIONS_DIR = Path("/usr/share/pythonos-sessions")


class LoginError(Exception):
    pass


@dataclass
class SessionDescriptor:
    name: str
    exec_command: list[str]
    session_type: str = "wayland"  # or "x11"

    @classmethod
    def from_file(cls, path: Path) -> "SessionDescriptor":
        parser = configparser.ConfigParser()
        parser.read(path)
        section = parser["Session"]
        return cls(
            name=section.get("Name", path.stem),
            exec_command=section["Exec"].split(),
            session_type=section.get("Type", "wayland"),
        )


def list_sessions(sessions_dir: Path = DEFAULT_SESSIONS_DIR) -> list[SessionDescriptor]:
    if not sessions_dir.exists():
        return []
    return [SessionDescriptor.from_file(p) for p in sorted(sessions_dir.glob("*.session"))]


class SessionLauncher:
    """Real process spawning. Substituted by a fake in tests, same pattern
    as system/init/manager.py's ProcessLauncher."""

    def spawn(self, argv: list[str], env: dict[str, str]) -> int:
        pid = os.fork()
        if pid == 0:
            os.execvpe(argv[0], argv, env)
        return pid


class LoginManager:
    def __init__(
        self,
        user_db: UserDatabase,
        sessions_dir: Path = DEFAULT_SESSIONS_DIR,
        launcher: SessionLauncher | None = None,
    ):
        self.user_db = user_db
        self.sessions_dir = sessions_dir
        self.launcher = launcher or SessionLauncher()
        self.active_sessions: dict[str, int] = {}  # username -> pid

    def available_sessions(self) -> list[SessionDescriptor]:
        return list_sessions(self.sessions_dir)

    def build_session_env(self, user: User, session: SessionDescriptor) -> dict[str, str]:
        env = dict(os.environ)
        env.update({
            "HOME": user.home,
            "USER": user.username,
            "LOGNAME": user.username,
            "SHELL": user.shell,
            "XDG_RUNTIME_DIR": f"/run/user/{user.uid}",
            "XDG_SESSION_TYPE": session.session_type,
            "XDG_CURRENT_DESKTOP": "PythonOS",
        })
        return env

    def login(self, username: str, password: str, session_name: str) -> int:
        """Authenticate and spawn the chosen session. Returns the PID.
        Raises AuthenticationError or LoginError on failure."""
        user = self.user_db.authenticate(username, password)  # raises AuthenticationError

        sessions = {s.name: s for s in self.available_sessions()}
        if session_name not in sessions:
            raise LoginError(f"no such session: {session_name!r}")
        session = sessions[session_name]

        env = self.build_session_env(user, session)
        pid = self.launcher.spawn(session.exec_command, env)
        self.active_sessions[username] = pid
        return pid

    def logout(self, username: str) -> None:
        self.active_sessions.pop(username, None)
