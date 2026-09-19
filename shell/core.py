"""PythonOS shell (pysh) — parsing and execution core.

Kept separate from the REPL entrypoint (pysh.py) so it can be unit tested
without a real terminal.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Command:
    argv: list[str]
    stdin_file: str | None = None
    stdout_file: str | None = None
    append_stdout: bool = False


@dataclass
class ShellState:
    cwd: Path = field(default_factory=Path.cwd)
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))
    aliases: dict[str, str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    last_status: int = 0


class ParseError(Exception):
    pass


REDIRECT_TOKENS = {">", ">>", "<"}


def expand(word: str, state: ShellState) -> str:
    if word.startswith("$") and len(word) > 1 and word[1:].isidentifier():
        return state.env.get(word[1:], "")
    if word == "~":
        return str(Path.home())
    return word


def parse_segment(tokens: list[str], state: ShellState) -> Command:
    argv: list[str] = []
    stdin_file = None
    stdout_file = None
    append_stdout = False

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in REDIRECT_TOKENS:
            if i + 1 >= len(tokens):
                raise ParseError(f"expected filename after {tok}")
            target = expand(tokens[i + 1], state)
            if tok == "<":
                stdin_file = target
            elif tok == ">":
                stdout_file = target
                append_stdout = False
            else:
                stdout_file = target
                append_stdout = True
            i += 2
            continue
        argv.append(expand(tok, state))
        i += 1

    if not argv:
        raise ParseError("empty command")
    return Command(argv=argv, stdin_file=stdin_file, stdout_file=stdout_file, append_stdout=append_stdout)


def parse_pipeline(line: str, state: ShellState) -> list[Command]:
    line = line.strip()
    if not line:
        return []

    first_word = line.split(maxsplit=1)[0]
    if first_word in state.aliases:
        line = line.replace(first_word, state.aliases[first_word], 1)

    try:
        segments_tokens = shlex.split(line, comments=True)
    except ValueError as exc:
        raise ParseError(str(exc)) from exc

    pipeline_raw: list[list[str]] = [[]]
    for tok in segments_tokens:
        if tok == "|":
            pipeline_raw.append([])
        else:
            pipeline_raw[-1].append(tok)

    return [parse_segment(seg, state) for seg in pipeline_raw]


BUILTIN_NAMES = {
    "cd", "pwd", "ls", "cp", "mv", "rm", "mkdir", "cat", "ps", "kill",
    "clear", "help", "history", "alias", "export", "exit", "echo",
}


class Shell:
    def __init__(self, state: ShellState | None = None, stdout=None, stderr=None):
        self.state = state or ShellState()
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.builtins = {
            "cd": self._cd, "pwd": self._pwd, "ls": self._ls, "cp": self._cp,
            "mv": self._mv, "rm": self._rm, "mkdir": self._mkdir, "cat": self._cat,
            "ps": self._ps, "kill": self._kill, "clear": self._clear, "help": self._help,
            "history": self._history, "alias": self._alias, "export": self._export,
            "echo": self._echo,
        }

    # ---- REPL entrypoint ----

    def run_line(self, line: str) -> int:
        line = line.strip()
        if not line or line.startswith("#"):
            return 0
        self.state.history.append(line)
        try:
            pipeline = parse_pipeline(line, self.state)
        except ParseError as exc:
            print(f"pysh: {exc}", file=self.stderr)
            self.state.last_status = 2
            return 2

        if not pipeline:
            return 0

        if len(pipeline) == 1 and pipeline[0].argv[0] in BUILTIN_NAMES:
            status = self._run_builtin(pipeline[0])
        else:
            status = self._run_external_pipeline(pipeline)

        self.state.last_status = status
        return status

    # ---- builtin dispatch ----

    def _run_builtin(self, cmd: Command) -> int:
        name, args = cmd.argv[0], cmd.argv[1:]
        if name == "exit":
            raise SystemExit(int(args[0]) if args else 0)
        out_path = self._resolve(cmd.stdout_file) if cmd.stdout_file else None
        out_fh = open(out_path, "a" if cmd.append_stdout else "w") if out_path else self.stdout
        try:
            return self.builtins[name](args, out_fh)
        finally:
            if out_fh is not self.stdout:
                out_fh.close()

    def _run_external_pipeline(self, pipeline: list[Command]) -> int:
        procs = []
        prev_stdout = None
        for idx, cmd in enumerate(pipeline):
            argv = cmd.argv
            resolved = shutil.which(argv[0]) or argv[0]
            stdin = prev_stdout
            if cmd.stdin_file:
                stdin = open(cmd.stdin_file, "r")

            is_last = idx == len(pipeline) - 1
            if cmd.stdout_file:
                stdout = open(cmd.stdout_file, "a" if cmd.append_stdout else "w")
            elif not is_last:
                stdout = subprocess.PIPE
            else:
                stdout = None

            try:
                proc = subprocess.Popen(
                    [resolved] + argv[1:], stdin=stdin, stdout=stdout,
                    cwd=self.state.cwd, env=self.state.env,
                )
            except FileNotFoundError:
                print(f"pysh: {argv[0]}: command not found", file=self.stderr)
                return 127
            if prev_stdout is not None:
                prev_stdout.close()
            prev_stdout = proc.stdout
            procs.append(proc)

        status = 0
        for proc in procs:
            status = proc.wait()
        return status

    # ---- builtins ----

    def _cd(self, args, out) -> int:
        target = args[0] if args else str(Path.home())
        target = expand(target, self.state)
        newdir = (self.state.cwd / target).resolve() if not target.startswith("/") else Path(target)
        if not newdir.is_dir():
            print(f"cd: no such directory: {target}", file=self.stderr)
            return 1
        self.state.cwd = newdir
        return 0

    def _pwd(self, args, out) -> int:
        print(self.state.cwd, file=out)
        return 0

    def _ls(self, args, out) -> int:
        target = Path(args[0]) if args else self.state.cwd
        if not target.is_absolute():
            target = self.state.cwd / target
        if not target.exists():
            print(f"ls: no such file or directory: {args[0] if args else target}", file=self.stderr)
            return 1
        if target.is_file():
            print(target.name, file=out)
            return 0
        for entry in sorted(target.iterdir()):
            print(entry.name, file=out)
        return 0

    def _cp(self, args, out) -> int:
        if len(args) != 2:
            print("usage: cp SRC DST", file=self.stderr)
            return 1
        shutil.copy(self._resolve(args[0]), self._resolve(args[1]))
        return 0

    def _mv(self, args, out) -> int:
        if len(args) != 2:
            print("usage: mv SRC DST", file=self.stderr)
            return 1
        shutil.move(self._resolve(args[0]), self._resolve(args[1]))
        return 0

    def _rm(self, args, out) -> int:
        recursive = "-r" in args or "-rf" in args
        targets = [a for a in args if not a.startswith("-")]
        for t in targets:
            path = self._resolve(t)
            if path.is_dir():
                if recursive:
                    shutil.rmtree(path)
                else:
                    print(f"rm: {t}: is a directory (use -r)", file=self.stderr)
                    return 1
            else:
                path.unlink(missing_ok=True)
        return 0

    def _mkdir(self, args, out) -> int:
        for a in args:
            self._resolve(a).mkdir(parents=True, exist_ok=True)
        return 0

    def _cat(self, args, out) -> int:
        if not args:
            return 0
        for a in args:
            path = self._resolve(a)
            if not path.exists():
                print(f"cat: {a}: no such file", file=self.stderr)
                return 1
            print(path.read_text(), end="", file=out)
        return 0

    def _ps(self, args, out) -> int:
        for pid in sorted(int(p) for p in os.listdir("/proc") if p.isdigit()):
            try:
                with open(f"/proc/{pid}/comm") as f:
                    comm = f.read().strip()
            except OSError:
                continue
            print(f"{pid}\t{comm}", file=out)
        return 0

    def _kill(self, args, out) -> int:
        if not args:
            print("usage: kill PID [PID...]", file=self.stderr)
            return 1
        for a in args:
            try:
                os.kill(int(a), signal.SIGTERM)
            except (ValueError, ProcessLookupError, PermissionError) as exc:
                print(f"kill: {a}: {exc}", file=self.stderr)
                return 1
        return 0

    def _clear(self, args, out) -> int:
        print("\033c", end="", file=out)
        return 0

    def _help(self, args, out) -> int:
        print("PythonOS shell (pysh). Builtins: " + ", ".join(sorted(self.builtins)), file=out)
        return 0

    def _history(self, args, out) -> int:
        for i, line in enumerate(self.state.history, 1):
            print(f"{i}\t{line}", file=out)
        return 0

    def _alias(self, args, out) -> int:
        if not args:
            for name, value in self.state.aliases.items():
                print(f"{name}={value}", file=out)
            return 0
        for a in args:
            if "=" in a:
                name, value = a.split("=", 1)
                self.state.aliases[name] = value
        return 0

    def _export(self, args, out) -> int:
        for a in args:
            if "=" in a:
                name, value = a.split("=", 1)
                self.state.env[name] = value
        return 0

    def _echo(self, args, out) -> int:
        print(" ".join(args), file=out)
        return 0

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        return p if p.is_absolute() else self.state.cwd / p
