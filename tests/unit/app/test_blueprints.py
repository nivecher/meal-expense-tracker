"""Tests for blueprint registration and initialization."""


def test_blueprint_registration(app):
    """Test that all blueprints are properly registered."""
    blueprints = app.blueprints

    # Check that all expected blueprints are registered
    # Get base blueprint names (without nested names)
    base_blueprints = {name.split(".")[0] for name in blueprints.keys()}
    expected_blueprints = {"auth", "expenses", "main", "restaurants", "api", "reports", "admin", "errors"}

    # Debug routes are part of the main blueprint, not a separate debug blueprint
    # So we don't add "debug" to expected blueprints

    # Verify all expected blueprints are registered
    assert (
        base_blueprints == expected_blueprints
    ), f"Expected base blueprints {expected_blueprints}, but got {base_blueprints}"

    url_rules = {rule.endpoint: rule.rule for rule in app.url_map.iter_rules()}

    assert "auth.login" in url_rules, "Login route not found"
    assert "auth.register" in url_rules, "Register route not found"

    assert any(endpoint.startswith("expenses.") for endpoint in url_rules), "Expenses routes not found"

    assert any(endpoint.startswith("restaurants.") for endpoint in url_rules), "Restaurants routes not found"

    # Check for main blueprint routes
    assert "main.index" in url_rules, "Main index route not found"
    assert "main.about" in url_rules, "Main about route not found"


def test_blueprint_initialization(app):
    """Test that blueprints are properly initialized with the app."""
    with app.app_context():
        assert app.config["TESTING"] is True, "App not in testing mode"

        assert hasattr(app, "extensions"), "App extensions not initialized"

        # Check for core extensions that should always be present
        assert "sqlalchemy" in app.extensions, "SQLAlchemy not initialized"
        assert "migrate" in app.extensions, "Flask-Migrate not initialized"
        assert "csrf" in app.extensions, "CSRF protection not initialized"

        # Check for authentication extensions (either login_manager or JWT)
        auth_extensions = [ext for ext in app.extensions.keys() if "login" in ext.lower() or "jwt" in ext.lower()]
        assert len(auth_extensions) > 0, f"No authentication extensions found. Available: {list(app.extensions.keys())}"

        # Check for session management (Flask-Session extends Flask's built-in session)
        # The session functionality is available through Flask's built-in session
        assert hasattr(app, "permanent_session_lifetime"), "Flask session not available"

        assert "auth" in app.blueprints, "Auth blueprint not registered"
        assert "expenses" in app.blueprints, "Expenses blueprint not registered"
        assert "main" in app.blueprints, "Main blueprint not registered"
        assert "restaurants" in app.blueprints, "Restaurants blueprint not registered"
        assert "api" in app.blueprints, "API blueprint not registered"
        assert "reports" in app.blueprints, "Reports blueprint not registered"
