"""Tests for the real X11 window manager (desktop/windows/wm.py).

These spin up a real Xvfb server and a real X client (xclock) and verify
the WindowManager actually intercepts MapRequest/UnmapNotify events for
it — not a simulation of X11, the genuine protocol, on a throwaway
display so it can't collide with anything else running.
"""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest

pytestmark = pytest.mark.skipif(
    shutil.which("Xvfb") is None or shutil.which("xclock") is None,
    reason="Xvfb or xclock not installed",
)


@pytest.fixture
def xvfb():
    display_name = ":92"
    proc = subprocess.Popen(
        ["Xvfb", display_name, "-screen", "0", "640x480x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.8)
    yield display_name
    proc.terminate()
    proc.wait(timeout=5)


def test_window_manager_tracks_real_client_open_and_close(xvfb):
    from desktop.windows.wm import WindowManager

    opened = []
    closed = []
    wm = WindowManager(
        display_name=xvfb,
        on_window_opened=lambda wid, title: opened.append((wid, title)),
        on_window_closed=lambda wid: closed.append(wid),
    )
    wm.start()

    client = subprocess.Popen(["xclock", "-display", xvfb])
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not opened:
            wm.process_pending_events()
            time.sleep(0.1)

        assert opened, "window manager never saw the xclock MapRequest"
        wid, title = opened[0]
        assert title == "xclock"
        assert wm.window_titles() == ["xclock"]
    finally:
        client.terminate()
        client.wait(timeout=5)

    deadline = time.time() + 5
    while time.time() < deadline and not closed:
        wm.process_pending_events()
        time.sleep(0.1)
    assert closed == [wid]
    assert wm.window_titles() == []

    wm.close()


def test_second_window_manager_cannot_take_over(xvfb):
    from desktop.windows.wm import WindowManager, WindowManagerError

    first = WindowManager(display_name=xvfb)
    first.start()

    second = WindowManager(display_name=xvfb)
    with pytest.raises(WindowManagerError):
        second.start()

    first.close()
    second.close()
