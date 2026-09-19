import pytest

from system.users.accounts import (
    AuthenticationError,
    UserDatabase,
    UserError,
    UserExistsError,
    UserNotFoundError,
)


def make_db(tmp_path):
    return UserDatabase(tmp_path / "users.json")


def test_create_user_allocates_uid_and_group(tmp_path):
    db = make_db(tmp_path)
    user = db.create_user("furax", "hunter2")
    assert user.uid == 1000
    assert "furax" in db.groups
    assert db.groups["furax"].gid == user.gid
    assert user.username in db.groups["furax"].members


def test_passwords_are_never_stored_in_plaintext(tmp_path):
    db = make_db(tmp_path)
    user = db.create_user("furax", "hunter2")
    assert "hunter2" not in user.password_hash
    assert user.password_hash != "hunter2"
    assert len(user.password_hash) == 64  # sha256 hex digest


def test_authenticate_success_and_failure(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "correct-horse")

    authenticated = db.authenticate("furax", "correct-horse")
    assert authenticated.username == "furax"

    with pytest.raises(AuthenticationError):
        db.authenticate("furax", "wrong-password")


def test_duplicate_username_rejected(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "pw")
    with pytest.raises(UserExistsError):
        db.create_user("furax", "pw2")


def test_invalid_username_rejected(tmp_path):
    db = make_db(tmp_path)
    with pytest.raises(UserError):
        db.create_user("1invalid", "pw")
    with pytest.raises(UserError):
        db.create_user("bad name", "pw")


def test_delete_user_removes_from_groups(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "pw", extra_groups=["wheel"])
    assert "furax" in db.groups["wheel"].members

    db.delete_user("furax")
    assert "furax" not in db.users
    assert "furax" not in db.groups["wheel"].members


def test_delete_missing_user_raises(tmp_path):
    db = make_db(tmp_path)
    with pytest.raises(UserNotFoundError):
        db.delete_user("ghost")


def test_lock_prevents_authentication(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "pw")
    db.lock_user("furax")
    with pytest.raises(AuthenticationError):
        db.authenticate("furax", "pw")

    db.unlock_user("furax")
    db.authenticate("furax", "pw")  # should not raise


def test_set_password_changes_hash_and_invalidates_old(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "old-pw")
    db.set_password("furax", "new-pw")

    with pytest.raises(AuthenticationError):
        db.authenticate("furax", "old-pw")
    db.authenticate("furax", "new-pw")


def test_persistence_round_trip(tmp_path):
    db_path = tmp_path / "users.json"
    db = UserDatabase(db_path)
    db.create_user("furax", "pw", extra_groups=["wheel"])
    db.save()

    reloaded = UserDatabase(db_path)
    assert "furax" in reloaded.users
    assert reloaded.users["furax"].uid == db.users["furax"].uid
    reloaded.authenticate("furax", "pw")


def test_add_to_group_creates_group_if_missing(tmp_path):
    db = make_db(tmp_path)
    db.create_user("furax", "pw")
    db.add_to_group("furax", "audio")
    assert "audio" in db.groups
    assert "furax" in db.groups["audio"].members
    assert "audio" in db.users["furax"].groups


def test_next_uid_reuses_gaps_after_delete(tmp_path):
    db = make_db(tmp_path)
    db.create_user("a", "pw")
    b = db.create_user("b", "pw")
    db.delete_user("a")
    c = db.create_user("c", "pw")
    # 1000 (a) freed, so c should reuse it rather than climbing forever
    assert c.uid == 1000
    assert b.uid == 1001
