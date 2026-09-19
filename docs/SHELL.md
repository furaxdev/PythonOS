# pysh — the PythonOS Shell

`shell/pysh.py` is the REPL entrypoint; `shell/core.py` holds the parser and
executor so it can be unit tested headlessly (`tests/unit/test_pysh.py`).

## Run it

```bash
python3 shell/pysh.py
```

## Supported syntax

- Simple commands: `ls`, `cat file.txt`
- Pipelines: `cmd1 | cmd2 | cmd3` (real OS pipes via `subprocess`, wired
  stage to stage)
- Redirection: `>` (truncate), `>>` (append), `<` (input)
- Variable expansion: `$VAR` expands from the shell's environment dict
- Aliases: `alias ll=ls` then `ll` expands to `ls`
- Comments: `# ...`

## Builtins (real Python implementations, not shellouts)

`cd`, `pwd`, `ls`, `cp`, `mv`, `rm` (`-r` for directories), `mkdir`, `cat`,
`ps` (reads `/proc` directly), `kill`, `clear`, `help`, `history`, `alias`,
`export`, `echo`, `exit`.

Anything else is resolved via `PATH` and executed as a real subprocess.

## Not yet implemented

Job control (`&`, `fg`/`bg`), tab-completion, and PythonOS `.pysh` scripts
are planned but not built.
