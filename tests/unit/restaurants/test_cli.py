"""Tests for restaurant CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from flask import Flask

from app.auth.models import User
from app.restaurants.cli import (
    _apply_restaurant_fixes,
    _build_street_address_from_components,
    _check_restaurant_mismatches,
    _detect_service_level_from_google_data,
    _display_google_info,
    _display_summary,
    _display_user_restaurants,
    _display_validation_summary,
    _format_restaurant_detailed,
    _format_restaurant_simple,
    _get_restaurants_to_validate,
    _get_restaurants_without_google_id,
    _get_target_users,
    _get_user_restaurants,
    _handle_service_level_updates,
    _process_restaurant_validation,
    _suggest_service_level_from_restaurant_data,
    _update_service_levels_for_restaurants,
    _validate_restaurant_with_google,
    list_restaurants,
    register_commands,
    restaurant_cli,
    validate_restaurants,
)
from app.restaurants.models import Restaurant


class TestRestaurantCLI:
    """Test restaurant CLI commands."""

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
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        return user

    @pytest.fixture
    def mock_restaurant(self):
        """Create mock restaurant."""
        restaurant = Mock(spec=Restaurant)
        restaurant.id = 1
        restaurant.name = "Test Restaurant"
        restaurant.cuisine = "Italian"
        restaurant.address = "123 Main St"
        restaurant.city = "Test City"
        restaurant.state = "TS"
        restaurant.postal_code = "12345"
        restaurant.phone = "555-1234"
        restaurant.google_place_id = "test_place_id"
        restaurant.rating = 4.5
        restaurant.service_level = "casual_dining"
        restaurant.expenses = []
        restaurant.user = Mock()
        restaurant.user.username = "testuser"
        restaurant.full_address = "123 Main St, Test City, TS 12345"
        return restaurant

    def test_restaurant_cli_group(self):
        """Test restaurant CLI group creation."""
        assert restaurant_cli.name == "restaurant"
        assert restaurant_cli.help == "Restaurant management commands."

    def test_register_commands(self, app):
        """Test command registration."""
        register_commands(app)
        assert "restaurant" in [cmd.name for cmd in app.cli.commands.values()]

    def test_build_street_address_from_components(self):
        """Test building street address from components."""
        # Test with street number and route
        components = [
            {"types": ["street_number"], "long_name": "123"},
            {"types": ["route"], "long_name": "Main St"},
        ]
        result = _build_street_address_from_components(components)
        assert result == "123 Main St"

        # Test with only route
        components = [{"types": ["route"], "long_name": "Main St"}]
        result = _build_street_address_from_components(components)
        assert result == "Main St"

        # Test with only street number
        components = [{"types": ["street_number"], "long_name": "123"}]
        result = _build_street_address_from_components(components)
        assert result == "123"

        # Test with no matching components
        components = [{"types": ["locality"], "long_name": "Test City"}]
        result = _build_street_address_from_components(components)
        assert result == ""

        # Test with empty components
        result = _build_street_address_from_components([])
        assert result == ""

    @patch("app.restaurants.cli.detect_service_level_from_google_data")
    def test_detect_service_level_from_google_data(self, mock_detect):
        """Test service level detection from Google data."""
        mock_detect.return_value = ("casual_dining", 0.8)
        google_data = {"name": "Test Restaurant"}

        result = _detect_service_level_from_google_data(google_data)
        assert result == ("casual_dining", 0.8)
        mock_detect.assert_called_once_with(google_data)

    @patch("app.restaurants.cli.db")
    def test_get_restaurants_without_google_id_by_restaurant_id(self, mock_db, mock_restaurant):
        """Test getting restaurants without Google ID by restaurant ID."""
        mock_db.session.get.return_value = mock_restaurant
        mock_restaurant.google_place_id = None

        result = _get_restaurants_without_google_id(None, None, False, 1)
        assert result == [mock_restaurant]
        mock_db.session.get.assert_called_once_with(Restaurant, 1)

    @patch("app.restaurants.cli.db")
    def test_get_restaurants_without_google_id_not_found(self, mock_db):
        """Test getting restaurants without Google ID when restaurant not found."""
        mock_db.session.get.return_value = None

        result = _get_restaurants_without_google_id(None, None, False, 1)
        assert result == []

    @patch("app.restaurants.cli._get_target_users")
    def test_get_restaurants_without_google_id_by_users(self, mock_get_users, mock_user, mock_restaurant):
        """Test getting restaurants without Google ID by users."""
        mock_get_users.return_value = [mock_user]
        mock_restaurant.google_place_id = None

        with patch("app.restaurants.cli.Restaurant") as mock_restaurant_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.filter.return_value.all.return_value = [mock_restaurant]
            mock_restaurant_class.query = mock_query

            result = _get_restaurants_without_google_id(None, None, True, None)
            assert result == [mock_restaurant]

    @patch("app.restaurants.cli._get_target_users")
    def test_get_restaurants_without_google_id_no_users(self, mock_get_users):
        """Test getting restaurants without Google ID when no users found."""
        mock_get_users.return_value = []

        result = _get_restaurants_without_google_id(None, None, True, None)
        assert result == []

    @patch("app.restaurants.cli.db")
    def test_update_service_levels_for_restaurants_dry_run(self, mock_db, mock_restaurant):
        """Test updating service levels in dry run mode."""
        mock_restaurant.service_level = None

        with patch("app.restaurants.cli._suggest_service_level_from_restaurant_data") as mock_suggest:
            mock_suggest.return_value = "casual_dining"

            result = _update_service_levels_for_restaurants([mock_restaurant], dry_run=True)
            assert result == 0  # No actual updates in dry run

    @patch("app.restaurants.cli.db")
    def test_update_service_levels_for_restaurants_actual_update(self, mock_db, mock_restaurant):
        """Test updating service levels with actual database update."""
        mock_restaurant.service_level = None

        with patch("app.restaurants.cli._suggest_service_level_from_restaurant_data") as mock_suggest:
            mock_suggest.return_value = "casual_dining"

            result = _update_service_levels_for_restaurants([mock_restaurant], dry_run=False)
            assert result == 1
            assert mock_restaurant.service_level == "casual_dining"
            mock_db.session.commit.assert_called_once()

    @patch("app.restaurants.cli.db")
    def test_update_service_levels_for_restaurants_database_error(self, mock_db, mock_restaurant):
        """Test updating service levels with database error."""
        mock_restaurant.service_level = None
        mock_db.session.commit.side_effect = Exception("Database error")

        with patch("app.restaurants.cli._suggest_service_level_from_restaurant_data") as mock_suggest:
            mock_suggest.return_value = "casual_dining"

            result = _update_service_levels_for_restaurants([mock_restaurant], dry_run=False)
            assert result == 0
            mock_db.session.rollback.assert_called_once()

    @patch("app.restaurants.cli.detect_service_level_from_name")
    def test_suggest_service_level_from_restaurant_data(self, mock_detect, mock_restaurant):
        """Test suggesting service level from restaurant data."""
        mock_detect.return_value = Mock(value="casual_dining")

        result = _suggest_service_level_from_restaurant_data(mock_restaurant)
        assert result == "casual_dining"
        mock_detect.assert_called_once_with(mock_restaurant.name)

    @patch("app.restaurants.cli.db")
    def test_get_target_users_by_user_id(self, mock_db, mock_user):
        """Test getting target users by user ID."""
        mock_db.session.get.return_value = mock_user

        result = _get_target_users(1, None, False)
        assert result == [mock_user]
        mock_db.session.get.assert_called_once_with(User, 1)

    @patch("app.restaurants.cli.db")
    def test_get_target_users_by_user_id_not_found(self, mock_db):
        """Test getting target users by user ID when user not found."""
        mock_db.session.get.return_value = None

        result = _get_target_users(1, None, False)
        assert result == []

    def test_get_target_users_by_username(self, mock_user):
        """Test getting target users by username."""
        with patch("app.restaurants.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_user
            mock_user_class.query = mock_query

            result = _get_target_users(None, "testuser", False)
            assert result == [mock_user]

    def test_get_target_users_by_username_not_found(self):
        """Test getting target users by username when user not found."""
        with patch("app.restaurants.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.first.return_value = None
            mock_user_class.query = mock_query

            result = _get_target_users(None, "testuser", False)
            assert result == []

    def test_get_target_users_all_users(self, mock_user):
        """Test getting all users."""
        with patch("app.restaurants.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.all.return_value = [mock_user]
            mock_user_class.query = mock_query

            result = _get_target_users(None, None, True)
            assert result == [mock_user]

    def test_get_target_users_all_users_none_found(self):
        """Test getting all users when none found."""
        with patch("app.restaurants.cli.User") as mock_user_class:
            mock_query = Mock()
            mock_query.all.return_value = []
            mock_user_class.query = mock_query

            result = _get_target_users(None, None, True)
            assert result == []

    def test_get_target_users_no_options(self):
        """Test getting target users with no options specified."""
        result = _get_target_users(None, None, False)
        assert result == []

    @patch("app.restaurants.cli.get_gmaps_client")
    def test_validate_restaurant_with_google_success(self, mock_get_gmaps, mock_restaurant):
        """Test validating restaurant with Google API success."""
        mock_gmaps = Mock()
        mock_get_gmaps.return_value = mock_gmaps
        mock_gmaps.place.return_value = {
            "result": {
                "name": "Google Restaurant Name",
                "formatted_address": "123 Google St",
                "rating": 4.5,
                "business_status": "OPERATIONAL",
                "type": ["restaurant", "food"],
                "international_phone_number": "+1-555-1234",
                "website": "https://example.com",
                "price_level": 2,
                "address_component": [
                    {"types": ["street_number"], "long_name": "123"},
                    {"types": ["route"], "long_name": "Google St"},
                    {"types": ["locality"], "long_name": "Google City"},
                    {"types": ["administrative_area_level_1"], "short_name": "GC"},
                    {"types": ["postal_code"], "long_name": "12345"},
                    {"types": ["country"], "long_name": "United States"},
                ],
            }
        }

        with patch("app.restaurants.cli._detect_service_level_from_google_data") as mock_detect:
            mock_detect.return_value = ("casual_dining", 0.8)

            result = _validate_restaurant_with_google(mock_restaurant)
            assert result["valid"] is True
            assert result["google_name"] == "Google Restaurant Name"
            assert result["google_address"] == "123 Google St"

    @patch("app.restaurants.cli.get_gmaps_client")
    def test_validate_restaurant_with_google_api_error(self, mock_get_gmaps, mock_restaurant):
        """Test validating restaurant with Google API error."""
        mock_gmaps = Mock()
        mock_get_gmaps.return_value = mock_gmaps
        mock_gmaps.place.return_value = {"status": "INVALID_REQUEST", "error_message": "Invalid place ID"}

        result = _validate_restaurant_with_google(mock_restaurant)
        assert result["valid"] is False
        assert "Invalid place ID" in result["errors"][0]

    @patch("app.restaurants.cli.get_gmaps_client")
    def test_validate_restaurant_with_google_no_response(self, mock_get_gmaps, mock_restaurant):
        """Test validating restaurant with no Google API response."""
        mock_gmaps = Mock()
        mock_get_gmaps.return_value = mock_gmaps
        mock_gmaps.place.return_value = {}

        result = _validate_restaurant_with_google(mock_restaurant)
        assert result["valid"] is False
        assert "No response from Google Places API" in result["errors"][0]

    def test_validate_restaurant_with_google_no_place_id(self, mock_restaurant):
        """Test validating restaurant with no Google Place ID."""
        mock_restaurant.google_place_id = None

        result = _validate_restaurant_with_google(mock_restaurant)
        assert result["valid"] is None
        assert "No Google Place ID available" in result["errors"][0]

    @patch("app.restaurants.cli.get_gmaps_client")
    def test_validate_restaurant_with_google_api_not_configured(self, mock_get_gmaps, mock_restaurant):
        """Test validating restaurant when Google API not configured."""
        mock_get_gmaps.return_value = None

        result = _validate_restaurant_with_google(mock_restaurant)
        assert result["valid"] is False
        assert "Google Maps API not configured" in result["errors"][0]

    def test_validate_restaurant_with_google_import_error(self, mock_restaurant):
        """Test validating restaurant with import error."""
        with patch("app.restaurants.cli.get_gmaps_client", side_effect=ImportError):
            result = _validate_restaurant_with_google(mock_restaurant)
            assert result["valid"] is False
            assert "Google Places API service not available" in result["errors"][0]

    def test_validate_restaurant_with_google_exception(self, mock_restaurant):
        """Test validating restaurant with unexpected exception."""
        with patch("app.restaurants.cli.get_gmaps_client", side_effect=Exception("Unexpected error")):
            with patch("app.restaurants.cli.current_app") as mock_app:
                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Unexpected error" in result["errors"][0]
                mock_app.logger.error.assert_called_once()

    def test_get_user_restaurants_with_google_id(self, mock_user, mock_restaurant):
        """Test getting user restaurants with Google ID filter."""
        with patch("app.restaurants.cli.Restaurant") as mock_restaurant_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.filter.return_value.order_by.return_value.all.return_value = [
                mock_restaurant
            ]
            mock_restaurant_class.query = mock_query

            result = _get_user_restaurants(mock_user, with_google_id=True)
            assert result == [mock_restaurant]

    def test_get_user_restaurants_without_google_id(self, mock_user, mock_restaurant):
        """Test getting user restaurants without Google ID filter."""
        with patch("app.restaurants.cli.Restaurant") as mock_restaurant_class:
            mock_query = Mock()
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_restaurant]
            mock_restaurant_class.query = mock_query

            result = _get_user_restaurants(mock_user, with_google_id=False)
            assert result == [mock_restaurant]

    def test_format_restaurant_detailed(self, mock_restaurant, capsys):
        """Test formatting detailed restaurant information."""
        _format_restaurant_detailed(mock_restaurant)
        captured = capsys.readouterr()
        assert "📍 Test Restaurant 🌐" in captured.out
        assert "ID: 1" in captured.out
        assert "Cuisine: Italian" in captured.out
        assert "Address: 123 Main St" in captured.out
        assert "Location: Test City, TS, 12345" in captured.out
        assert "Phone: 555-1234" in captured.out
        assert "Google Place ID: test_place_id" in captured.out
        assert "Expenses: 0" in captured.out
        assert "Rating: 4.5/5.0" in captured.out

    def test_format_restaurant_simple(self, mock_restaurant, capsys):
        """Test formatting simple restaurant information."""
        _format_restaurant_simple(mock_restaurant)
        captured = capsys.readouterr()
        assert "- Test Restaurant 🌐 (0 expenses)" in captured.out

    def test_display_user_restaurants(self, mock_user, mock_restaurant, capsys):
        """Test displaying user restaurants."""
        _display_user_restaurants(mock_user, [mock_restaurant], detailed=False, with_google_id=False)
        captured = capsys.readouterr()
        assert "👤 testuser (ID: 1) - 1 restaurants:" in captured.out
        assert "- Test Restaurant 🌐 (0 expenses)" in captured.out

    def test_display_user_restaurants_detailed(self, mock_user, mock_restaurant, capsys):
        """Test displaying user restaurants in detailed mode."""
        _display_user_restaurants(mock_user, [mock_restaurant], detailed=True, with_google_id=False)
        captured = capsys.readouterr()
        assert "👤 testuser (ID: 1) - 1 restaurants:" in captured.out
        assert "📍 Test Restaurant 🌐" in captured.out

    def test_display_user_restaurants_empty(self, mock_user, capsys):
        """Test displaying empty user restaurants."""
        result = _display_user_restaurants(mock_user, [], detailed=False, with_google_id=False)
        captured = capsys.readouterr()
        assert "👤 testuser (ID: 1) - 0 restaurants:" in captured.out
        assert "(No restaurants)" in captured.out
        assert result == 0

    def test_display_summary(self, capsys):
        """Test displaying summary statistics."""
        _display_summary(10, 7)
        captured = capsys.readouterr()
        assert "📊 Summary:" in captured.out
        assert "Total restaurants: 10" in captured.out
        assert "With Google Place ID: 7" in captured.out
        assert "Without Google Place ID: 3" in captured.out

    def test_list_restaurants_no_options(self, runner, app):
        """Test list restaurants with no options specified."""
        with app.app_context():
            result = runner.invoke(list_restaurants, [])
            assert result.exit_code == 0
            assert "❌ Error: Must specify --user-id, --username, or --all-users" in result.output

    def test_list_restaurants_user_not_found(self, runner, app):
        """Test list restaurants when user not found."""
        with app.app_context():
            with patch("app.restaurants.cli._get_target_users") as mock_get_users:
                mock_get_users.return_value = []

                result = runner.invoke(list_restaurants, ["--user-id", "999"])
                assert result.exit_code == 0
                # Should return early when no users found

    def test_list_restaurants_success(self, runner, app, mock_user, mock_restaurant):
        """Test successful list restaurants."""
        with app.app_context():
            with patch("app.restaurants.cli._get_target_users") as mock_get_users:
                with patch("app.restaurants.cli._get_user_restaurants") as mock_get_restaurants:
                    with patch("app.restaurants.cli._display_user_restaurants") as mock_display:
                        mock_get_users.return_value = [mock_user]
                        mock_get_restaurants.return_value = [mock_restaurant]
                        mock_display.return_value = 1

                        result = runner.invoke(list_restaurants, ["--user-id", "1"])
                        assert result.exit_code == 0
                        assert "🍽️  Restaurants for 1 user(s):" in result.output

    def test_get_restaurants_to_validate_by_restaurant_id(self, mock_restaurant):
        """Test getting restaurants to validate by restaurant ID."""
        with patch("app.restaurants.cli.db") as mock_db:
            mock_db.session.get.return_value = mock_restaurant

            restaurants, counts = _get_restaurants_to_validate(None, None, False, 1)
            assert restaurants == [mock_restaurant]
            assert counts["total_restaurants"] == 1
            assert counts["with_google_id"] == 1
            assert counts["missing_google_id"] == 0

    def test_get_restaurants_to_validate_restaurant_not_found(self):
        """Test getting restaurants to validate when restaurant not found."""
        with patch("app.restaurants.cli.db") as mock_db:
            mock_db.session.get.return_value = None

            restaurants, counts = _get_restaurants_to_validate(None, None, False, 999)
            assert restaurants == []
            assert counts["total_restaurants"] == 0

    def test_get_restaurants_to_validate_no_options(self):
        """Test getting restaurants to validate with no options."""
        restaurants, counts = _get_restaurants_to_validate(None, None, False, None)
        assert restaurants == []
        assert counts["total_restaurants"] == 0

    def test_check_restaurant_mismatches_name(self, mock_restaurant):
        """Test checking restaurant mismatches for name."""
        validation_result = {
            "google_name": "Different Name",
            "google_street_address": "123 Main St",
            "google_service_level": None,
        }

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Name: 'Test Restaurant' vs Google: 'Different Name'" in mismatches[0]
        assert fixes["name"] == "Different Name"

    def test_check_restaurant_mismatches_address(self, mock_restaurant):
        """Test checking restaurant mismatches for address."""
        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "456 Different St",
            "google_service_level": None,
        }

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Address: '123 Main St' vs Google: '456 Different St'" in mismatches[0]
        assert fixes["address"] == "456 Different St"

    def test_check_restaurant_mismatches_service_level(self, mock_restaurant):
        """Test checking restaurant mismatches for service level."""
        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": ("fine_dining", 0.9),
        }

        with patch("app.restaurants.cli.validate_restaurant_service_level") as mock_validate:
            mock_validate.return_value = (True, "Service level mismatch", "fine_dining")

            mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
            assert len(mismatches) == 1
            assert "Service level mismatch" in mismatches[0]
            assert fixes["service_level"] == "fine_dining"

    def test_apply_restaurant_fixes_dry_run(self, mock_restaurant):
        """Test applying restaurant fixes in dry run mode."""
        fixes = {"name": "New Name", "address": "New Address"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=True)
        assert result is True
        # In dry run, no actual changes should be made
        assert mock_restaurant.name == "Test Restaurant"

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_actual(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with actual changes."""
        fixes = {"name": "New Name", "address": "New Address"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is True
        assert mock_restaurant.name == "New Name"
        assert mock_restaurant.address == "New Address"
        mock_db.session.commit.assert_called_once()

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_error(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with database error."""
        fixes = {"name": "New Name"}
        mock_db.session.commit.side_effect = Exception("Database error")

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is False
        mock_db.session.rollback.assert_called_once()

    def test_display_google_info(self, capsys):
        """Test displaying Google Places information."""
        validation_result = {
            "google_status": "OPERATIONAL",
            "google_rating": 4.5,
            "google_phone": "+1-555-1234",
            "google_website": "https://example.com",
            "google_price_level": 2,
            "types": ["restaurant", "food"],
            "google_service_level": ("casual_dining", 0.8),
        }

        with patch("app.restaurants.cli.get_service_level_display_info") as mock_display_info:
            mock_display_info.return_value = {"display_name": "Casual Dining"}

            _display_google_info(validation_result)
            captured = capsys.readouterr()
            assert "📊 Status: OPERATIONAL" in captured.out
            assert "⭐ Google Rating: 4.5/5.0" in captured.out
            assert "📞 Phone: +1-555-1234" in captured.out
            assert "🌐 Website: https://example.com" in captured.out
            assert "💲 Price Level: 💰💰" in captured.out
            assert "🏷️  Types: restaurant, food" in captured.out
            assert "🍽️  Service Level: Casual Dining (confidence: 0.80)" in captured.out

    def test_display_google_info_types_list(self, capsys):
        """Test displaying Google Places information with types as list."""
        validation_result = {"types": ["restaurant", "food", "establishment", "point_of_interest"]}

        _display_google_info(validation_result)
        captured = capsys.readouterr()
        assert "🏷️  Types: restaurant, food, establishment" in captured.out

    def test_display_google_info_types_string(self, capsys):
        """Test displaying Google Places information with types as string."""
        validation_result = {"types": "restaurant"}

        _display_google_info(validation_result)
        captured = capsys.readouterr()
        assert "🏷️  Types: restaurant" in captured.out

    @patch("app.restaurants.cli._validate_restaurant_with_google")
    def test_process_restaurant_validation_valid(self, mock_validate, mock_restaurant):
        """Test processing restaurant validation with valid result."""
        mock_validate.return_value = {
            "valid": True,
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": None,
            "errors": [],
        }

        with patch("app.restaurants.cli._check_restaurant_mismatches") as mock_check:
            with patch("app.restaurants.cli._display_google_info"):
                mock_check.return_value = ([], {})

                status, fixed = _process_restaurant_validation(mock_restaurant, False, False)
                assert status == "valid"
                assert fixed is False

    @patch("app.restaurants.cli._validate_restaurant_with_google")
    def test_process_restaurant_validation_invalid(self, mock_validate, mock_restaurant):
        """Test processing restaurant validation with invalid result."""
        mock_validate.return_value = {"valid": False, "errors": ["Invalid place ID"]}

        status, fixed = _process_restaurant_validation(mock_restaurant, False, False)
        assert status == "invalid"
        assert fixed is False

    @patch("app.restaurants.cli._validate_restaurant_with_google")
    def test_process_restaurant_validation_error(self, mock_validate, mock_restaurant):
        """Test processing restaurant validation with error result."""
        mock_validate.return_value = {"valid": None, "errors": ["No Google Place ID available"]}

        status, fixed = _process_restaurant_validation(mock_restaurant, False, False)
        assert status == "error"
        assert fixed is False

    def test_handle_service_level_updates_disabled(self):
        """Test handling service level updates when disabled."""
        result = _handle_service_level_updates(None, None, False, None, False, False)
        assert result == (0, 0)

    @patch("app.restaurants.cli._get_restaurants_without_google_id")
    def test_handle_service_level_updates_enabled(self, mock_get_restaurants, mock_restaurant):
        """Test handling service level updates when enabled."""
        mock_get_restaurants.return_value = [mock_restaurant]

        with patch("app.restaurants.cli._update_service_levels_for_restaurants") as mock_update:
            mock_update.return_value = 1

            result = _handle_service_level_updates(None, None, True, None, True, False)
            assert result == (1, 1)

    def test_display_validation_summary(self, capsys):
        """Test displaying validation summary."""
        _display_validation_summary(
            valid_count=5,
            invalid_count=2,
            error_count=1,
            fixed_count=3,
            mismatch_count=4,
            total_restaurants=10,
            missing_google_id=3,
            with_google_id=7,
            fix_mismatches=True,
            dry_run=False,
            service_level_updated_count=2,
            service_level_total_count=3,
        )
        captured = capsys.readouterr()
        assert "📊 Validation Summary:" in captured.out
        assert "🍽️  Total restaurants: 10" in captured.out
        assert "🌐 With Google Place ID: 7" in captured.out
        assert "📍 Missing Google Place ID: 3" in captured.out
        assert "✅ Valid: 5" in captured.out
        assert "❌ Invalid: 2" in captured.out
        assert "⚠️  Cannot validate: 1" in captured.out
        assert "🔄 With mismatches: 4" in captured.out
        assert "🔧 Fixed: 3 restaurants" in captured.out
        assert "🍽️  Service Level Updates:" in captured.out
        assert "📊 Total without Google Place ID: 3" in captured.out
        assert "✅ Updated: 2 restaurants" in captured.out

    def test_validate_restaurants_no_options(self, runner, app):
        """Test validate restaurants with no options."""
        with app.app_context():
            result = runner.invoke(validate_restaurants, [])
            assert result.exit_code == 0
            # Should show error about missing options

    def test_validate_restaurants_success(self, runner, app, mock_restaurant):
        """Test successful restaurant validation."""
        with app.app_context():
            with patch("app.restaurants.cli._get_restaurants_to_validate") as mock_get_restaurants:
                with patch("app.restaurants.cli._handle_service_level_updates") as mock_service_level:
                    with patch("app.restaurants.cli._handle_restaurant_validation") as mock_validation:
                        mock_get_restaurants.return_value = (
                            [mock_restaurant],
                            {"total_restaurants": 1, "with_google_id": 1, "missing_google_id": 0},
                        )
                        mock_service_level.return_value = (0, 0)

                        result = runner.invoke(validate_restaurants, ["--user-id", "1"])
                        assert result.exit_code == 0
                        mock_validation.assert_called_once()
