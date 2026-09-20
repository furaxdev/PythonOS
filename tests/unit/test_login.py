from pathlib import Path

import pytest

from system.session.login import (
    LoginError,
    LoginManager,
    SessionDescriptor,
    list_sessions,
)
from system.users.accounts import AuthenticationError, UserDatabase


def write_session_file(path: Path, name: str, exec_cmd: str, session_type="wayland"):
    path.write_text(f"[Session]\nName={name}\nExec={exec_cmd}\nType={session_type}\n")


def make_login_manager(tmp_path, launcher=None):
    db = UserDatabase(tmp_path / "users.json")
    db.create_user("furax", "hunter2")
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    write_session_file(sessions_dir / "pythonos.session", "PythonOS", "/usr/bin/pythonos-shell-session")
    return LoginManager(db, sessions_dir=sessions_dir, launcher=launcher), db


def test_list_sessions_parses_session_files(tmp_path):
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    write_session_file(sessions_dir / "pythonos.session", "PythonOS", "/usr/bin/plasma-equivalent --wayland")

    sessions = list_sessions(sessions_dir)
    assert len(sessions) == 1
    assert sessions[0].name == "PythonOS"
    assert sessions[0].exec_command == ["/usr/bin/plasma-equivalent", "--wayland"]


def test_list_sessions_missing_dir_returns_empty(tmp_path):
    assert list_sessions(tmp_path / "nope") == []


class FakeSessionLauncher:
    def __init__(self):
        self.spawned: list[tuple[list[str], dict]] = []

    def spawn(self, argv, env):
        self.spawned.append((argv, env))
        return 4242


def test_login_success_authenticates_and_spawns_session(tmp_path):
    fake_launcher = FakeSessionLauncher()
    manager, db = make_login_manager(tmp_path, launcher=fake_launcher)

    pid = manager.login("furax", "hunter2", "PythonOS")

    assert pid == 4242
    assert manager.active_sessions["furax"] == 4242
    argv, env = fake_launcher.spawned[0]
    assert argv == ["/usr/bin/pythonos-shell-session"]
    assert env["USER"] == "furax"
    assert env["HOME"] == db.users["furax"].home
    assert env["XDG_SESSION_TYPE"] == "wayland"


def test_login_wrong_password_raises(tmp_path):
    manager, _ = make_login_manager(tmp_path, launcher=FakeSessionLauncher())
    with pytest.raises(AuthenticationError):
        manager.login("furax", "wrong", "PythonOS")


def test_login_unknown_session_raises(tmp_path):
    manager, _ = make_login_manager(tmp_path, launcher=FakeSessionLauncher())
    with pytest.raises(LoginError):
        manager.login("furax", "hunter2", "NoSuchSession")


def test_logout_clears_active_session(tmp_path):
    fake_launcher = FakeSessionLauncher()
    manager, _ = make_login_manager(tmp_path, launcher=fake_launcher)
    manager.login("furax", "hunter2", "PythonOS")
    assert "furax" in manager.active_sessions

    manager.logout("furax")
    assert "furax" not in manager.active_sessions
