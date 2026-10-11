"""End-to-end test: real Xvfb + real xclock client + our WindowManager +
our PanelWidget, wired together exactly as desktop/session/graphical_session.py
does it. Proves the panel's task manager reflects genuinely open windows.

Runs in a subprocess: a real (xcb-backed) QApplication can't safely share
a process with the offscreen-backed QApplication the other desktop tests
create (qapp fixture) — Qt only ever initializes one platform plugin per
process, and reusing an xcb QApplication after its X connection is torn
down hangs later tests. A subprocess keeps this test's QApplication
fully isolated.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    shutil.which("Xvfb") is None or shutil.which("xclock") is None,
    reason="Xvfb or xclock not installed",
)

PROOF_SCRIPT = textwrap.dedent("""
    import sys, time, subprocess
    sys.path.insert(0, %(repo_root)r)
    from desktop.session.graphical_session import GraphicalSession

    display_name = sys.argv[1]
    session = GraphicalSession(display_name=display_name)
    session.start()

    client = subprocess.Popen(["xclock", "-display", display_name])
    try:
        deadline = time.time() + 8
        while time.time() < deadline and not session.panel.task_manager.window_titles():
            session.app.processEvents()
            session.wm.process_pending_events()
            time.sleep(0.1)
        print("TITLES=" + ",".join(session.panel.task_manager.window_titles()))
    finally:
        client.terminate()
        client.wait(timeout=5)
""") % {"repo_root": str(REPO_ROOT)}


@pytest.fixture
def xvfb_display():
    display_name = ":93"
    proc = subprocess.Popen(
        ["Xvfb", display_name, "-screen", "0", "640x480x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    import time
    time.sleep(0.8)
    yield display_name
    proc.terminate()
    proc.wait(timeout=5)


def test_graphical_session_reflects_real_window_in_task_manager(xvfb_display, tmp_path):
    script = tmp_path / "proof.py"
    script.write_text(PROOF_SCRIPT)

    result = subprocess.run(
        [sys.executable, "-I", str(script), xvfb_display],
        env={"DISPLAY": xvfb_display, "QT_QPA_PLATFORM": "xcb", "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True, timeout=20,
    )

    assert "TITLES=xclock" in result.stdout, (
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
