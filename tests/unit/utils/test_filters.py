"""Tests for utils filters to improve coverage."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock

from app.utils.filters import (
    _build_search_query,
    _extract_restaurant_data,
    google_maps_url,
    init_app,
    time_ago,
)


class TestTimeAgo:
    """Test time_ago filter function."""

    def test_time_ago_none_input(self) -> None:
        """Test time_ago with None input."""

        result = time_ago(None)  # type: ignore[arg-type]
        assert result == "Never"

    def test_time_ago_just_now(self) -> None:
        """Test time_ago with very recent datetime."""
        now = datetime.now(UTC)
        result = time_ago(now)
        assert result == "just now"

    def test_time_ago_seconds_ago(self) -> None:
        """Test time_ago with seconds ago."""
        now = datetime.now(UTC)
        past = now - timedelta(seconds=30)
        result = time_ago(past)
        assert result == "30 seconds ago"

    def test_time_ago_minutes_ago(self) -> None:
        """Test time_ago with minutes ago."""
        now = datetime.now(UTC)
        past = now - timedelta(minutes=5)
        result = time_ago(past)
        assert result == "5 minutes ago"

    def test_time_ago_hours_ago(self) -> None:
        """Test time_ago with hours ago."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=3)
        result = time_ago(past)
        assert result == "3 hours ago"

    def test_time_ago_days_ago(self) -> None:
        """Test time_ago with days ago."""
        now = datetime.now(UTC)
        past = now - timedelta(days=7)
        result = time_ago(past)
        # 7 days = 1 week, so it should show as "1 week ago"
        assert result == "1 week ago"

    def test_time_ago_weeks_ago(self) -> None:
        """Test time_ago with weeks ago."""
        now = datetime.now(UTC)
        past = now - timedelta(weeks=2)
        result = time_ago(past)
        assert result == "2 weeks ago"  # 2 weeks = 14 days, but shows as weeks

    def test_time_ago_months_ago(self) -> None:
        """Test time_ago with months ago."""
        now = datetime.now(UTC)
        past = now - timedelta(days=60)  # ~2 months
        result = time_ago(past)
        assert result == "2 months ago"

    def test_time_ago_years_ago(self) -> None:
        """Test time_ago with years ago."""
        now = datetime.now(UTC)
        past = now - timedelta(days=400)  # ~1 year
        result = time_ago(past)
        assert result == "1 year ago"

    def test_time_ago_naive_datetime(self) -> None:
        """Test time_ago with naive datetime (no timezone)."""
        now = datetime.now()
        past = now - timedelta(hours=2)
        result = time_ago(past)
        assert "hours ago" in result

    def test_time_ago_singular_forms(self) -> None:
        """Test time_ago with singular forms."""
        now = datetime.now(UTC)

        # 1 second ago
        past = now - timedelta(seconds=1)
        result = time_ago(past)
        assert result == "1 second ago"

        # 1 minute ago
        past = now - timedelta(minutes=1)
        result = time_ago(past)
        assert result == "1 minute ago"

        # 1 hour ago
        past = now - timedelta(hours=1)
        result = time_ago(past)
        assert result == "1 hour ago"

        # 1 day ago
        past = now - timedelta(days=1)
        result = time_ago(past)
        assert result == "1 day ago"

        # 1 month ago
        past = now - timedelta(days=30)
        result = time_ago(past)
        assert result == "1 month ago"

        # 1 year ago
        past = now - timedelta(days=365)
        result = time_ago(past)
        assert result == "1 year ago"


class TestExtractRestaurantData:
    """Test _extract_restaurant_data helper function."""

    def test_extract_restaurant_data_dict(self) -> None:
        """Test extracting data from dictionary."""
        data = {
            "name": "Test Restaurant",
            "google_place_id": "place123",
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

        result = _extract_restaurant_data(data)

        assert result == {
            "name": "Test Restaurant",
            "google_place_id": "place123",
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

    def test_extract_restaurant_data_dict_partial(self) -> None:
        """Test extracting data from partial dictionary."""
        data = {"name": "Test Restaurant", "city": "Test City"}

        result = _extract_restaurant_data(data)

        assert result == {
            "name": "Test Restaurant",
            "google_place_id": None,
            "address": "",
            "city": "Test City",
            "state": "",
            "postal_code": "",
        }

    def test_extract_restaurant_data_object(self) -> None:
        """Test extracting data from object."""
        mock_obj = Mock()
        mock_obj.name = "Test Restaurant"
        mock_obj.google_place_id = "place123"
        mock_obj.address_line_1 = "123 Main St"
        mock_obj.address = "123 Main St"  # The address property that combines address lines
        mock_obj.city = "Test City"
        mock_obj.state = "TS"
        mock_obj.postal_code = "12345"

        result = _extract_restaurant_data(mock_obj)

        assert result == {
            "name": "Test Restaurant",
            "google_place_id": "place123",
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

    def test_extract_restaurant_data_object_missing_attrs(self) -> None:
        """Test extracting data from object with missing attributes."""
        mock_obj = Mock()
        mock_obj.name = "Test Restaurant"
        # Set other attributes to None to simulate missing attributes
        mock_obj.google_place_id = None
        mock_obj.address_line_1 = ""
        mock_obj.address = ""  # The address property should be empty when address_line_1 is empty
        mock_obj.city = ""
        mock_obj.state = ""
        mock_obj.postal_code = ""

        result = _extract_restaurant_data(mock_obj)

        assert result == {
            "name": "Test Restaurant",
            "google_place_id": None,
            "address": "",
            "city": "",
            "state": "",
            "postal_code": "",
        }

    def test_extract_restaurant_data_invalid_type(self) -> None:
        """Test extracting data from invalid type."""
        result = _extract_restaurant_data("invalid")
        # Invalid types return empty dictionary, not None
        assert result == {
            "name": "",
            "google_place_id": None,
            "address": "",
            "city": "",
            "state": "",
            "postal_code": "",
        }

    def test_extract_restaurant_data_none(self) -> None:
        """Test extracting data from None."""
        result = _extract_restaurant_data(None)
        # None returns empty dictionary, not None
        assert result == {
            "name": "",
            "google_place_id": None,
            "address": "",
            "city": "",
            "state": "",
            "postal_code": "",
        }


class TestBuildSearchQuery:
    """Test _build_search_query helper function."""

    def test_build_search_query_full_data(self) -> None:
        """Test building search query with full data."""
        data = {
            "name": "Test Restaurant",
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

        result = _build_search_query(data)

        assert result == "Test+Restaurant%2C+123+Main+St%2C+Test+City%2C+TS%2C+12345"

    def test_build_search_query_name_only(self) -> None:
        """Test building search query with name only."""
        data = {"name": "Test Restaurant", "address": "", "city": "", "state": "", "postal_code": ""}

        result = _build_search_query(data)

        assert result == "Test+Restaurant"

    def test_build_search_query_name_and_city(self) -> None:
        """Test building search query with name and city."""
        data = {"name": "Test Restaurant", "address": "", "city": "Test City", "state": "", "postal_code": ""}

        result = _build_search_query(data)

        assert result == "Test+Restaurant%2C+Test+City"

    def test_build_search_query_city_in_address(self) -> None:
        """Test building search query when city is already in address."""
        data = {
            "name": "Test Restaurant",
            "address": "123 Main St, Test City",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

        result = _build_search_query(data)

        # Should not duplicate city
        assert result is not None
        assert "Test+City" in result
        # Count occurrences of "Test City" - should be 1
        assert result.count("Test+City") == 1

    def test_build_search_query_empty_data(self) -> None:
        """Test building search query with empty data."""
        data = {"name": "", "address": "", "city": "", "state": "", "postal_code": ""}

        result = _build_search_query(data)

        assert result is None

    def test_build_search_query_no_name(self) -> None:
        """Test building search query without name."""
        data = {"name": "", "address": "123 Main St", "city": "Test City", "state": "TS", "postal_code": "12345"}

        result = _build_search_query(data)

        # When no name, it should still build query from other fields
        assert result == "123+Main+St%2C+Test+City%2C+TS%2C+12345"


class TestGoogleMapsUrl:
    """Test google_maps_url filter function."""

    def test_google_maps_url_none_input(self) -> None:
        """Test google_maps_url with None input."""
        result = google_maps_url(None)
        assert result is None

    def test_google_maps_url_with_method(self) -> None:
        """Test google_maps_url with object that has get_google_maps_url method."""
        mock_restaurant = Mock()
        mock_restaurant.get_google_maps_url.return_value = "https://maps.google.com/test"

        result = google_maps_url(mock_restaurant)

        assert result == "https://maps.google.com/test"
        mock_restaurant.get_google_maps_url.assert_called_once()

    def test_google_maps_url_with_place_id(self) -> None:
        """Test google_maps_url with place_id and name."""
        data = {"name": "Test Restaurant", "google_place_id": "place123", "address": "123 Main St", "city": "Test City"}

        result = google_maps_url(data)

        expected = "https://www.google.com/maps/search/?api=1&query=Test+Restaurant&query_place_id=place123"
        assert result == expected

    def test_google_maps_url_without_place_id(self) -> None:
        """Test google_maps_url without place_id."""
        data = {
            "name": "Test Restaurant",
            "google_place_id": None,
            "address": "123 Main St",
            "city": "Test City",
            "state": "TS",
            "postal_code": "12345",
        }

        result = google_maps_url(data)

        expected = (
            "https://www.google.com/maps/search/?api=1&query=Test+Restaurant%2C+123+Main+St%2C+Test+City%2C+TS%2C+12345"
        )
        assert result == expected

    def test_google_maps_url_name_only(self) -> None:
        """Test google_maps_url with name only."""
        data = {
            "name": "Test Restaurant",
            "google_place_id": None,
            "address": "",
            "city": "",
            "state": "",
            "postal_code": "",
        }

        result = google_maps_url(data)

        expected = "https://www.google.com/maps/search/?api=1&query=Test+Restaurant"
        assert result == expected

    def test_google_maps_url_invalid_data(self) -> None:
        """Test google_maps_url with invalid data."""
        result = google_maps_url("invalid")
        assert result is None

    def test_google_maps_url_empty_data(self) -> None:
        """Test google_maps_url with empty data."""
        data = {"name": "", "google_place_id": None, "address": "", "city": "", "state": "", "postal_code": ""}

        result = google_maps_url(data)

        assert result is None

    def test_google_maps_url_place_id_no_name(self) -> None:
        """Test google_maps_url with place_id but no name."""
        data = {"name": "", "google_place_id": "place123", "address": "123 Main St", "city": "Test City"}

        result = google_maps_url(data)

        # Should fall back to search-based URL
        expected = "https://www.google.com/maps/search/?api=1&query=123+Main+St%2C+Test+City"
        assert result == expected


class TestInitApp:
    """Test init_app function."""

    def test_init_app(self, app) -> None:
        """Test that filters are registered with Flask app."""
        # Initialize the filters
        init_app(app)

        # Check that filters are now registered
        assert "time_ago" in app.jinja_env.filters
        assert "google_maps_url" in app.jinja_env.filters

        # Check that the registered functions are correct
        assert app.jinja_env.filters["time_ago"] == time_ago
        assert app.jinja_env.filters["google_maps_url"] == google_maps_url


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_time_ago_future_datetime(self) -> None:
        """Test time_ago with future datetime."""
        now = datetime.now(UTC)
        future = now + timedelta(hours=1)
        result = time_ago(future)
        # Future datetime gets treated as past due to calculation
        assert "hours ago" in result

    def test_time_ago_very_old_datetime(self) -> None:
        """Test time_ago with very old datetime."""
        now = datetime.now(UTC)
        very_old = now - timedelta(days=1000)  # ~3 years
        result = time_ago(very_old)
        assert "years ago" in result

    def test_build_search_query_special_characters(self) -> None:
        """Test building search query with special characters."""
        data = {
            "name": "Café & Restaurant",
            "address": "123 Main St, Apt #4",
            "city": "São Paulo",
            "state": "SP",
            "postal_code": "01234-567",
        }

        result = _build_search_query(data)

        # Should be URL encoded
        assert "%" in result
        assert "Caf%C3%A9" in result  # URL encoded café
        assert "S%C3%A3o" in result  # URL encoded são

    def test_google_maps_url_unicode_characters(self) -> None:
        """Test google_maps_url with unicode characters."""
        data = {
            "name": "Café José",
            "google_place_id": "place123",
            "address": "Rua das Flores, 123",
            "city": "São Paulo",
        }

        result = google_maps_url(data)

        # Should be URL encoded
        assert result is not None
        assert "%" in result
        assert "Caf%C3%A9" in result
        assert "Jos%C3%A9" in result
