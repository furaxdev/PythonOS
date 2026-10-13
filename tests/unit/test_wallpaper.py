from desktop.background.wallpaper_widget import WallpaperWidget
from desktop.theme.theme_manager import load_theme


def test_wallpaper_widget_renders_without_crashing(qapp):
    theme = load_theme("pythonos-dark")
    widget = WallpaperWidget(theme=theme)
    widget.resize(200, 100)
    widget.show()
    qapp.processEvents()

    pixmap = widget.grab()
    assert pixmap.width() == 200
    assert pixmap.height() == 100


def test_wallpaper_set_theme_updates(qapp):
    dark = load_theme("pythonos-dark")
    light = load_theme("pythonos-light")
    widget = WallpaperWidget(theme=dark)
    assert widget.theme.name == "PythonOS Dark"

    widget.set_theme(light)
    assert widget.theme.name == "PythonOS Light"
