import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    QApplication = None


@pytest.fixture(scope="session")
def qapp():
    if QApplication is None:
        pytest.skip("PySide6 not installed")
    app = QApplication.instance() or QApplication([])
    yield app
