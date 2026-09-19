import io
from pathlib import Path

import pytest

from shell.core import Shell, ShellState, parse_pipeline, ParseError


def make_shell(tmp_path):
    state = ShellState(cwd=tmp_path, env={"HOME": str(tmp_path)})
    out = io.StringIO()
    err = io.StringIO()
    shell = Shell(state=state, stdout=out, stderr=err)
    return shell, out, err


def test_parse_pipeline_splits_on_pipe():
    state = ShellState(cwd=Path("/"))
    cmds = parse_pipeline("ls | grep foo", state)
    assert [c.argv for c in cmds] == [["ls"], ["grep", "foo"]]


def test_parse_pipeline_redirection():
    state = ShellState(cwd=Path("/"))
    cmds = parse_pipeline("cat a.txt > out.txt", state)
    assert cmds[0].argv == ["cat", "a.txt"]
    assert cmds[0].stdout_file == "out.txt"
    assert cmds[0].append_stdout is False


def test_parse_pipeline_empty_raises_on_empty_command():
    state = ShellState(cwd=Path("/"))
    with pytest.raises(ParseError):
        parse_pipeline("| ls", state)


def test_pwd_and_cd(tmp_path):
    shell, out, err = make_shell(tmp_path)
    sub = tmp_path / "sub"
    sub.mkdir()

    shell.run_line("cd sub")
    shell.run_line("pwd")
    assert out.getvalue().strip() == str(sub)


def test_mkdir_ls_and_cat(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.run_line("mkdir newdir")
    assert (tmp_path / "newdir").is_dir()

    (tmp_path / "hello.txt").write_text("hi there")
    shell.run_line("cat hello.txt")
    assert out.getvalue().strip() == "hi there"


def test_cp_mv_rm(tmp_path):
    shell, out, err = make_shell(tmp_path)
    (tmp_path / "a.txt").write_text("data")

    shell.run_line("cp a.txt b.txt")
    assert (tmp_path / "b.txt").read_text() == "data"

    shell.run_line("mv b.txt c.txt")
    assert not (tmp_path / "b.txt").exists()
    assert (tmp_path / "c.txt").exists()

    shell.run_line("rm c.txt")
    assert not (tmp_path / "c.txt").exists()


def test_redirection_writes_file(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.run_line("echo hello world > greeting.txt")
    assert (tmp_path / "greeting.txt").read_text().strip() == "hello world"


def test_append_redirection(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.run_line("echo one > f.txt")
    shell.run_line("echo two >> f.txt")
    content = (tmp_path / "f.txt").read_text()
    assert content == "one\ntwo\n"


def test_alias_and_history(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.run_line("alias ll=ls")
    assert shell.state.aliases["ll"] == "ls"

    shell.run_line("echo hi")
    shell.run_line("history")
    history_output = out.getvalue()
    assert "echo hi" in history_output


def test_export_sets_env(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.run_line("export FOO=bar")
    assert shell.state.env["FOO"] == "bar"


def test_variable_expansion(tmp_path):
    shell, out, err = make_shell(tmp_path)
    shell.state.env["GREETING"] = "hello"
    shell.run_line("echo $GREETING")
    assert out.getvalue().strip() == "hello"


def test_unknown_command_returns_127(tmp_path):
    shell, out, err = make_shell(tmp_path)
    status = shell.run_line("this_command_does_not_exist_xyz")
    assert status == 127


def test_exit_raises_systemexit(tmp_path):
    shell, out, err = make_shell(tmp_path)
    with pytest.raises(SystemExit) as exc_info:
        shell.run_line("exit 3")
    assert exc_info.value.code == 3
