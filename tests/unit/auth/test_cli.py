"""Tests for auth CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.auth.cli import (
    _check_related_data,
    _confirm_and_apply_changes,
    _confirm_deletion,
    _count_user_objects,
    _display_user_info,
    _execute_user_deletion,
    _find_user_by_identifier,
    _update_user_active_status,
    _update_user_admin_status,
    _update_user_email,
    _update_user_password,
    _update_user_username,
    create_user,
    delete_user,
    list_users,
    register_commands,
    reset_admin_password,
    update_user,
    user_cli,
)


class TestAuthCLI:
    """Test auth CLI commands."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_admin = True
        user.is_active = True
        user.expenses = Mock()
        user.restaurants = Mock()
        user.categories = Mock()
        user.expenses.count.return_value = 5
        user.restaurants.count.return_value = 3
        user.categories.count.return_value = 2
        return user

    def test_user_cli_group(self):
        """Test user CLI group creation."""
        assert user_cli.name == "user"
        assert user_cli.help == "User management commands."

    def test_register_commands(self, app):
        """Test command registration."""
        register_commands(app)
        assert "user" in [cmd.name for cmd in app.cli.commands.values()]

    def test_reset_admin_password_success(self, runner, app, mock_user):
        """Test successful admin password reset."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalar.return_value = mock_user

                result = runner.invoke(
                    reset_admin_password, ["--email", "admin@example.com", "--password", "newpass123"]
                )
                assert result.exit_code == 0
                assert "Successfully updated password" in result.output
                mock_user.set_password.assert_called_once_with("newpass123")
                mock_db.session.commit.assert_called_once()

    def test_reset_admin_password_user_not_found(self, runner, app):
        """Test admin password reset when user not found."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalar.return_value = None

                result = runner.invoke(
                    reset_admin_password, ["--email", "admin@example.com", "--password", "newpass123"]
                )
                assert result.exit_code == 0
                assert "No admin user found" in result.output

    def test_reset_admin_password_exception(self, runner, app, mock_user):
        """Test admin password reset with exception."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalar.return_value = mock_user
                mock_user.set_password.side_effect = Exception("Database error")

                result = runner.invoke(
                    reset_admin_password, ["--email", "admin@example.com", "--password", "newpass123"]
                )
                assert result.exit_code == 0
                assert "Error updating password" in result.output
                mock_db.session.rollback.assert_called_once()

    def test_count_user_objects(self, mock_user):
        """Test counting user related objects."""
        result = _count_user_objects(mock_user)

        assert result == {"expenses": 5, "restaurants": 3, "categories": 2}

    def test_list_users_success(self, runner, app, mock_user):
        """Test successful user listing."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalars.return_value.all.return_value = [mock_user]

                result = runner.invoke(list_users, [])
                assert result.exit_code == 0
                assert "testuser" in result.output
                assert "test@example.com" in result.output

    def test_list_users_admin_only(self, runner, app, mock_user):
        """Test user listing with admin only filter."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalars.return_value.all.return_value = [mock_user]

                result = runner.invoke(list_users, ["--admin-only"])
                assert result.exit_code == 0
                assert "admin only" in result.output

    def test_list_users_with_objects(self, runner, app, mock_user):
        """Test user listing with object counts."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalars.return_value.all.return_value = [mock_user]

                result = runner.invoke(list_users, ["--objects"])
                assert result.exit_code == 0
                assert "Expenses" in result.output
                assert "Restaurants" in result.output
                assert "Categories" in result.output

    def test_list_users_no_users(self, runner, app):
        """Test user listing when no users found."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalars.return_value.all.return_value = []

                result = runner.invoke(list_users, [])
                assert result.exit_code == 0
                assert "No users found" in result.output

    def test_create_user_success(self, runner, app):
        """Test successful user creation."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                with patch("app.auth.cli.User") as mock_user_class:
                    mock_user_class.query.filter.return_value.first.return_value = None
                    mock_user = Mock()
                    mock_user_class.return_value = mock_user

                    result = runner.invoke(
                        create_user,
                        [
                            "--username",
                            "newuser",
                            "--email",
                            "newuser@example.com",
                            "--password",
                            "password123",
                            "--admin",
                        ],
                    )
                    assert result.exit_code == 0
                    assert "Successfully created user" in result.output
                    mock_db.session.add.assert_called_once()
                    mock_db.session.commit.assert_called_once()

    def test_create_user_invalid_email(self, runner, app):
        """Test user creation with invalid email."""
        result = runner.invoke(
            create_user, ["--username", "newuser", "--email", "invalid-email", "--password", "password123"]
        )
        assert result.exit_code == 0
        assert "Invalid email format" in result.output

    def test_create_user_short_password(self, runner, app):
        """Test user creation with short password."""
        result = runner.invoke(
            create_user, ["--username", "newuser", "--email", "newuser@example.com", "--password", "123"]
        )
        assert result.exit_code == 0
        assert "Password must be at least 8 characters" in result.output

    def test_create_user_existing_user(self, runner, app):
        """Test user creation when user already exists."""
        with app.app_context():
            with patch("app.auth.cli.User") as mock_user_class:
                mock_user_class.query.filter.return_value.first.return_value = Mock()

                result = runner.invoke(
                    create_user,
                    ["--username", "existinguser", "--email", "existing@example.com", "--password", "password123"],
                )
                assert result.exit_code == 0
                assert "already exists" in result.output

    def test_create_user_integrity_error(self, runner, app):
        """Test user creation with integrity error."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                with patch("app.auth.cli.User") as mock_user_class:
                    mock_user_class.query.filter.return_value.first.return_value = None
                    mock_user = Mock()
                    mock_user_class.return_value = mock_user
                    mock_db.session.commit.side_effect = IntegrityError("Constraint violation", None, None)

                    result = runner.invoke(
                        create_user,
                        ["--username", "newuser", "--email", "newuser@example.com", "--password", "password123"],
                    )
                    assert result.exit_code == 0
                    assert "Error creating user" in result.output
                    mock_db.session.rollback.assert_called_once()

    def test_find_user_by_identifier_id(self, app, mock_user):
        """Test finding user by ID."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.get.return_value = mock_user

                result = _find_user_by_identifier("123")
                assert result == mock_user
                mock_db.session.get.assert_called_once()

    def test_find_user_by_identifier_username(self, app, mock_user):
        """Test finding user by username."""
        with app.app_context():
            with patch("app.auth.cli.User") as mock_user_class:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_user
                mock_user_class.query = mock_query

                result = _find_user_by_identifier("testuser")
                assert result == mock_user

    def test_find_user_by_identifier_email(self, app, mock_user):
        """Test finding user by email."""
        with app.app_context():
            with patch("app.auth.cli.User") as mock_user_class:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_user
                mock_user_class.query = mock_query

                result = _find_user_by_identifier("test@example.com")
                assert result == mock_user

    def test_find_user_by_identifier_not_found(self, app):
        """Test finding user when not found."""
        with app.app_context():
            with patch("app.auth.cli.User") as mock_user_class:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = None
                mock_user_class.query = mock_query

                result = _find_user_by_identifier("nonexistent")
                assert result is None

    def test_update_user_username_success(self, mock_user):
        """Test successful username update."""
        changes = []
        result = _update_user_username(mock_user, "newusername", changes)

        assert result is True
        assert mock_user.username == "newusername"
        assert "username to 'newusername'" in changes

    def test_update_user_username_same(self, mock_user):
        """Test username update with same username."""
        changes = []
        result = _update_user_username(mock_user, "testuser", changes)

        assert result is True
        assert changes == []

    def test_update_user_username_taken(self, mock_user):
        """Test username update with taken username."""
        with patch("app.auth.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = Mock()
            mock_user_class.query = mock_query

            changes = []
            result = _update_user_username(mock_user, "takenusername", changes)

            assert result is False
            assert changes == []

    def test_update_user_email_success(self, mock_user):
        """Test successful email update."""
        changes = []
        result = _update_user_email(mock_user, "newemail@example.com", changes)

        assert result is True
        assert mock_user.email == "newemail@example.com"
        assert "email to 'newemail@example.com'" in changes

    def test_update_user_email_same(self, mock_user):
        """Test email update with same email."""
        changes = []
        result = _update_user_email(mock_user, "test@example.com", changes)

        assert result is True
        assert changes == []

    def test_update_user_email_invalid(self, mock_user):
        """Test email update with invalid email."""
        changes = []
        result = _update_user_email(mock_user, "invalid-email", changes)

        assert result is False
        assert changes == []

    def test_update_user_email_taken(self, mock_user):
        """Test email update with taken email."""
        with patch("app.auth.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = Mock()
            mock_user_class.query = mock_query

            changes = []
            result = _update_user_email(mock_user, "taken@example.com", changes)

            assert result is False
            assert changes == []

    def test_update_user_password_success(self, mock_user):
        """Test successful password update."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.prompt.return_value = "newpassword123"
            mock_click.confirm.return_value = True

            changes = []
            result = _update_user_password(mock_user, changes)

            assert result is True
            mock_user.set_password.assert_called_once_with("newpassword123")
            assert "password" in changes

    def test_update_user_password_short(self, mock_user):
        """Test password update with short password."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.prompt.return_value = "123"

            changes = []
            result = _update_user_password(mock_user, changes)

            assert result is False
            assert changes == []

    def test_update_user_password_cancelled(self, mock_user):
        """Test password update when cancelled."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.prompt.return_value = "newpassword123"
            mock_click.confirm.return_value = False

            changes = []
            result = _update_user_password(mock_user, changes)

            assert result is False
            assert changes == []

    def test_update_user_admin_status_changed(self, mock_user):
        """Test admin status update when changed."""
        changes = []
        result = _update_user_admin_status(mock_user, False, changes)

        assert result is True
        assert mock_user.is_admin is False
        assert "admin privileges revoked" in changes

    def test_update_user_admin_status_unchanged(self, mock_user):
        """Test admin status update when unchanged."""
        changes = []
        result = _update_user_admin_status(mock_user, True, changes)

        assert result is True
        assert changes == []

    def test_update_user_active_status_changed(self, mock_user):
        """Test active status update when changed."""
        changes = []
        result = _update_user_active_status(mock_user, False, changes)

        assert result is True
        assert mock_user.is_active is False
        assert "account deactivated" in changes

    def test_update_user_active_status_unchanged(self, mock_user):
        """Test active status update when unchanged."""
        changes = []
        result = _update_user_active_status(mock_user, True, changes)

        assert result is True
        assert changes == []

    def test_confirm_and_apply_changes_no_changes(self, mock_user):
        """Test confirm and apply changes with no changes."""
        result = _confirm_and_apply_changes(mock_user, [])
        assert result is False

    def test_confirm_and_apply_changes_success(self, mock_user):
        """Test successful confirm and apply changes."""
        with patch("app.auth.cli.db") as mock_db:
            with patch("app.auth.cli.click") as mock_click:
                mock_click.confirm.return_value = True

                changes = ["username to newuser"]
                result = _confirm_and_apply_changes(mock_user, changes)

                assert result is True
                mock_db.session.commit.assert_called_once()

    def test_confirm_and_apply_changes_cancelled(self, mock_user):
        """Test confirm and apply changes when cancelled."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.confirm.return_value = False

            changes = ["username to newuser"]
            result = _confirm_and_apply_changes(mock_user, changes)

            assert result is False

    def test_confirm_and_apply_changes_integrity_error(self, mock_user):
        """Test confirm and apply changes with integrity error."""
        with patch("app.auth.cli.db") as mock_db:
            with patch("app.auth.cli.click") as mock_click:
                mock_click.confirm.return_value = True
                mock_db.session.commit.side_effect = IntegrityError("Constraint violation", None, None)

                changes = ["username to newuser"]
                result = _confirm_and_apply_changes(mock_user, changes)

                assert result is False
                mock_db.session.rollback.assert_called_once()

    def test_update_user_success(self, runner, app, mock_user):
        """Test successful user update."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                with patch("app.auth.cli._update_user_username") as mock_update_username:
                    with patch("app.auth.cli._confirm_and_apply_changes") as mock_confirm:
                        mock_find.return_value = mock_user
                        mock_update_username.return_value = True
                        mock_confirm.return_value = True

                        result = runner.invoke(update_user, ["testuser", "--username", "newuser"])
                        assert result.exit_code == 0
                        mock_update_username.assert_called_once()

    def test_update_user_not_found(self, runner, app):
        """Test user update when user not found."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                mock_find.return_value = None

                result = runner.invoke(update_user, ["nonexistent", "--username", "newuser"])
                assert result.exit_code == 0
                assert "No user found" in result.output

    def test_update_user_no_changes(self, runner, app, mock_user):
        """Test user update with no changes specified."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                mock_find.return_value = mock_user

                result = runner.invoke(update_user, ["testuser"])
                assert result.exit_code == 0
                assert "No changes specified" in result.output

    def test_display_user_info(self, mock_user, capsys):
        """Test displaying user information."""
        _display_user_info(mock_user)
        captured = capsys.readouterr()
        assert "testuser" in captured.out
        assert "test@example.com" in captured.out
        assert "Admin: Yes" in captured.out
        assert "Active: Yes" in captured.out

    def test_check_related_data_no_data(self, mock_user):
        """Test checking related data when no data exists."""
        mock_user.expenses.count.return_value = 0
        mock_user.restaurants.count.return_value = 0
        mock_user.categories.count.return_value = 0

        result = _check_related_data(mock_user, False, False)
        assert result is True

    def test_check_related_data_with_data_cascade(self, mock_user):
        """Test checking related data with cascade enabled."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.confirm.return_value = True

            result = _check_related_data(mock_user, False, False)
            assert result is True

    def test_check_related_data_with_data_no_cascade(self, mock_user):
        """Test checking related data with no cascade."""
        result = _check_related_data(mock_user, True, False)
        assert result is False

    def test_check_related_data_with_data_force(self, mock_user):
        """Test checking related data with force flag."""
        result = _check_related_data(mock_user, False, True)
        assert result is True

    def test_confirm_deletion_success(self, mock_user):
        """Test successful deletion confirmation."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.confirm.return_value = True

            result = _confirm_deletion(mock_user, False)
            assert result is True

    def test_confirm_deletion_cancelled(self, mock_user):
        """Test deletion confirmation when cancelled."""
        with patch("app.auth.cli.click") as mock_click:
            mock_click.confirm.return_value = False

            result = _confirm_deletion(mock_user, False)
            assert result is False

    def test_confirm_deletion_force(self, mock_user):
        """Test deletion confirmation with force flag."""
        result = _confirm_deletion(mock_user, True)
        assert result is True

    def test_execute_user_deletion_success(self, mock_user):
        """Test successful user deletion."""
        with patch("app.auth.cli.db") as mock_db:
            _execute_user_deletion(mock_user)

            mock_db.session.delete.assert_called_once_with(mock_user)
            mock_db.session.commit.assert_called_once()

    def test_execute_user_deletion_integrity_error(self, mock_user):
        """Test user deletion with integrity error."""
        with patch("app.auth.cli.db") as mock_db:
            mock_db.session.commit.side_effect = IntegrityError("Constraint violation", None, None)

            _execute_user_deletion(mock_user)

            mock_db.session.rollback.assert_called_once()

    def test_execute_user_deletion_exception(self, mock_user):
        """Test user deletion with exception."""
        with patch("app.auth.cli.db") as mock_db:
            mock_db.session.commit.side_effect = Exception("Database error")

            _execute_user_deletion(mock_user)

            mock_db.session.rollback.assert_called_once()

    def test_delete_user_success(self, runner, app, mock_user):
        """Test successful user deletion."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                with patch("app.auth.cli._check_related_data") as mock_check:
                    with patch("app.auth.cli._confirm_deletion") as mock_confirm:
                        with patch("app.auth.cli._execute_user_deletion") as mock_execute:
                            mock_find.return_value = mock_user
                            mock_check.return_value = True
                            mock_confirm.return_value = True

                            result = runner.invoke(delete_user, ["testuser", "--force"])
                            assert result.exit_code == 0
                            mock_execute.assert_called_once()

    def test_delete_user_not_found(self, runner, app):
        """Test user deletion when user not found."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                mock_find.return_value = None

                result = runner.invoke(delete_user, ["nonexistent"])
                assert result.exit_code == 0
                assert "No user found" in result.output

    def test_delete_user_no_cascade_with_data(self, runner, app, mock_user):
        """Test user deletion with no cascade when user has data."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                with patch("app.auth.cli._check_related_data") as mock_check:
                    mock_find.return_value = mock_user
                    mock_check.return_value = False

                    result = runner.invoke(delete_user, ["testuser", "--no-cascade"])
                    assert result.exit_code == 0

    def test_delete_user_cancelled(self, runner, app, mock_user):
        """Test user deletion when cancelled."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                with patch("app.auth.cli._check_related_data") as mock_check:
                    with patch("app.auth.cli._confirm_deletion") as mock_confirm:
                        mock_find.return_value = mock_user
                        mock_check.return_value = True
                        mock_confirm.return_value = False

                        result = runner.invoke(delete_user, ["testuser"])
                        assert result.exit_code == 0

    def test_create_user_inactive(self, runner, app):
        """Test creating inactive user."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                with patch("app.auth.cli.User") as mock_user_class:
                    mock_user_class.query.filter.return_value.first.return_value = None
                    mock_user = Mock()
                    mock_user_class.return_value = mock_user

                    result = runner.invoke(
                        create_user,
                        [
                            "--username",
                            "newuser",
                            "--email",
                            "newuser@example.com",
                            "--password",
                            "password123",
                            "--inactive",
                        ],
                    )
                    assert result.exit_code == 0
                    assert "Active: No" in result.output

    def test_update_user_multiple_changes(self, runner, app, mock_user):
        """Test user update with multiple changes."""
        with app.app_context():
            with patch("app.auth.cli._find_user_by_identifier") as mock_find:
                with patch("app.auth.cli._update_user_username") as mock_update_username:
                    with patch("app.auth.cli._update_user_email") as mock_update_email:
                        with patch("app.auth.cli._confirm_and_apply_changes") as mock_confirm:
                            mock_find.return_value = mock_user
                            mock_update_username.return_value = True
                            mock_update_email.return_value = True
                            mock_confirm.return_value = True

                            result = runner.invoke(
                                update_user, ["testuser", "--username", "newuser", "--email", "newemail@example.com"]
                            )
                            assert result.exit_code == 0
                            mock_update_username.assert_called_once()
                            mock_update_email.assert_called_once()

    def test_list_users_table_formatting(self, runner, app, mock_user):
        """Test user listing table formatting."""
        with app.app_context():
            with patch("app.auth.cli.db") as mock_db:
                mock_db.session.scalars.return_value.all.return_value = [mock_user]

                result = runner.invoke(list_users, ["--objects"])
                assert result.exit_code == 0
                assert "ID" in result.output
                assert "Email" in result.output
                assert "Username" in result.output
                assert "Admin" in result.output
                assert "Active" in result.output
