#!/usr/bin/env python3
"""pysh — the PythonOS interactive shell (REPL entrypoint)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shell.core import Shell  # noqa: E402


def main() -> int:
    shell = Shell()
    while True:
        try:
            line = input(f"pysh:{shell.state.cwd}$ ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        try:
            shell.run_line(line)
        except SystemExit as exc:
            return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
