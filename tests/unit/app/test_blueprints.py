"""Tests for blueprint registration and initialization."""


def test_blueprint_registration(app) -> None:
    """Test that all blueprints are properly registered."""
    blueprints = app.blueprints

    # Check that all expected blueprints are registered
    # Get base blueprint names (without nested names)
    base_blueprints = {name.split(".")[0] for name in blueprints.keys()}
    expected_blueprints = {"auth", "expenses", "main", "restaurants", "api", "reports", "admin", "errors", "health"}

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


def test_blueprint_initialization(app) -> None:
    """Test that blueprints are properly initialized with the app."""
    with app.app_context():
        assert app.config["TESTING"] is True, "App not in testing mode"

        assert hasattr(app, "extensions"), "App extensions not initialized"

        # Check for core extensions that should always be present
        assert "sqlalchemy" in app.extensions, "SQLAlchemy not initialized"
        assert "migrate" in app.extensions, "Flask-Migrate not initialized"
        assert "csrf" in app.extensions, "CSRF protection not initialized"

        # Check for Flask-Login (session-based authentication)
        # Flask-Login doesn't register as an extension, but we can check if it's configured
        from flask_login import LoginManager

        from app.extensions import login_manager

        assert isinstance(login_manager, LoginManager), "Flask-Login not properly initialized"

        # Check for session management (using Flask's built-in signed cookie sessions)
        # The session functionality is available through Flask's built-in session
        assert hasattr(app, "permanent_session_lifetime"), "Flask session not available"

        assert "auth" in app.blueprints, "Auth blueprint not registered"
        assert "expenses" in app.blueprints, "Expenses blueprint not registered"
        assert "main" in app.blueprints, "Main blueprint not registered"
        assert "restaurants" in app.blueprints, "Restaurants blueprint not registered"
        assert "api" in app.blueprints, "API blueprint not registered"
        assert "reports" in app.blueprints, "Reports blueprint not registered"
