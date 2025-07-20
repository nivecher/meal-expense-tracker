"""Tests for blueprint registration and initialization."""


def test_blueprint_registration(app):
    """Test that all blueprints are properly registered."""
    blueprints = app.blueprints

    # Check that all expected blueprints are registered
    # Get base blueprint names (without nested names)
    base_blueprints = {name.split(".")[0] for name in blueprints.keys()}
    expected_blueprints = {"auth", "expenses", "main", "restaurants", "api", "errors"}
    if app.config.get("DEBUG"):
        expected_blueprints.add("debug")

    # Verify all expected blueprints are registered
    assert (
        base_blueprints == expected_blueprints
    ), f"Expected base blueprints {expected_blueprints}, but got {base_blueprints}"

    url_rules = {rule.endpoint: rule.rule for rule in app.url_map.iter_rules()}

    assert "auth.login" in url_rules, "Login route not found"
    assert "auth.register" in url_rules, "Register route not found"

    assert any(endpoint.startswith("expenses.") for endpoint in url_rules), "Expenses routes not found"

    assert any(endpoint.startswith("restaurants.") for endpoint in url_rules), "Restaurants routes not found"

    assert "health_check" in url_rules, "Health check route not found"


def test_blueprint_initialization(app):
    """Test that blueprints are properly initialized with the app."""
    with app.app_context():
        assert app.config["TESTING"] is True, "App not in testing mode"

        assert hasattr(app, "extensions"), "App extensions not initialized"
        assert "sqlalchemy" in app.extensions, "SQLAlchemy not initialized"
        assert "login_manager" in app.extensions, "Login manager not initialized"

        assert "auth" in app.blueprints, "Auth blueprint not registered"
        assert "expenses" in app.blueprints, "Expenses blueprint not registered"
        assert "main" in app.blueprints, "Main blueprint not registered"
        assert "restaurants" in app.blueprints, "Restaurants blueprint not registered"
        assert "api" in app.blueprints, "API blueprint not registered"
        assert "errors" in app.blueprints, "Errors blueprint not registered"
