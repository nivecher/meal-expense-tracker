"""Tests for blueprint registration and initialization."""


def test_blueprint_registration(app):
    """Test that all blueprints are properly registered."""
    blueprints = app.blueprints

    # Check that all expected blueprints are registered
    # Get base blueprint names (without nested names)
    base_blueprints = {name.split(".")[0] for name in blueprints.keys()}
    expected_blueprints = {"auth", "expenses", "main", "restaurants", "health"}
    if app.config.get("DEBUG"):
        expected_blueprints.add("debug")

    # Verify all expected blueprints are registered
    assert (
        base_blueprints == expected_blueprints
    ), f"Expected base blueprints {expected_blueprints}, but got {base_blueprints}"

    url_rules = {rule.endpoint: rule.rule for rule in app.url_map.iter_rules()}

    assert any(rule.startswith("/login") for rule in url_rules.values()), "Login route not found"
    assert any(rule.startswith("/register") for rule in url_rules.values()), "Register route not found"

    assert any(rule.startswith("/expenses") for rule in url_rules.values()), "Expenses routes not found"

    assert any(rule.startswith("/restaurants") for rule in url_rules.values()), "Restaurants routes not found"

    assert "/health" in url_rules.values(), "Health check route not found"


def test_blueprint_initialization(app):
    """Test that blueprints are properly initialized with the app."""
    assert app.config["TESTING"] is True, "App not in testing mode"

    assert hasattr(app, "extensions"), "App extensions not initialized"
    assert "sqlalchemy" in app.extensions, "SQLAlchemy not initialized"
    assert "login_manager" in app.extensions, "Login manager not initialized"

    assert "auth" in app.blueprints, "Auth blueprint not registered"
    assert "expenses" in app.blueprints, "Expenses blueprint not registered"
    assert "main" in app.blueprints, "Main blueprint not registered"
    assert "restaurants" in app.blueprints, "Restaurants blueprint not registered"
    assert "health" in app.blueprints, "Health blueprint not registered"
