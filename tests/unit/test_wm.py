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


def test_client_is_reparented_into_a_decorated_frame(xvfb):
    """Proves real reparenting: the client's parent in the X server's own
    window tree becomes our frame, not the root — exactly how a
    traditional X11 WM decorates windows."""
    from Xlib import display as xdisplay

    from desktop.windows.wm import WindowManager

    wm = WindowManager(display_name=xvfb)
    wm.start()

    client_proc = subprocess.Popen(["xclock", "-display", xvfb])
    try:
        opened = []
        wm.on_window_opened = lambda wid, title: opened.append(wid)
        deadline = time.time() + 5
        while time.time() < deadline and not opened:
            wm.process_pending_events()
            time.sleep(0.1)
        assert opened, "window manager never framed the xclock window"

        managed = wm.windows[opened[0]]
        assert managed.frame_id != managed.client_id

        probe = xdisplay.Display(xvfb)
        client_res = probe.create_resource_object("window", managed.client_id)
        parent = client_res.query_tree().parent
        assert parent.id == managed.frame_id, "client was not reparented into its frame"
        probe.close()
    finally:
        client_proc.terminate()
        client_proc.wait(timeout=5)
    wm.close()


def test_close_button_click_closes_the_real_window(xvfb):
    from desktop.windows.wm import WindowManager

    opened = []
    closed = []
    wm = WindowManager(
        display_name=xvfb,
        on_window_opened=lambda wid, title: opened.append(wid),
        on_window_closed=lambda wid: closed.append(wid),
    )
    wm.start()

    client_proc = subprocess.Popen(["xclock", "-display", xvfb])
    try:
        deadline = time.time() + 5
        while time.time() < deadline and not opened:
            wm.process_pending_events()
            time.sleep(0.1)
        assert opened, "window manager never framed the xclock window"

        client_id = opened[0]
        managed = wm.windows[client_id]
        bx, by, bw, bh = wm._button_rects(managed.normal_geometry[2])["close"]

        from Xlib.protocol import event as xevent
        from Xlib import X

        frame = wm._display.create_resource_object("window", managed.frame_id)
        synthetic = xevent.ButtonPress(
            time=0, root=wm._root, window=frame, same_screen=1,
            child=X.NONE, root_x=0, root_y=0,
            event_x=bx + bw // 2, event_y=by + bh // 2, state=0, detail=1,
        )
        wm._handle_button_press(synthetic)
        wm._display.sync()

        deadline = time.time() + 5
        while time.time() < deadline and not closed:
            wm.process_pending_events()
            time.sleep(0.1)
        assert closed == [client_id], "close button did not close the real client window"
    finally:
        client_proc.poll() is None and client_proc.terminate()
        client_proc.wait(timeout=5)
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
