"""Tests for merchant CLI commands."""

import json
from unittest.mock import Mock, patch

import click
from click.testing import CliRunner
from flask import Flask
import pytest

from app.merchants.cli import (
    _get_target_users,
    categories_merchants,
    create_merchant_cmd,
    delete_merchant_cmd,
    export_merchants,
    link_merchant,
    list_merchants,
    merchant_cli,
    register_commands,
    show_merchant,
)


class TestMerchantCLI:
    """Test merchant CLI commands."""

    @pytest.fixture
    def app(self) -> Flask:
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI runner."""
        return CliRunner()

    def test_merchant_cli_group(self) -> None:
        """Test merchant CLI group creation."""
        assert merchant_cli.name == "merchant"
        assert merchant_cli.help == "Merchant management commands."

    def test_register_commands(self, app: Flask) -> None:
        """Test command registration."""
        register_commands(app)
        assert "merchant" in [cmd.name for cmd in app.cli.commands.values()]

    @patch("app.merchants.cli.merchant_services.get_merchants")
    def test_list_merchants_invocation_succeeds(self, mock_get_merchants: Mock, app: Flask, runner: CliRunner) -> None:
        """List runs with app context and returns success when get_merchants returns."""
        mock_get_merchants.return_value = []
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "list"])
        assert result.exit_code == 0
        assert "Merchants: 0" in result.output

    @patch("app.merchants.cli.merchant_services.get_merchants")
    def test_list_merchants_no_user_scope(self, mock_get_merchants: Mock, app: Flask, runner: CliRunner) -> None:
        """List without user scope shows all merchants."""
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme Coffee"
        mock_merchant.short_name = "Acme"
        mock_merchant.category = "coffee_shop"
        mock_merchant.website = "https://acme.example"
        mock_get_merchants.return_value = [mock_merchant]

        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "list"])

        assert result.exit_code == 0
        mock_get_merchants.assert_called_once()
        assert "Acme Coffee" in result.output
        assert "Merchants: 1" in result.output

    @patch("app.merchants.cli.merchant_services.get_merchants_with_stats")
    @patch("app.merchants.cli._get_target_users")
    def test_list_merchants_with_username(
        self,
        mock_get_users: Mock,
        mock_get_stats: Mock,
        app: Flask,
        runner: CliRunner,
    ) -> None:
        """List with --username shows merchants with restaurant counts for that user."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_users.return_value = [mock_user]

        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Starbucks"
        mock_merchant.short_name = None
        mock_merchant.category = "coffee_shop"
        mock_merchant.website = None
        mock_get_stats.return_value = ([mock_merchant], {"merchant_data": {1: {"restaurant_count": 3}}})

        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "list", "--username", "admin"])

        assert result.exit_code == 0
        mock_get_users.assert_called_once_with(None, "admin", False)
        mock_get_stats.assert_called_once()
        assert "Starbucks" in result.output
        assert "3 restaurants" in result.output
        assert "admin" in result.output

    @patch("app.merchants.cli.merchant_services.get_merchant")
    def test_show_merchant_found(self, mock_get_merchant: Mock, app: Flask, runner: CliRunner) -> None:
        """Show displays merchant details when found."""
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme Coffee"
        mock_merchant.short_name = "Acme"
        mock_merchant.category = "coffee_shop"
        mock_merchant.website = "https://acme.example"
        # Use a real list so len(list(merchant.restaurants)) works in CLI
        mock_merchant.restaurants = [1, 2, 3, 4, 5]
        mock_get_merchant.return_value = mock_merchant

        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "show", "1"])

        assert result.exit_code == 0
        assert "Acme Coffee" in result.output
        assert "Short name: Acme" in result.output
        assert "Category: coffee_shop" in result.output
        assert "Total linked restaurants" in result.output
        assert "5" in result.output

    @patch("app.merchants.cli.merchant_services.get_merchant")
    def test_show_merchant_not_found(self, mock_get_merchant: Mock, app: Flask, runner: CliRunner) -> None:
        """Show exits non-zero when merchant ID not found."""
        mock_get_merchant.return_value = None

        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "show", "999"])

        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("app.merchants.cli._get_target_users")
    def test_list_merchants_multiple_user_options_fails(
        self, mock_get_users: Mock, app: Flask, runner: CliRunner
    ) -> None:
        """List with both --user-id and --username raises UsageError."""
        register_commands(app)
        result = runner.invoke(
            app.cli,
            ["merchant", "list", "--user-id", "1", "--username", "admin"],
        )
        assert result.exit_code != 0
        assert "one of" in result.output.lower()
        mock_get_users.assert_not_called()

    @patch("app.merchants.cli.merchant_services.get_merchant_categories")
    def test_categories_output(self, mock_categories: Mock, app: Flask, runner: CliRunner) -> None:
        """Categories command prints valid categories."""
        mock_categories.return_value = ["fast_food", "coffee_shop", "casual_dining"]
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "categories"])
        assert result.exit_code == 0
        assert "coffee_shop" in result.output
        assert "Valid categories" in result.output

    @patch("app.merchants.cli.merchant_services.export_merchants_for_user")
    @patch("app.merchants.cli._get_target_users")
    def test_export_requires_user(self, mock_get_users: Mock, mock_export: Mock, app: Flask, runner: CliRunner) -> None:
        """Export without --user-id or --username fails."""
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "export"])
        assert result.exit_code != 0
        assert "Must specify" in result.output
        mock_export.assert_not_called()

    @patch("app.merchants.cli.merchant_services.export_merchants_for_user")
    @patch("app.merchants.cli._get_target_users")
    def test_export_json_stdout(self, mock_get_users: Mock, mock_export: Mock, app: Flask, runner: CliRunner) -> None:
        """Export with --username and --format json writes JSON to stdout."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_users.return_value = [mock_user]
        mock_export.return_value = [{"name": "Acme", "short_name": "", "website": "", "category": "coffee_shop"}]
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "export", "--username", "admin", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "Acme"

    @patch("app.merchants.cli.merchant_services.create_merchant")
    @patch("app.merchants.cli._get_target_users")
    def test_create_success(self, mock_get_users: Mock, mock_create: Mock, app: Flask, runner: CliRunner) -> None:
        """Create with --name and --username succeeds."""
        mock_user = Mock()
        mock_user.id = 1
        mock_get_users.return_value = [mock_user]
        mock_merchant = Mock()
        mock_merchant.id = 10
        mock_merchant.name = "New Merchant"
        mock_create.return_value = mock_merchant
        register_commands(app)
        result = runner.invoke(
            app.cli,
            ["merchant", "create", "--username", "admin", "--name", "New Merchant"],
        )
        assert result.exit_code == 0
        assert "New Merchant" in result.output
        assert "ID: 10" in result.output

    @patch("app.merchants.cli.merchant_services.create_merchant")
    @patch("app.merchants.cli._get_target_users")
    def test_create_conflict_raises(
        self, mock_get_users: Mock, mock_create: Mock, app: Flask, runner: CliRunner
    ) -> None:
        """Create when name/alias exists exits non-zero."""
        mock_user = Mock()
        mock_user.id = 1
        mock_get_users.return_value = [mock_user]
        mock_create.side_effect = ValueError("Merchant name or alias already exists")
        register_commands(app)
        result = runner.invoke(
            app.cli,
            ["merchant", "create", "--username", "admin", "--name", "Acme"],
        )
        assert result.exit_code != 0
        assert "already exists" in result.output

    @patch("app.merchants.cli.merchant_services.delete_merchant")
    @patch("app.merchants.cli.merchant_services.get_merchant")
    def test_delete_force_success(self, mock_get: Mock, mock_delete: Mock, app: Flask, runner: CliRunner) -> None:
        """Delete with --force succeeds without prompt."""
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme"
        mock_get.return_value = mock_merchant
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "delete", "1", "--force"])
        assert result.exit_code == 0
        mock_delete.assert_called_once_with(1)

    @patch("app.merchants.cli.merchant_services.get_merchant")
    def test_delete_not_found_exits_nonzero(self, mock_get: Mock, app: Flask, runner: CliRunner) -> None:
        """Delete when merchant not found exits non-zero."""
        mock_get.return_value = None
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "delete", "999", "--force"])
        assert result.exit_code != 0

    @patch("app.merchants.cli.merchant_services.get_unlinked_matching_restaurants_for_merchant")
    @patch("app.merchants.cli.merchant_services.get_merchant")
    @patch("app.merchants.cli._get_target_users")
    def test_show_unlinked(
        self,
        mock_get_users: Mock,
        mock_get_merchant: Mock,
        mock_unlinked: Mock,
        app: Flask,
        runner: CliRunner,
    ) -> None:
        """Show with --unlinked and --username lists matching unlinked restaurants."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_get_users.return_value = [mock_user]
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme"
        mock_merchant.short_name = None
        mock_merchant.category = None
        mock_merchant.website = None
        mock_merchant.restaurants = []
        mock_get_merchant.return_value = mock_merchant
        mock_rest = Mock()
        mock_rest.id = 5
        mock_rest.name = "Acme Downtown"
        mock_unlinked.return_value = [mock_rest]
        with patch("app.merchants.cli.merchant_services.get_restaurants_for_merchant") as mock_link:
            mock_link.return_value = []
            register_commands(app)
            result = runner.invoke(app.cli, ["merchant", "show", "1", "--username", "admin", "--unlinked"])
        assert result.exit_code == 0
        assert "Acme Downtown" in result.output
        assert "Unlinked matching" in result.output

    @patch("app.merchants.cli.merchant_services.associate_unlinked_matching_restaurants")
    @patch("app.merchants.cli.merchant_services.get_unlinked_matching_restaurants_for_merchant")
    @patch("app.merchants.cli.merchant_services.get_merchant")
    @patch("app.merchants.cli._get_target_users")
    def test_link_dry_run(
        self,
        mock_get_users: Mock,
        mock_get_merchant: Mock,
        mock_unlinked: Mock,
        mock_associate: Mock,
        app: Flask,
        runner: CliRunner,
    ) -> None:
        """Link with --dry-run does not call associate."""
        mock_user = Mock()
        mock_user.id = 1
        mock_get_users.return_value = [mock_user]
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme"
        mock_get_merchant.return_value = mock_merchant
        mock_rest = Mock()
        mock_rest.id = 10
        mock_rest.name = "Acme Mall"
        mock_unlinked.return_value = [mock_rest]
        register_commands(app)
        result = runner.invoke(
            app.cli,
            ["merchant", "link", "1", "--username", "admin", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Would link" in result.output
        mock_associate.assert_not_called()

    @patch("app.merchants.cli.merchant_services.get_merchants_with_detailed_stats")
    def test_list_format_json(self, mock_detailed: Mock, app: Flask, runner: CliRunner) -> None:
        """List with --format json outputs valid JSON."""
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme"
        mock_merchant.short_name = "Acme"
        mock_merchant.category = "coffee_shop"
        mock_merchant.website = None
        mock_detailed.return_value = (
            [mock_merchant],
            {
                "merchant_data": {1: {"restaurant_count": 2, "expense_count": 5, "total_amount": 50.0}},
                "stats": {"total_merchants": 1, "total_restaurants": 2, "total_expenses": 5, "total_amount": 50.0},
            },
        )
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "merchants" in data
        assert data["merchants"][0]["name"] == "Acme"
        assert "stats" in data

    @patch("app.merchants.cli.merchant_services.get_merchant_expense_summary")
    @patch("app.merchants.cli.merchant_services.get_merchant")
    def test_show_format_json(self, mock_get: Mock, mock_summary: Mock, app: Flask, runner: CliRunner) -> None:
        """Show with --format json outputs valid JSON."""
        mock_merchant = Mock()
        mock_merchant.id = 1
        mock_merchant.name = "Acme"
        mock_merchant.short_name = "Acme"
        mock_merchant.category = "coffee_shop"
        mock_merchant.website = None
        mock_merchant.restaurants = []
        mock_get.return_value = mock_merchant
        mock_summary.return_value = {"expense_count": 3, "total_amount": 25.0}
        register_commands(app)
        result = runner.invoke(app.cli, ["merchant", "show", "1", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == 1
        assert data["name"] == "Acme"
        assert "expense_summary" in data


class TestMerchantCLIGetTargetUsers:
    """Test _get_target_users helper."""

    @pytest.fixture
    def app(self) -> Flask:
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @patch("app.extensions.db")
    def test_get_target_users_by_user_id_found(self, mock_db: Mock, app: Flask) -> None:
        """_get_target_users returns user when user_id exists."""
        with app.app_context():
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "testuser"
            mock_db.session.get.return_value = mock_user

            result = _get_target_users(user_id=1, username=None, all_users=False)

            assert result == [mock_user]
            mock_db.session.get.assert_called_once()

    @patch("app.extensions.db")
    def test_get_target_users_by_user_id_not_found(self, mock_db: Mock, app: Flask) -> None:
        """_get_target_users raises ClickException when user_id not found."""
        with app.app_context():
            mock_db.session.get.return_value = None

            with pytest.raises(click.ClickException) as exc_info:
                _get_target_users(user_id=999, username=None, all_users=False)

            assert "not found" in str(exc_info.value)

    @patch("app.merchants.cli.User")
    def test_get_target_users_by_username_found(self, mock_user_class: Mock, app: Flask) -> None:
        """_get_target_users returns user when username exists."""
        with app.app_context():
            mock_user = Mock()
            mock_user.id = 1
            mock_user.username = "admin"
            mock_user_class.query.filter_by.return_value.first.return_value = mock_user

            result = _get_target_users(user_id=None, username="admin", all_users=False)

            assert result == [mock_user]

    @patch("app.merchants.cli.User")
    def test_get_target_users_by_username_not_found(self, mock_user_class: Mock, app: Flask) -> None:
        """_get_target_users raises ClickException when username not found."""
        with app.app_context():
            mock_user_class.query.filter_by.return_value.first.return_value = None

            with pytest.raises(click.ClickException) as exc_info:
                _get_target_users(user_id=None, username="nobody", all_users=False)

            assert "not found" in str(exc_info.value)
