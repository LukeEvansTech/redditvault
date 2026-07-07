"""Tests for app factory and configuration."""

from webapp.app import create_app


def test_create_app():
    from tests.conftest import TestConfig
    app = create_app(TestConfig)
    assert app is not None
    assert app.config["TESTING"] is True


def test_create_app_has_blueprints():
    from tests.conftest import TestConfig
    app = create_app(TestConfig)
    blueprint_names = list(app.blueprints.keys())
    assert "auth" in blueprint_names
    assert "views" in blueprint_names
    assert "api" in blueprint_names
