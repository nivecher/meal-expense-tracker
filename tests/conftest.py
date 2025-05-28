import pytest
from app import app as flask_app, db

@pytest.fixture(scope='session')
def app():
    """Create and configure a Flask app for testing."""
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key'
    })
    return flask_app

@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client() 