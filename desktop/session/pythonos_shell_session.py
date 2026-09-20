#!/usr/bin/env python3
"""The PythonOS headless shell session — the one real, working "session"
available today. Started by LoginManager once a graphical session exists
(Phase 6+, needs a display this dev container doesn't have) a proper
compositor-backed session will be added alongside this one, not instead
of it: a text session is a legitimate target in its own right (see spec
section 5 — pysh as the default interactive shell).

This is intentionally the primary (and only) SessionManager component for
now: exiting it ends the session, exactly like a compositor exiting ends
a graphical one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shell.pysh import main as pysh_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(pysh_main())
