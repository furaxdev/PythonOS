"""PythonOS user account management.

Stores accounts as JSON (system/users/accounts.py is backend-agnostic: the
on-disk format is a simple JSON database at a configurable path, defaulting
to /etc/pythonos/users.json). Passwords are never stored in plaintext —
they're hashed with PBKDF2-HMAC-SHA256 and a per-user random salt, in the
same spirit as a shadow file.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_DB_PATH = Path("/etc/pythonos/users.json")
PBKDF2_ITERATIONS = 310_000


class UserError(Exception):
    pass


class UserExistsError(UserError):
    pass


class UserNotFoundError(UserError):
    pass


class AuthenticationError(UserError):
    pass


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, computed = _hash_password(password, salt)
    return secrets.compare_digest(computed, hash_hex)


@dataclass
class User:
    username: str
    uid: int
    gid: int
    home: str
    shell: str = "/usr/bin/pysh"
    groups: list[str] = field(default_factory=list)
    salt: str = ""
    password_hash: str = ""
    locked: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(**data)


@dataclass
class Group:
    name: str
    gid: int
    members: list[str] = field(default_factory=list)


class UserDatabase:
    """Loads/saves accounts from a JSON file and enforces the usual
    invariants (unique username, unique uid, uid/gid allocation)."""

    FIRST_UID = 1000

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.users: dict[str, User] = {}
        self.groups: dict[str, Group] = {}
        if self.db_path.exists():
            self.load()

    def load(self) -> None:
        data = json.loads(self.db_path.read_text())
        self.users = {u["username"]: User.from_dict(u) for u in data.get("users", [])}
        self.groups = {g["name"]: Group(**g) for g in data.get("groups", [])}

    def save(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "users": [u.to_dict() for u in self.users.values()],
            "groups": [asdict(g) for g in self.groups.values()],
        }
        tmp = self.db_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2))
        os.chmod(tmp, 0o600)
        tmp.replace(self.db_path)

    def _next_uid(self) -> int:
        used = {u.uid for u in self.users.values()}
        candidate = self.FIRST_UID
        while candidate in used:
            candidate += 1
        return candidate

    def _next_gid(self) -> int:
        used = {g.gid for g in self.groups.values()}
        candidate = self.FIRST_UID
        while candidate in used:
            candidate += 1
        return candidate

    def create_group(self, name: str, gid: int | None = None) -> Group:
        if name in self.groups:
            raise UserExistsError(f"group {name!r} already exists")
        group = Group(name=name, gid=gid if gid is not None else self._next_gid())
        self.groups[name] = group
        return group

    def create_user(
        self,
        username: str,
        password: str,
        home: str | None = None,
        shell: str = "/usr/bin/pysh",
        extra_groups: list[str] | None = None,
    ) -> User:
        if username in self.users:
            raise UserExistsError(f"user {username!r} already exists")
        if not username or not username[0].isalpha() or " " in username:
            raise UserError(f"invalid username: {username!r}")

        primary_group = self.groups.get(username) or self.create_group(username)
        salt, pwhash = _hash_password(password)
        user = User(
            username=username,
            uid=self._next_uid(),
            gid=primary_group.gid,
            home=home or f"/home/{username}",
            shell=shell,
            groups=[username] + (extra_groups or []),
            salt=salt,
            password_hash=pwhash,
        )
        self.users[username] = user
        primary_group.members.append(username)
        for gname in extra_groups or []:
            group = self.groups.get(gname) or self.create_group(gname)
            if username not in group.members:
                group.members.append(username)
        return user

    def delete_user(self, username: str) -> None:
        if username not in self.users:
            raise UserNotFoundError(f"user {username!r} not found")
        del self.users[username]
        for group in self.groups.values():
            if username in group.members:
                group.members.remove(username)

    def set_password(self, username: str, new_password: str) -> None:
        user = self._require_user(username)
        user.salt, user.password_hash = _hash_password(new_password)

    def authenticate(self, username: str, password: str) -> User:
        user = self._require_user(username)
        if user.locked:
            raise AuthenticationError(f"account {username!r} is locked")
        if not user.password_hash or not _verify_password(password, user.salt, user.password_hash):
            raise AuthenticationError("invalid credentials")
        return user

    def lock_user(self, username: str) -> None:
        self._require_user(username).locked = True

    def unlock_user(self, username: str) -> None:
        self._require_user(username).locked = False

    def add_to_group(self, username: str, group_name: str) -> None:
        user = self._require_user(username)
        group = self.groups.get(group_name) or self.create_group(group_name)
        if group_name not in user.groups:
            user.groups.append(group_name)
        if username not in group.members:
            group.members.append(username)

    def _require_user(self, username: str) -> User:
        user = self.users.get(username)
        if user is None:
            raise UserNotFoundError(f"user {username!r} not found")
        return user
