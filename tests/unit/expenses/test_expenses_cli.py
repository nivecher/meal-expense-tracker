"""Tests for expenses CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from flask import Flask

from app.expenses.cli import (
    _get_target_users,
    _process_users,
    _show_results,
    _sort_categories_by_default_order,
    category_cli,
    list_categories,
    register_commands,
    reinit_categories,
)
from app.expenses.models import Category


class TestExpensesCLI:
    """Test expenses CLI commands."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        # Initialize SQLAlchemy
        from flask_sqlalchemy import SQLAlchemy

        db = SQLAlchemy()
        db.init_app(app)

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
        return user

    @pytest.fixture
    def mock_category(self):
        """Create mock category."""
        category = Mock(spec=Category)
        category.id = 1
        category.name = "Food"
        category.description = "Food and dining expenses"
        category.color = "#FF5733"
        category.icon = "🍽️"
        category.is_default = True
        category.user_id = 1
        return category

    def test_category_cli_group(self):
        """Test category CLI group creation."""
        assert category_cli.name == "category"
        assert category_cli.help == "Category management commands."

    def test_register_commands(self, app):
        """Test command registration."""
        register_commands(app)
        assert "category" in [cmd.name for cmd in app.cli.commands.values()]

    def test_sort_categories_by_default_order(self, mock_category):
        """Test sorting categories by default order."""
        # Create additional mock categories
        cat1 = Mock(spec=Category)
        cat1.name = "Food"
        cat2 = Mock(spec=Category)
        cat2.name = "Transportation"
        cat3 = Mock(spec=Category)
        cat3.name = "Custom Category"

        categories = [cat3, cat1, cat2]  # Out of order

        with patch("app.expenses.cli.get_default_categories") as mock_get_default:
            mock_get_default.return_value = [{"name": "Food"}, {"name": "Transportation"}, {"name": "Entertainment"}]

            result = _sort_categories_by_default_order(categories)

            # Should be sorted with default categories first, then custom
            assert result[0].name == "Food"
            assert result[1].name == "Transportation"
            assert result[2].name == "Custom Category"

    def test_sort_categories_by_default_order_custom_only(self, mock_category):
        """Test sorting categories with only custom categories."""
        cat1 = Mock(spec=Category)
        cat1.name = "Custom Category B"
        cat2 = Mock(spec=Category)
        cat2.name = "Custom Category A"

        categories = [cat1, cat2]

        with patch("app.expenses.cli.get_default_categories") as mock_get_default:
            mock_get_default.return_value = [{"name": "Food"}]

            result = _sort_categories_by_default_order(categories)

            # Should be sorted alphabetically
            assert result[0].name == "Custom Category A"
            assert result[1].name == "Custom Category B"

    def test_get_target_users_by_user_id(self, mock_user):
        """Test getting target users by user ID."""
        with patch("app.expenses.cli.db.session.get") as mock_get:
            mock_get.return_value = mock_user

            result = _get_target_users(1, None, False)
            assert result == [mock_user]
            assert mock_get.called

    def test_get_target_users_by_user_id_not_found(self):
        """Test getting target users by user ID when user not found."""
        with patch("app.expenses.cli.db.session.get") as mock_get:
            mock_get.return_value = None

            result = _get_target_users(1, None, False)
            assert result == []

    def test_get_target_users_by_username(self, mock_user):
        """Test getting target users by username."""
        with patch("app.expenses.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_user
            mock_user_class.query = mock_query

            result = _get_target_users(None, "testuser", False)
            assert result == [mock_user]

    def test_get_target_users_by_username_not_found(self):
        """Test getting target users by username when user not found."""
        with patch("app.expenses.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.first.return_value = None
            mock_user_class.query = mock_query

            result = _get_target_users(None, "testuser", False)
            assert result == []

    def test_get_target_users_all_users(self, mock_user):
        """Test getting all users."""
        with patch("app.expenses.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.all.return_value = [mock_user]
            mock_user_class.query = mock_query

            result = _get_target_users(None, None, True)
            assert result == [mock_user]

    def test_get_target_users_all_users_none_found(self):
        """Test getting all users when none found."""
        with patch("app.expenses.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.all.return_value = []
            mock_user_class.query = mock_query

            result = _get_target_users(None, None, True)
            assert result == []

    def test_get_target_users_no_options(self):
        """Test getting target users with no options specified."""
        result = _get_target_users(None, None, False)
        assert result == []

    def test_process_users_no_categories(self, app, mock_user):
        """Test processing users with no existing categories."""
        with app.app_context():
            with patch("app.expenses.cli.get_default_categories") as mock_get_default:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli.db"):
                        mock_get_default.return_value = [
                            {"name": "Food", "description": "Food expenses", "color": "#FF5733", "icon": "🍽️"}
                        ]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = []
                        mock_category_class.query = mock_query

                        result = _process_users([mock_user], False, False)
                        assert result == (1, 0)  # 1 created, 0 deleted

    def test_process_users_with_existing_categories(self, mock_user, mock_category):
        """Test processing users with existing categories."""
        with patch("app.expenses.cli.get_default_categories") as mock_get_default:
            with patch("app.expenses.cli.Category") as mock_category_class:
                mock_get_default.return_value = [
                    {"name": "Food", "description": "Food expenses", "color": "#FF5733", "icon": "🍽️"}
                ]
                mock_query = Mock()
                mock_query.filter_by.return_value.all.return_value = [mock_category]
                mock_category_class.query = mock_query

                result = _process_users([mock_user], False, False)
                assert result == (0, 0)  # 0 created, 0 deleted

    def test_process_users_force_mode(self, mock_user, mock_category):
        """Test processing users in force mode."""
        with patch("app.expenses.cli.get_default_categories") as mock_get_default:
            with patch("app.expenses.cli.Category") as mock_category_class:
                with patch("app.expenses.cli.db") as mock_db:
                    mock_get_default.return_value = [
                        {"name": "Food", "description": "Food expenses", "color": "#FF5733", "icon": "🍽️"}
                    ]
                    mock_query = Mock()
                    mock_query.filter_by.return_value.all.return_value = [mock_category]
                    mock_category_class.query = mock_query

                    result = _process_users([mock_user], True, False)
                    assert result == (1, 1)  # 1 created, 1 deleted
                    mock_db.session.delete.assert_called_once()
                    mock_db.session.flush.assert_called_once()

    def test_process_users_dry_run(self, mock_user):
        """Test processing users in dry run mode."""
        with patch("app.expenses.cli.get_default_categories") as mock_get_default:
            with patch("app.expenses.cli.Category") as mock_category_class:
                mock_get_default.return_value = [
                    {"name": "Food", "description": "Food expenses", "color": "#FF5733", "icon": "🍽️"}
                ]
                mock_query = Mock()
                mock_query.filter_by.return_value.all.return_value = []
                mock_category_class.query = mock_query

                result = _process_users([mock_user], False, True)
                assert result == (1, 0)  # 1 created, 0 deleted

    def test_show_results_success(self):
        """Test showing results successfully."""
        with patch("app.expenses.cli.db") as mock_db:
            _show_results(5, 2, True, False)

            mock_db.session.commit.assert_called_once()

    def test_show_results_exception(self, app):
        """Test showing results with exception."""
        with app.app_context():
            with patch("app.expenses.cli.db") as mock_db:
                with patch("app.expenses.cli.current_app") as mock_app:
                    # Ensure logger.error is a regular Mock, not AsyncMock
                    mock_app.logger.error = Mock()
                    mock_db.session.commit.side_effect = Exception("Database error")

                    with pytest.raises(Exception):
                        _show_results(5, 2, True, False)

                    mock_db.session.rollback.assert_called_once()
                    mock_app.logger.error.assert_called_once()

    def test_show_results_dry_run(self):
        """Test showing results in dry run mode."""
        with patch("app.expenses.cli.db") as mock_db:
            _show_results(5, 2, True, True)

            mock_db.session.commit.assert_not_called()

    def test_reinit_categories_no_options(self, runner, app):
        """Test reinit categories with no options specified."""
        with app.app_context():
            result = runner.invoke(reinit_categories, [])
            assert result.exit_code == 0
            assert "Must specify --user-id, --username, or --all-users" in result.output

    def test_reinit_categories_multiple_options(self, runner, app):
        """Test reinit categories with multiple options specified."""
        with app.app_context():
            result = runner.invoke(reinit_categories, ["--user-id", "1", "--username", "testuser"])
            assert result.exit_code == 0
            assert "Can only specify one of" in result.output

    def test_reinit_categories_success(self, runner, app, mock_user):
        """Test successful category reinitialization."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli._process_users") as mock_process:
                    with patch("app.expenses.cli._show_results") as mock_show:
                        mock_get_users.return_value = [mock_user]
                        mock_process.return_value = (5, 2)

                        result = runner.invoke(reinit_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        mock_get_users.assert_called_once()
                        mock_process.assert_called_once()
                        mock_show.assert_called_once()

    def test_reinit_categories_dry_run(self, runner, app, mock_user):
        """Test category reinitialization in dry run mode."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli._process_users") as mock_process:
                    with patch("app.expenses.cli._show_results"):
                        mock_get_users.return_value = [mock_user]
                        mock_process.return_value = (5, 2)

                        result = runner.invoke(reinit_categories, ["--user-id", "1", "--dry-run"])
                        assert result.exit_code == 0
                        assert "DRY RUN MODE" in result.output

    def test_reinit_categories_force(self, runner, app, mock_user):
        """Test category reinitialization with force flag."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli._process_users") as mock_process:
                    with patch("app.expenses.cli._show_results"):
                        mock_get_users.return_value = [mock_user]
                        mock_process.return_value = (5, 2)

                        result = runner.invoke(reinit_categories, ["--user-id", "1", "--force"])
                        assert result.exit_code == 0
                        mock_process.assert_called_once_with([mock_user], True, False)

    def test_list_categories_no_options(self, runner, app):
        """Test list categories with no options specified."""
        with app.app_context():
            result = runner.invoke(list_categories, [])
            assert result.exit_code == 0
            assert "Must specify --user-id, --username, or --all-users" in result.output

    def test_list_categories_success(self, runner, app, mock_user, mock_category):
        """Test successful category listing."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "testuser" in result.output
                        assert "Food" in result.output

    def test_list_categories_no_categories(self, runner, app, mock_user):
        """Test listing categories when user has no categories."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = []
                        mock_category_class.query = mock_query
                        mock_sort.return_value = []

                        result = runner.invoke(list_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "No categories" in result.output

    def test_list_categories_with_default_flag(self, runner, app, mock_user, mock_category):
        """Test listing categories with default flag."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "[DEFAULT]" in result.output

    def test_list_categories_with_color_and_icon(self, runner, app, mock_user, mock_category):
        """Test listing categories with color and icon information."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "#FF5733" in result.output
                        assert "🍽️" in result.output

    def test_list_categories_with_description(self, runner, app, mock_user, mock_category):
        """Test listing categories with description."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "Food and dining expenses" in result.output

    def test_process_users_multiple_users(self, app, mock_user):
        """Test processing multiple users."""
        user2 = Mock()
        user2.id = 2
        user2.username = "user2"

        with app.app_context():
            with patch("app.expenses.cli.get_default_categories") as mock_get_default:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli.db"):
                        mock_get_default.return_value = [
                            {"name": "Food", "description": "Food expenses", "color": "#FF5733", "icon": "🍽️"}
                        ]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = []
                        mock_category_class.query = mock_query

                        result = _process_users([mock_user, user2], False, False)
                        assert result == (2, 0)  # 2 created, 0 deleted

    def test_show_results_no_force(self):
        """Test showing results without force flag."""
        with patch("app.expenses.cli.db") as mock_db:
            _show_results(5, 0, False, False)

            mock_db.session.commit.assert_called_once()

    def test_show_results_dry_run_with_force(self):
        """Test showing results in dry run mode with force flag."""
        with patch("app.expenses.cli.db") as mock_db:
            _show_results(5, 2, True, True)

            mock_db.session.commit.assert_not_called()

    def test_reinit_categories_all_users(self, runner, app, mock_user):
        """Test reinit categories for all users."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli._process_users") as mock_process:
                    with patch("app.expenses.cli._show_results"):
                        mock_get_users.return_value = [mock_user]
                        mock_process.return_value = (5, 2)

                        result = runner.invoke(reinit_categories, ["--all-users"])
                        assert result.exit_code == 0
                        mock_get_users.assert_called_once_with(None, None, True)

    def test_reinit_categories_by_username(self, runner, app, mock_user):
        """Test reinit categories by username."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli._process_users") as mock_process:
                    with patch("app.expenses.cli._show_results"):
                        mock_get_users.return_value = [mock_user]
                        mock_process.return_value = (5, 2)

                        result = runner.invoke(reinit_categories, ["--username", "testuser"])
                        assert result.exit_code == 0
                        mock_get_users.assert_called_once_with(None, "testuser", False)

    def test_list_categories_all_users(self, runner, app, mock_user, mock_category):
        """Test list categories for all users."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--all-users"])
                        assert result.exit_code == 0
                        mock_get_users.assert_called_once_with(None, None, True)

    def test_list_categories_by_username(self, runner, app, mock_user, mock_category):
        """Test list categories by username."""
        with app.app_context():
            with patch("app.expenses.cli._get_target_users") as mock_get_users:
                with patch("app.expenses.cli.Category") as mock_category_class:
                    with patch("app.expenses.cli._sort_categories_by_default_order") as mock_sort:
                        mock_get_users.return_value = [mock_user]
                        mock_query = Mock()
                        mock_query.filter_by.return_value.all.return_value = [mock_category]
                        mock_category_class.query = mock_query
                        mock_sort.return_value = [mock_category]

                        result = runner.invoke(list_categories, ["--username", "testuser"])
                        assert result.exit_code == 0
                        mock_get_users.assert_called_once_with(None, "testuser", False)
