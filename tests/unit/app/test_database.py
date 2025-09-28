"""Tests for database module."""

import os
from unittest.mock import Mock, patch

import pytest
from flask import Flask

from app.database import (
    _get_database_uri,
    _is_lambda_environment,
    create_tables,
    drop_tables,
    get_engine,
    get_session,
    init_database,
)


class TestDatabaseModule:
    """Test database module functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    def test_is_lambda_environment_aws_execution_env(self):
        """Test Lambda environment detection with AWS_EXECUTION_ENV."""
        with patch.dict(os.environ, {"AWS_EXECUTION_ENV": "AWS_Lambda_python3.9"}):
            assert _is_lambda_environment() is True

    def test_is_lambda_environment_aws_lambda_function_name(self):
        """Test Lambda environment detection with AWS_LAMBDA_FUNCTION_NAME."""
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "my-function"}):
            assert _is_lambda_environment() is True

    def test_is_lambda_environment_not_lambda(self):
        """Test Lambda environment detection when not in Lambda."""
        with patch.dict(os.environ, {}, clear=True):
            assert _is_lambda_environment() is False

    def test_is_lambda_environment_empty_aws_execution_env(self):
        """Test Lambda environment detection with empty AWS_EXECUTION_ENV."""
        with patch.dict(os.environ, {"AWS_EXECUTION_ENV": ""}):
            assert _is_lambda_environment() is False

    def test_get_database_uri_from_env_postgres(self):
        """Test getting database URI from environment variable with postgres://."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@host:5432/db"}):
            uri = _get_database_uri()
            assert uri == "postgresql://user:pass@host:5432/db"

    def test_get_database_uri_from_env_postgresql(self):
        """Test getting database URI from environment variable with postgresql://."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            uri = _get_database_uri()
            assert uri == "postgresql://user:pass@host:5432/db"

    def test_get_database_uri_from_env_mysql(self):
        """Test getting database URI from environment variable with mysql://."""
        with patch.dict(os.environ, {"DATABASE_URL": "mysql://user:pass@host:3306/db"}):
            uri = _get_database_uri()
            assert uri == "mysql://user:pass@host:3306/db"

    def test_get_database_uri_lambda_environment_no_url(self):
        """Test getting database URI in Lambda environment without DATABASE_URL."""
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "my-function"}, clear=True):
            with pytest.raises(
                RuntimeError, match="DATABASE_URL environment variable must be set in Lambda environment"
            ):
                _get_database_uri()

    def test_get_database_uri_from_app_config(self, app):
        """Test getting database URI from app config."""
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"

        with patch.dict(os.environ, {}, clear=True):
            uri = _get_database_uri(app)
            assert uri == "sqlite:///test.db"

    def test_get_database_uri_from_app_config_runtime_error(self, app):
        """Test getting database URI when app context is not available."""
        with patch.dict(os.environ, {}, clear=True):
            # Test without app context - should fall back to SQLite
            uri = _get_database_uri()  # No app parameter passed
            assert uri.startswith("sqlite:///")
            assert "app-development.db" in uri

    def test_get_database_uri_sqlite_development(self):
        """Test getting database URI for SQLite development database."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.database.os.path.exists") as mock_exists:
                with patch("app.database.os.makedirs"):
                    mock_exists.return_value = True

                    uri = _get_database_uri()
                    assert uri.startswith("sqlite:///")
                    assert "app-development.db" in uri
                    assert "check_same_thread=False" in uri
                    assert "timeout=30" in uri

    def test_get_database_uri_sqlite_development_no_instance_dir(self):
        """Test getting database URI when instance directory doesn't exist."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.database.os.path.exists") as mock_exists:
                with patch("app.database.os.makedirs"):
                    mock_exists.return_value = False

                    uri = _get_database_uri()
                    assert uri == "sqlite:///:memory:"

    def test_get_database_uri_with_flask_env(self):
        """Test getting database URI with different FLASK_ENV values."""
        with patch.dict(os.environ, {"FLASK_ENV": "production"}, clear=True):
            with patch("app.database.os.path.exists") as mock_exists:
                with patch("app.database.os.makedirs"):
                    mock_exists.return_value = True

                    uri = _get_database_uri()
                    assert "app-production.db" in uri

    def test_init_database_already_initialized(self, app):
        """Test initializing database when already initialized."""
        app.extensions["sqlalchemy"] = Mock()

        with patch("app.database.db.init_app") as mock_init_app:
            init_database(app)
            mock_init_app.assert_not_called()

    def test_init_database_success(self, app):
        """Test successful database initialization."""
        with patch("app.database.db.init_app") as mock_init_app:
            with patch("app.database.db.create_all") as mock_create_all:
                with patch("app.database.logger") as mock_logger:
                    init_database(app)

                    mock_init_app.assert_called_once_with(app)
                    mock_create_all.assert_called_once()
                    mock_logger.info.assert_called_once()

    def test_init_database_with_connection_pooling(self, app):
        """Test database initialization with connection pooling for non-SQLite databases."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            with patch("app.database.db.init_app"):
                with patch("app.database.db.create_all"):
                    init_database(app)

                    assert "SQLALCHEMY_ENGINE_OPTIONS" in app.config
                    engine_options = app.config["SQLALCHEMY_ENGINE_OPTIONS"]
                    assert engine_options["pool_pre_ping"] is True
                    assert engine_options["pool_recycle"] == 300
                    assert engine_options["pool_size"] == 5
                    assert engine_options["max_overflow"] == 10

    def test_init_database_sqlite_no_pooling(self, app):
        """Test database initialization without connection pooling for SQLite."""
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        with patch("app.database.db.init_app"):
            with patch("app.database.db.create_all"):
                init_database(app)

                assert "SQLALCHEMY_ENGINE_OPTIONS" not in app.config

    def test_init_database_exception(self, app):
        """Test database initialization with exception."""
        with patch("app.database.db.init_app", side_effect=Exception("Database error")):
            with patch("app.database.logger") as mock_logger:
                with pytest.raises(RuntimeError, match="Failed to initialize database"):
                    init_database(app)
                mock_logger.error.assert_called_once()

    def test_create_tables(self, app):
        """Test creating database tables."""
        with app.app_context():
            with patch("app.database.db.create_all") as mock_create_all:
                create_tables()
                mock_create_all.assert_called_once()

    def test_drop_tables(self, app):
        """Test dropping database tables."""
        with app.app_context():
            with patch("app.database.db.drop_all") as mock_drop_all:
                drop_tables()
                mock_drop_all.assert_called_once()

    def test_get_session_success(self, app):
        """Test getting database session successfully."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                mock_session = Mock()
                mock_db.session = mock_session

                session = get_session()
                assert session == mock_session

    def test_get_session_not_initialized(self, app):
        """Test getting database session when not initialized."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                mock_db.session = None

                with pytest.raises(RuntimeError, match="Database session factory not initialized"):
                    get_session()

    def test_get_session_no_session_attribute(self, app):
        """Test getting database session when session attribute doesn't exist."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                del mock_db.session

                with pytest.raises(RuntimeError, match="Database session factory not initialized"):
                    get_session()

    def test_get_engine_success(self, app):
        """Test getting database engine successfully."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                mock_engine = Mock()
                mock_db.engine = mock_engine

                engine = get_engine()
                assert engine == mock_engine

    def test_get_engine_not_initialized(self, app):
        """Test getting database engine when not initialized."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                mock_db.engine = None

                with pytest.raises(RuntimeError, match="Database engine not initialized"):
                    get_engine()

    def test_get_engine_no_engine_attribute(self, app):
        """Test getting database engine when engine attribute doesn't exist."""
        with app.app_context():
            with patch("app.database.db") as mock_db:
                del mock_db.engine

                with pytest.raises(RuntimeError, match="Database engine not initialized"):
                    get_engine()

    def test_database_uri_postgres_conversion_edge_cases(self):
        """Test postgres:// to postgresql:// conversion edge cases."""
        test_cases = [
            ("postgres://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db"),
            (
                "postgres://user:pass@host:5432/db?sslmode=require",
                "postgresql://user:pass@host:5432/db?sslmode=require",
            ),
            ("postgres://user:pass@host:5432/db#fragment", "postgresql://user:pass@host:5432/db#fragment"),
            ("postgresql://user:pass@host:5432/db", "postgresql://user:pass@host:5432/db"),  # Already correct
        ]

        for input_uri, expected_uri in test_cases:
            with patch.dict(os.environ, {"DATABASE_URL": input_uri}):
                result = _get_database_uri()
                assert result == expected_uri

    def test_database_uri_environment_variable_priority(self, app):
        """Test that DATABASE_URL environment variable takes priority over app config."""
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://env:pass@host:5432/envdb"}):
            uri = _get_database_uri(app)
            assert uri == "postgresql://env:pass@host:5432/envdb"

    def test_database_uri_app_config_fallback(self, app):
        """Test that app config is used when no environment variable is set."""
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"

        with patch.dict(os.environ, {}, clear=True):
            uri = _get_database_uri(app)
            assert uri == "sqlite:///app.db"

    def test_database_uri_sqlite_path_construction(self):
        """Test SQLite path construction for development database."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("app.database.os.path.exists") as mock_exists:
                with patch("app.database.os.makedirs"):
                    with patch("app.database.os.path.dirname") as mock_dirname:
                        with patch("app.database.os.path.join") as mock_join:
                            mock_exists.return_value = True
                            mock_dirname.return_value = "/path/to/instance"
                            mock_join.side_effect = lambda *args: "/".join(args)

                            uri = _get_database_uri()
                            assert uri.startswith("sqlite:///")
                            assert "check_same_thread=False" in uri
                            assert "timeout=30" in uri

    def test_init_database_configuration_values(self, app):
        """Test that init_database sets correct configuration values."""
        with patch("app.database.db.init_app"):
            with patch("app.database.db.create_all"):
                init_database(app)

                assert app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False
                assert "SQLALCHEMY_DATABASE_URI" in app.config

    def test_init_database_logging(self, app):
        """Test that init_database logs appropriate messages."""
        with patch("app.database.db.init_app"):
            with patch("app.database.db.create_all"):
                with patch("app.database.logger") as mock_logger:
                    init_database(app)

                    # Should log success message
                    mock_logger.info.assert_called_once()
                    log_message = mock_logger.info.call_args[0][0]
                    assert "Database initialized successfully" in log_message

    def test_init_database_exception_logging(self, app):
        """Test that init_database logs exceptions properly."""
        with patch("app.database.db.init_app", side_effect=Exception("Connection failed")):
            with patch("app.database.logger") as mock_logger:
                with pytest.raises(RuntimeError):
                    init_database(app)

                # Should log error message
                mock_logger.error.assert_called_once()
                log_message = mock_logger.error.call_args[0][0]
                assert "Failed to initialize database" in log_message
