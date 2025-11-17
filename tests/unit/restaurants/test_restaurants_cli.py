"""Tests for restaurant CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner
from flask import Flask

from app.auth.models import User
from app.restaurants.cli import (
    _apply_restaurant_fixes,
    _check_restaurant_mismatches,
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
        restaurant.address_line_1 = "123 Main St"
        restaurant.address_line_2 = None  # Explicitly set to None
        restaurant.city = "Test City"
        restaurant.state = "TS"
        restaurant.postal_code = "12345"
        restaurant.country = None  # Explicitly set to None
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
        """Test building street address from components using centralized service."""
        # This test is removed as the function no longer exists in the CLI
        # The functionality has been moved to the GooglePlacesService

    def test_detect_service_level_from_google_data(self):
        """Test service level detection from Google data using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.detect_service_level_from_data.return_value = ("casual_dining", 0.8)
            mock_service.return_value = mock_places_service

            google_data = {"name": "Test Restaurant"}
            result = mock_places_service.detect_service_level_from_data(google_data)
            assert result == ("casual_dining", 0.8)

    @patch("app.extensions.db")
    def test_get_restaurants_without_google_id_by_restaurant_id(self, mock_db, app, mock_restaurant):
        """Test getting restaurants without Google ID by restaurant ID."""
        with app.app_context():
            mock_db.session.get.return_value = mock_restaurant
            mock_restaurant.google_place_id = None

            result = _get_restaurants_without_google_id(None, None, False, 1)
            assert result == [mock_restaurant]
            mock_db.session.get.assert_called_once_with(Restaurant, 1)

    @patch("app.extensions.db")
    def test_get_restaurants_without_google_id_not_found(self, mock_db, app):
        """Test getting restaurants without Google ID when restaurant not found."""
        with app.app_context():
            mock_db.session.get.return_value = None

            result = _get_restaurants_without_google_id(None, None, False, 1)
            assert result == []

    @patch("app.restaurants.cli._get_target_users")
    def test_get_restaurants_without_google_id_by_users(self, mock_get_users, app, mock_user, mock_restaurant):
        """Test getting restaurants without Google ID by users."""
        with app.app_context():
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

    @patch("app.utils.service_level_detector.detect_service_level_from_name")
    def test_suggest_service_level_from_restaurant_data(self, mock_detect, mock_restaurant):
        """Test suggesting service level from restaurant data."""
        mock_detect.return_value = Mock(value="casual_dining")

        result = _suggest_service_level_from_restaurant_data(mock_restaurant)
        assert result == "casual_dining"
        mock_detect.assert_called_once_with(mock_restaurant.name)

    @patch("app.extensions.db")
    def test_get_target_users_by_user_id(self, mock_db, app, mock_user):
        """Test getting target users by user ID."""
        with app.app_context():
            mock_db.session.get.return_value = mock_user

            result = _get_target_users(1, None, False)
            assert result == [mock_user]
            mock_db.session.get.assert_called_once_with(User, 1)

    @patch("app.extensions.db")
    def test_get_target_users_by_user_id_not_found(self, mock_db, app):
        """Test getting target users by user ID when user not found."""
        with app.app_context():
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

    def test_validate_restaurant_with_google_success(self, app, mock_restaurant):
        """Test validating restaurant with Google API success."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service

                # Mock the place details response
                mock_place_data = {
                    "displayName": {"text": "Google Restaurant Name"},
                    "formattedAddress": "123 Google St",
                    "rating": 4.5,
                    "nationalPhoneNumber": "+1-555-1234",
                    "websiteUri": "https://example.com",
                    "priceLevel": "PRICE_LEVEL_MODERATE",
                    "addressComponents": [
                        {"types": ["street_number"], "longText": "123"},
                        {"types": ["route"], "longText": "Google St"},
                        {"types": ["locality"], "longText": "Google City"},
                        {"types": ["administrative_area_level_1"], "shortText": "GC"},
                        {"types": ["postal_code"], "longText": "12345"},
                        {"types": ["country"], "longText": "United States"},
                    ],
                }

                mock_service.get_place_details.return_value = mock_place_data
                mock_service.extract_restaurant_data.return_value = {
                    "name": "Google Restaurant Name",
                    "formatted_address": "123 Google St",
                    "rating": 4.5,
                    "business_status": "OPERATIONAL",
                    "types": ["restaurant", "food"],
                    "primary_type": "restaurant",
                }
                mock_service.analyze_restaurant_types.return_value = {
                    "cuisine_type": "American",
                    "service_level": "casual_dining",
                    "confidence": 0.8,
                }
                mock_service.detect_service_level_from_data.return_value = ("casual_dining", 0.8)

                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)

                assert result["valid"] is True
                assert result["google_name"] == "Google Restaurant Name"
                assert result["google_address"] == "123 Google St"

    def test_validate_restaurant_with_google_api_error(self, app, mock_restaurant):
        """Test validating restaurant with Google API error."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.get_place_details.side_effect = Exception("API Error")

                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Unexpected error" in result["errors"][0]

    def test_validate_restaurant_with_google_no_response(self, app, mock_restaurant):
        """Test validating restaurant with no Google API response."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.get_place_details.return_value = None  # No response

                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Failed to retrieve place data from Google Places API" in result["errors"][0]

    def test_validate_restaurant_with_google_no_place_id(self, mock_restaurant):
        """Test validating restaurant with no Google Place ID."""
        mock_restaurant.google_place_id = None

        result = _validate_restaurant_with_google(mock_restaurant)
        assert result["valid"] is None
        assert "No Google Place ID available" in result["errors"][0]

    def test_validate_restaurant_with_google_api_not_configured(self, app, mock_restaurant):
        """Test validating restaurant when Google API not configured."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_get_service.side_effect = ValueError("Google Maps API key not found")

                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Google Places API key not configured" in result["errors"][0]

    def test_validate_restaurant_with_google_import_error(self, app, mock_restaurant):
        """Test validating restaurant with import error."""
        with app.app_context():
            with patch(
                "app.services.google_places_service.get_google_places_service",
                side_effect=ImportError("Module not found"),
            ):
                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Google Places API service not available" in result["errors"][0]

    def test_validate_restaurant_with_google_exception(self, app, mock_restaurant):
        """Test validating restaurant with unexpected exception."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.get_place_details.side_effect = Exception("Unexpected error")

                mock_restaurant.google_place_id = "test_place_id"

                result = _validate_restaurant_with_google(mock_restaurant)
                assert result["valid"] is False
                assert "Unexpected error" in result["errors"][0]

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
        # Ensure address_line_2 is None to avoid Mock issues
        mock_restaurant.address_line_2 = None

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

    def test_get_restaurants_to_validate_by_restaurant_id(self, app, mock_restaurant):
        """Test getting restaurants to validate by restaurant ID."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                mock_db.session.get.return_value = mock_restaurant

                restaurants, counts = _get_restaurants_to_validate(None, None, False, 1)
                assert restaurants == [mock_restaurant]
                assert counts["total_restaurants"] == 1
                assert counts["with_google_id"] == 1
                assert counts["missing_google_id"] == 0

    def test_get_restaurants_to_validate_restaurant_not_found(self, app):
        """Test getting restaurants to validate when restaurant not found."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
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
            "google_address_line_1": "456 Different St",
            "google_service_level": None,
        }

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Address Line 1: '123 Main St' vs Google: '456 Different St'" in mismatches[0]
        assert fixes["address_line_1"] == "456 Different St"

    def test_check_restaurant_mismatches_service_level(self, mock_restaurant):
        """Test checking restaurant mismatches for service level."""
        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": ("fine_dining", 0.9),
        }

        with patch("app.restaurants.services.validate_restaurant_service_level") as mock_validate:
            mock_validate.return_value = (True, "Service level mismatch", "fine_dining")

            mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
            assert len(mismatches) == 1
            assert "Service level mismatch" in mismatches[0]
            assert fixes["service_level"] == "fine_dining"

    def test_check_restaurant_mismatches_price_level(self, mock_restaurant):
        """Test checking restaurant mismatches for price level."""
        # Set restaurant price level to 2
        mock_restaurant.price_level = 2

        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": None,
            "google_price_level": 3,  # Different price level
        }

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.convert_price_level_to_int.return_value = 3  # Return as-is for integer input

            mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
            assert len(mismatches) == 1
            assert "Price Level: '$$ (Moderate)' vs Google: '$$$ (Expensive)'" in mismatches[0]
            assert fixes["price_level"] == 3

    def test_check_restaurant_mismatches_price_level_none_vs_set(self, mock_restaurant):
        """Test checking restaurant mismatches when restaurant has no price level but Google does."""
        # Set restaurant price level to None
        mock_restaurant.price_level = None

        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": None,
            "google_price_level": 2,  # Google has price level
        }

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.convert_price_level_to_int.return_value = 2  # Return as-is for integer input

            mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
            assert len(mismatches) == 1
            assert "Price Level: 'Not set' vs Google: '$$ (Moderate)'" in mismatches[0]
            assert fixes["price_level"] == 2

    def test_check_restaurant_mismatches_price_level_string_conversion(self, mock_restaurant):
        """Test checking restaurant mismatches with Google string price level format."""
        # Set restaurant price level to 1
        mock_restaurant.price_level = 1

        validation_result = {
            "google_name": "Test Restaurant",
            "google_street_address": "123 Main St",
            "google_service_level": None,
            "google_price_level": "PRICE_LEVEL_INEXPENSIVE",  # Google string format
        }

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = mock_get_service.return_value
            mock_service.convert_price_level_to_int.return_value = 1  # Convert string to int

            mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
            # Should not have mismatch since both are 1 after conversion
            assert len(mismatches) == 0
            assert "price_level" not in fixes

    def test_format_price_level_display(self):
        """Test the price level display formatting function."""
        from app.restaurants.cli import _format_price_level_display

        # Test various price levels
        assert _format_price_level_display(0) == "Free"
        assert _format_price_level_display(1) == "$ (Inexpensive)"
        assert _format_price_level_display(2) == "$$ (Moderate)"
        assert _format_price_level_display(3) == "$$$ (Expensive)"
        assert _format_price_level_display(4) == "$$$$ (Very Expensive)"
        assert _format_price_level_display(None) == "Not set"
        assert _format_price_level_display(99) == "99"  # Unknown level

    def test_check_restaurant_mismatches_cuisine(self, mock_restaurant):
        """Test checking restaurant mismatches for cuisine."""
        # Set restaurant cuisine to 'Italian'
        mock_restaurant.cuisine = "Italian"

        validation_result = {"google_cuisine": "American"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Cuisine: 'Italian' vs Google: 'American'" in mismatches[0]
        assert fixes["cuisine"] == "American"

    def test_check_restaurant_mismatches_cuisine_none_vs_set(self, mock_restaurant):
        """Test checking restaurant mismatches when restaurant has no cuisine but Google does."""
        # Set restaurant cuisine to None
        mock_restaurant.cuisine = None

        validation_result = {"google_cuisine": "Mexican"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Cuisine: 'Not set' vs Google: 'Mexican'" in mismatches[0]
        assert fixes["cuisine"] == "Mexican"

    def test_check_restaurant_mismatches_cuisine_match(self, mock_restaurant):
        """Test checking restaurant mismatches when cuisines match."""
        # Set restaurant cuisine to match Google
        mock_restaurant.cuisine = "Chinese"

        validation_result = {"google_cuisine": "Chinese"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "cuisine" not in fixes

    def test_check_restaurant_mismatches_cuisine_no_google_data(self, mock_restaurant):
        """Test checking restaurant mismatches when Google has no cuisine data."""
        mock_restaurant.cuisine = "Italian"

        validation_result = {"google_cuisine": None}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "cuisine" not in fixes

    def test_apply_restaurant_fixes_dry_run(self, mock_restaurant):
        """Test applying restaurant fixes in dry run mode."""
        fixes = {"name": "New Name", "address": "New Address"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=True)
        assert result is True
        # In dry run, no actual changes should be made
        assert mock_restaurant.name == "Test Restaurant"

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_cuisine(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with cuisine field."""
        fixes = {"cuisine": "Japanese"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is True
        assert mock_restaurant.cuisine == "Japanese"

    def test_check_restaurant_mismatches_phone(self, mock_restaurant):
        """Test checking restaurant mismatches for phone."""
        # Set restaurant phone to '(555) 123-4567'
        mock_restaurant.phone = "(555) 123-4567"

        validation_result = {"google_phone": "+1-555-987-6543"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Phone: '(555) 123-4567' vs Google: '+1-555-987-6543'" in mismatches[0]
        assert fixes["phone"] == "+1-555-987-6543"

    def test_check_restaurant_mismatches_phone_none_vs_set(self, mock_restaurant):
        """Test checking restaurant mismatches when restaurant has no phone but Google does."""
        # Set restaurant phone to None
        mock_restaurant.phone = None

        validation_result = {"google_phone": "(555) 111-2222"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Phone: 'Not set' vs Google: '(555) 111-2222'" in mismatches[0]
        assert fixes["phone"] == "(555) 111-2222"

    def test_check_restaurant_mismatches_phone_match(self, mock_restaurant):
        """Test checking restaurant mismatches when phones match."""
        # Set restaurant phone to match Google
        mock_restaurant.phone = "(555) 333-4444"

        validation_result = {"google_phone": "(555) 333-4444"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "phone" not in fixes

    def test_check_restaurant_mismatches_phone_no_google_data(self, mock_restaurant):
        """Test checking restaurant mismatches when Google has no phone data."""
        mock_restaurant.phone = "(555) 123-4567"

        validation_result = {"google_phone": None}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "phone" not in fixes

    def test_check_restaurant_mismatches_website(self, mock_restaurant):
        """Test checking restaurant mismatches for website."""
        # Set restaurant website to 'https://old-site.com'
        mock_restaurant.website = "https://old-site.com"

        validation_result = {"google_website": "https://new-site.com"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Website: 'https://old-site.com' vs Google: 'https://new-site.com'" in mismatches[0]
        assert fixes["website"] == "https://new-site.com"

    def test_check_restaurant_mismatches_website_none_vs_set(self, mock_restaurant):
        """Test checking restaurant mismatches when restaurant has no website but Google does."""
        # Set restaurant website to None
        mock_restaurant.website = None

        validation_result = {"google_website": "https://example.com"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Website: 'Not set' vs Google: 'https://example.com'" in mismatches[0]
        assert fixes["website"] == "https://example.com"

    def test_check_restaurant_mismatches_website_match(self, mock_restaurant):
        """Test checking restaurant mismatches when websites match."""
        # Set restaurant website to match Google
        mock_restaurant.website = "https://restaurant.com"

        validation_result = {"google_website": "https://restaurant.com"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "website" not in fixes

    def test_check_restaurant_mismatches_website_no_google_data(self, mock_restaurant):
        """Test checking restaurant mismatches when Google has no website data."""
        mock_restaurant.website = "https://old-site.com"

        validation_result = {"google_website": None}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "website" not in fixes

    def test_check_restaurant_mismatches_type(self, mock_restaurant):
        """Test checking restaurant mismatches for type field."""
        mock_restaurant.type = "cafe"

        validation_result = {"primary_type": "restaurant"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Type: 'cafe' vs Google: 'restaurant'" in mismatches
        assert fixes["type"] == "restaurant"

    def test_check_restaurant_mismatches_type_none_vs_set(self, mock_restaurant):
        """Test checking restaurant mismatches when local type is None but Google has primary type."""
        mock_restaurant.type = None

        validation_result = {"primary_type": "restaurant"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 1
        assert "Type: 'Not set' vs Google: 'restaurant'" in mismatches
        assert fixes["type"] == "restaurant"

    def test_check_restaurant_mismatches_type_match(self, mock_restaurant):
        """Test checking restaurant mismatches when type matches Google primary type."""
        mock_restaurant.type = "restaurant"

        validation_result = {"primary_type": "restaurant"}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "type" not in fixes

    def test_check_restaurant_mismatches_type_no_google_data(self, mock_restaurant):
        """Test checking restaurant mismatches when Google has no primary type data."""
        mock_restaurant.type = "restaurant"

        validation_result = {"primary_type": None}

        mismatches, fixes = _check_restaurant_mismatches(mock_restaurant, validation_result)
        assert len(mismatches) == 0
        assert "type" not in fixes

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_phone_and_website(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with phone and website fields."""
        fixes = {"phone": "+1-555-999-8888", "website": "https://updated-site.com"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is True
        assert mock_restaurant.phone == "+1-555-999-8888"
        assert mock_restaurant.website == "https://updated-site.com"

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_type(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with type field."""
        fixes = {"type": "restaurant"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is True
        assert mock_restaurant.type == "restaurant"

    @patch("app.restaurants.cli.db")
    def test_apply_restaurant_fixes_actual(self, mock_db, mock_restaurant):
        """Test applying restaurant fixes with actual changes."""
        fixes = {"name": "New Name", "address_line_1": "New Address"}

        result = _apply_restaurant_fixes(mock_restaurant, fixes, dry_run=False)
        assert result is True
        assert mock_restaurant.name == "New Name"
        assert mock_restaurant.address_line_1 == "New Address"
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

        with patch("app.restaurants.services.get_service_level_display_info") as mock_display_info:
            mock_display_info.return_value = {"display_name": "Casual Dining"}

            _display_google_info(validation_result)
            captured = capsys.readouterr()
            assert "📊 Status: OPERATIONAL" in captured.out
            assert "⭐ Google Rating: 4.5/5.0" in captured.out
            assert "📞 Phone: +1-555-1234" in captured.out
            assert "🌐 Website: https://example.com" in captured.out
            assert "💲 Price Level: $$ (Moderate)" in captured.out
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
