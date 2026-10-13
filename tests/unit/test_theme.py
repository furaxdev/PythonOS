import pytest

from desktop.theme.theme_manager import DEFAULT_THEME, ThemeError, ThemeManager, list_themes, load_theme


def test_list_themes_finds_both_builtin_themes():
    themes = list_themes()
    assert "pythonos-dark" in themes
    assert "pythonos-light" in themes


def test_load_default_theme():
    theme = load_theme(DEFAULT_THEME)
    assert theme.name == "PythonOS Dark"
    assert theme.variant == "dark"
    assert theme.color("accent").startswith("#")


def test_load_unknown_theme_raises():
    with pytest.raises(ThemeError):
        load_theme("does-not-exist")


def test_render_stylesheet_substitutes_tokens():
    theme = load_theme(DEFAULT_THEME)
    css = theme.render_stylesheet()
    for token in theme.colors:
        assert "{" + token + "}" not in css, f"token {token!r} was not substituted"
    assert theme.color("window_bg") in css


def test_theme_manager_apply_sets_qapp_stylesheet(qapp):
    manager = ThemeManager()
    theme = manager.apply(DEFAULT_THEME, app=qapp)
    assert manager.current is theme
    assert qapp.styleSheet() != ""
    assert theme.color("accent") in qapp.styleSheet()


def test_light_theme_has_different_colors_than_dark():
    dark = load_theme("pythonos-dark")
    light = load_theme("pythonos-light")
    assert dark.color("window_bg") != light.color("window_bg")
