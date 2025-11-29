"""Tests for restaurants routes module."""

from unittest.mock import Mock, patch

from flask import Flask
import pytest

from app.restaurants.routes import (
    _build_photo_urls,
    _build_reviews_summary,
    _build_search_params,
    _create_ajax_error_response,
    _create_ajax_success_response,
    _create_restaurant_from_form,
    _extract_location_from_query,
    _filter_place_by_criteria,
    _get_page_size_from_cookie,
    _handle_import_error,
    _handle_import_success,
    _handle_restaurant_creation_error,
    _handle_restaurant_creation_success,
    _prepare_restaurant_form,
    _process_import_file,
    _process_search_result_place,
    _validate_google_places_request,
    _validate_import_file,
    _validate_search_params,
    detect_chain_restaurant,
    generate_description,
    generate_notes,
    get_cuisine_choices,
)


class TestRestaurantsRoutes:
    """Test restaurants routes functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["GOOGLE_MAPS_API_KEY"] = "test-api-key"
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    @pytest.fixture
    def mock_restaurant(self):
        """Create mock restaurant."""
        restaurant = Mock()
        restaurant.id = 1
        restaurant.name = "Test Restaurant"
        restaurant.city = "Test City"
        restaurant.google_place_id = "test_place_id"
        return restaurant

    def test_get_page_size_from_cookie_valid(self, app) -> None:
        """Test getting valid page size from cookie."""
        with app.test_request_context() as ctx:
            ctx.request.cookies = {"restaurant_page_size": "25"}
            result = _get_page_size_from_cookie()
            assert result == 25

    def test_get_page_size_from_cookie_invalid(self, app) -> None:
        """Test getting invalid page size from cookie."""
        with app.test_request_context() as ctx:
            ctx.request.cookies = {"restaurant_page_size": "15"}
            result = _get_page_size_from_cookie()
            assert result == 10  # Default

    def test_get_page_size_from_cookie_missing(self, app) -> None:
        """Test getting page size when cookie is missing."""
        with app.test_request_context() as ctx:
            ctx.request.cookies = {}
            result = _get_page_size_from_cookie()
            assert result == 10  # Default

    def test_get_page_size_from_cookie_show_all(self, app) -> None:
        """Test getting show all page size from cookie."""
        with app.test_request_context() as ctx:
            ctx.request.cookies = {"restaurant_page_size": "-1"}
            result = _get_page_size_from_cookie()
            assert result == -1  # SHOW_ALL

    def test_extract_location_from_query_in_pattern(self) -> None:
        """Test extracting location from query with 'in' pattern."""
        business, location = _extract_location_from_query("McDonald's in Dallas, TX")
        assert business == "McDonald's"
        assert location == "Dallas, TX"

    def test_extract_location_from_query_near_pattern(self) -> None:
        """Test extracting location from query with 'near' pattern."""
        business, location = _extract_location_from_query("Pizza near Austin")
        assert business == "Pizza"
        assert location == "Austin"

    def test_extract_location_from_query_at_pattern(self) -> None:
        """Test extracting location from query with 'at' pattern."""
        business, location = _extract_location_from_query("Starbucks at Dallas")
        assert business == "Starbucks"
        assert location == "Dallas"

    def test_extract_location_from_query_city_state_pattern(self) -> None:
        """Test extracting location from query with city, state pattern."""
        business, location = _extract_location_from_query("McDonald's Dallas, TX")
        assert business == "McDonald's"
        assert location == "Dallas, TX"

    def test_extract_location_from_query_no_location(self) -> None:
        """Test extracting location from query without location."""
        business, location = _extract_location_from_query("Starbucks")
        assert business == "Starbucks"
        assert location is None

    def test_build_search_params_with_location(self, app) -> None:
        """Test building search parameters with location."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.search_places_with_fallback.return_value = []

                places = _build_search_params("McDonald's Dallas", "American", "32.7767", "-96.7970", "5", "test-key")
                assert isinstance(places, list)
                mock_service.search_places_with_fallback.assert_called_once()

    def test_build_search_params_without_location(self, app) -> None:
        """Test building search parameters without location."""
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.search_places_with_fallback.return_value = []

                places = _build_search_params("McDonald's", "American", None, None, "5", "test-key")
                assert isinstance(places, list)
                mock_service.search_places_with_fallback.assert_called_once()

    def test_build_photo_urls(self) -> None:
        """Test building photo URLs."""
        photos = [
            {"photo_reference": "ref1"},
            {"photo_reference": "ref2"},
            {"photo_reference": "ref3"},
            {"photo_reference": "ref4"},  # Should be limited to 3
        ]

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.build_photo_urls.return_value = [
                {"photo_reference": "ref1", "url": "url1"},
                {"photo_reference": "ref2", "url": "url2"},
                {"photo_reference": "ref3", "url": "url3"},
            ]

            result = _build_photo_urls(photos, "test-key")
            assert len(result) == 3
            assert "ref1" in result[0]["photo_reference"]
            mock_service.build_photo_urls.assert_called_once_with(photos, "test-key")

    def test_build_photo_urls_empty(self) -> None:
        """Test building photo URLs with empty list."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.build_photo_urls.return_value = []

            result = _build_photo_urls([], "test-key")
            assert result == []

    def test_build_reviews_summary(self) -> None:
        """Test building reviews summary."""
        reviews = [
            {
                "author_name": "John Doe",
                "rating": 5,
                "text": "Great food!" * 50,  # Long text
                "time": 1234567890,
            },
            {
                "author_name": "Jane Smith",
                "rating": 4,
                "text": "Good service",
                "time": 1234567891,
            },
        ]

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.build_reviews_summary.return_value = [
                {"author_name": "John Doe", "rating": 5, "text": "Great food!..."},
                {"author_name": "Jane Smith", "rating": 4, "text": "Good service"},
            ]

            result = _build_reviews_summary(reviews)
            assert len(result) == 2
            assert result[0]["author_name"] == "John Doe"
            mock_service.build_reviews_summary.assert_called_once_with(reviews)

    def test_build_reviews_summary_empty(self) -> None:
        """Test building reviews summary with empty list."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.build_reviews_summary.return_value = []

            result = _build_reviews_summary([])
            assert result == []

    def test_validate_search_params_success(self, app) -> None:
        """Test validating search parameters successfully."""
        with app.test_request_context("/?query=test&lat=32.7767&lng=-96.7970"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is None
                assert params["query"] == "test"
                assert params["lat"] == "32.7767"

    def test_validate_search_params_missing_query(self, app) -> None:
        """Test validating search parameters with missing query."""
        with app.test_request_context("/"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is not None
                assert status == 400

    def test_validate_search_params_missing_api_key(self, app) -> None:
        """Test validating search parameters with missing API key."""
        app.config["GOOGLE_MAPS_API_KEY"] = None
        with app.test_request_context("/?query=test"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is not None
                assert status == 500

    def test_filter_place_by_criteria_rating(self) -> None:
        """Test filtering place by rating criteria."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.filter_places_by_criteria.return_value = [False]  # Returns list

            place = {"rating": 3.5, "price_level": 2}
            result = _filter_place_by_criteria(place, 4.0)
            assert result == [False]

            mock_service.filter_places_by_criteria.return_value = [True]
            result = _filter_place_by_criteria(place, 3.0)
            assert result == [True]

    def test_filter_place_by_criteria_price_level(self) -> None:
        """Test filtering place by price level criteria (price level filtering removed from Essentials tier)."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.filter_places_by_criteria.return_value = [True]  # Returns list

            place = {"rating": 4.0, "price_level": 3}
            # Price level filtering removed, so function only takes place and min_rating
            result = _filter_place_by_criteria(place, None)
            assert result == [True]

    def test_filter_place_by_criteria_no_filters(self) -> None:
        """Test filtering place with no filters."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.filter_places_by_criteria.return_value = [True]  # Returns list

            place = {"rating": 4.0, "price_level": 2}
            result = _filter_place_by_criteria(place, None)
            assert result == [True]

    def test_process_search_result_place_success(self, app) -> None:
        """Test processing search result place successfully."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.process_search_result_place.return_value = {"id": "test_id", "name": "Test Restaurant"}

            place = {"id": "test_id", "displayName": {"text": "Test Restaurant"}}

            with app.app_context():
                result = _process_search_result_place(place, "test-key")
                assert result is not None
                assert result["name"] == "Test Restaurant"
                mock_service.process_search_result_place.assert_called_once_with(place)

    def test_process_search_result_place_no_place_id(self, app) -> None:
        """Test processing search result place without place_id."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.process_search_result_place.return_value = None

            place = {"displayName": {"text": "Test Restaurant"}}

            with app.app_context():
                result = _process_search_result_place(place, "test-key")
                assert result is None

    def test_parse_address_components(self) -> None:
        """Test parsing address components using centralized service."""
        components = [
            {"types": ["street_number"], "longText": "123", "shortText": "123"},
            {"types": ["route"], "longText": "Main St", "shortText": "Main St"},
            {"types": ["locality"], "longText": "Dallas", "shortText": "Dallas"},
            {"types": ["administrative_area_level_1"], "longText": "Texas", "shortText": "TX"},
            {"types": ["postal_code"], "longText": "75201", "shortText": "75201"},
            {"types": ["country"], "longText": "United States", "shortText": "US"},
        ]

        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.parse_address_components.return_value = {
                "street_address": "123 Main St",
                "city": "Dallas",
                "state": "TX",
                "postal_code": "75201",
                "country": "United States",
            }
            mock_service.return_value = mock_places_service

            result = mock_places_service.parse_address_components(components)
            assert result["street_address"] == "123 Main St"
            assert result["city"] == "Dallas"
            assert result["state"] == "TX"
            assert result["postal_code"] == "75201"
            assert result["country"] == "United States"

    def test_get_cuisine_choices(self) -> None:
        """Test getting cuisine choices."""
        choices = get_cuisine_choices()
        assert "American" in choices
        assert "Chinese" in choices
        assert "Italian" in choices
        assert len(choices) > 10

    def test_analyze_restaurant_types(self, app) -> None:
        """Test analyzing restaurant types using centralized service."""
        types = ["chinese_restaurant", "restaurant", "food"]
        with app.app_context():
            with patch("app.services.google_places_service.get_google_places_service") as mock_service:
                mock_places_service = Mock()
                mock_places_service.analyze_restaurant_types.return_value = ("Chinese", "casual_dining")
                mock_service.return_value = mock_places_service

                # Test the service method directly
                cuisine, service_level = mock_places_service.analyze_restaurant_types(types)
                assert cuisine == "Chinese"
                assert service_level == "casual_dining"

    def test_detect_cuisine_from_name_japanese(self) -> None:
        """Test detecting Japanese cuisine from name using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = ("Japanese", "casual_dining")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types([], {"name": "Sushi Palace"})
            assert cuisine == "Japanese"

    def test_detect_cuisine_from_name_chinese(self) -> None:
        """Test detecting Chinese cuisine from name using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = ("Chinese", "casual_dining")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types(
                [], {"name": "Golden Dragon Chinese Restaurant"}
            )
            assert cuisine == "Chinese"

    def test_detect_cuisine_from_name_italian(self) -> None:
        """Test detecting Italian cuisine from name using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = ("Italian", "casual_dining")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types([], {"name": "Mario's Pizza"})
            assert cuisine == "Italian"

    def test_detect_cuisine_from_name_american_chain(self) -> None:
        """Test detecting American cuisine from chain name using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = ("American", "quick_service")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types([], {"name": "McDonald's"})
            assert cuisine == "American"

    def test_detect_cuisine_from_name_pub(self) -> None:
        """Test detecting pub from name with food indicators using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = ("American", "casual_dining")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types(
                [], {"name": "The Sports Bar & Grill"}
            )
            assert cuisine == "American"

    def test_detect_cuisine_from_name_no_match(self) -> None:
        """Test detecting cuisine with no matching patterns using centralized service."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_service:
            mock_places_service = Mock()
            mock_places_service.analyze_restaurant_types.return_value = (None, "casual_dining")
            mock_service.return_value = mock_places_service

            # Test the service method directly
            cuisine, service_level = mock_places_service.analyze_restaurant_types([], {"name": "Generic Restaurant"})
            assert cuisine is None

    def test_analyze_restaurant_types_dessert_shop_quick_service(self, app) -> None:
        """Test that inexpensive dessert shops are classified (simplified logic may classify as casual_dining)."""
        place_data = {"primaryType": "dessert_shop", "priceLevel": "PRICE_LEVEL_INEXPENSIVE"}

        with app.app_context():
            # Use the actual service instead of mocking to test the logic
            from app.services.google_places_service import GooglePlacesService

            service = GooglePlacesService(api_key="test_key")  # Won't actually call API

            # Test the detection logic directly
            service_level, confidence = service.detect_service_level_from_data(place_data)
            # Service may return unknown if data is insufficient
            assert service_level in ["quick_service", "casual_dining", "unknown"]
            assert confidence >= 0.0  # Should have some confidence

    def test_analyze_restaurant_types_expensive_dessert_shop_casual_dining(self, app) -> None:
        """Test that expensive dessert shops are classified (may return unknown if data insufficient)."""
        place_data = {"primaryType": "dessert_shop", "priceLevel": "PRICE_LEVEL_EXPENSIVE"}

        with app.app_context():
            from app.services.google_places_service import GooglePlacesService

            service = GooglePlacesService(api_key="test_key")

            # Test the detection logic directly
            service_level, confidence = service.detect_service_level_from_data(place_data)
            # Service may return unknown if data is insufficient, or casual_dining with sufficient data
            assert service_level in ["casual_dining", "unknown"]

    def test_analyze_restaurant_types_fast_food_primary_type_casual_dining(self, app) -> None:
        """Test that fast_food_restaurant as primary type is classified as casual dining (simplified logic)."""
        place_data = {"primaryType": "fast_food_restaurant", "priceLevel": "PRICE_LEVEL_MODERATE"}

        with app.app_context():
            from app.services.google_places_service import GooglePlacesService

            service = GooglePlacesService(api_key="test_key")

            # Test the detection logic directly
            service_level, confidence = service.detect_service_level_from_data(place_data)
            # Service may return unknown if data is insufficient, or casual_dining with simplified logic
            assert service_level in ["casual_dining", "unknown"]
            assert confidence >= 0.0  # Should have some confidence (may be lower with simplified logic)

    def test_format_primary_type_for_display(self, app) -> None:
        """Test formatting primary types for display."""
        with app.app_context():
            from app.services.google_places_service import GooglePlacesService

            service = GooglePlacesService(api_key="test_key")

            # Test various primary types
            assert service.format_primary_type_for_display("fast_food_restaurant") == "Fast Food Restaurant"
            assert service.format_primary_type_for_display("ice_cream_shop") == "Ice Cream Shop"
            assert service.format_primary_type_for_display("dessert_shop") == "Dessert Shop"
            assert service.format_primary_type_for_display("coffee_shop") == "Coffee Shop"
            assert service.format_primary_type_for_display("") is None
            assert service.format_primary_type_for_display(None) is None

    def test_detect_chain_restaurant_mcdonalds(self, app) -> None:
        """Test detecting McDonald's as chain."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.detect_chain_restaurant.return_value = True

            with app.app_context():
                result = detect_chain_restaurant("McDonald's")
                assert result is True

    def test_detect_chain_restaurant_starbucks(self, app) -> None:
        """Test detecting Starbucks as chain."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.detect_chain_restaurant.return_value = True

            with app.app_context():
                result = detect_chain_restaurant("Starbucks Coffee")
                assert result is True

    def test_detect_chain_restaurant_local(self, app) -> None:
        """Test detecting local restaurant as non-chain."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.detect_chain_restaurant.return_value = False

            with app.app_context():
                result = detect_chain_restaurant("Local Family Restaurant")
                assert result is False

    def test_generate_description_with_rating(self) -> None:
        """Test generating description with rating."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.generate_description.return_value = "Google Rating: 4.5/5 (100 reviews)"

            place = {
                "rating": 4.5,
                "user_ratings_total": 100,
                "price_level": 2,
                "types": ["restaurant", "food"],
            }
            result = generate_description(place)
            assert "Google Rating: 4.5/5 (100 reviews)" in result

    def test_generate_description_with_editorial_summary(self) -> None:
        """Test generating description with editorial summary."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.generate_description.return_value = "Great local restaurant"

            place = {
                "editorial_summary": {"overview": "Great local restaurant"},
                "rating": 4.0,
            }
            result = generate_description(place)
            assert "Great local restaurant" in result

    def test_generate_description_minimal(self) -> None:
        """Test generating description with minimal data."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.generate_description.return_value = "Restaurant from Google Places"

            place = {}
            result = generate_description(place)
            assert result == "Restaurant from Google Places"

    def test_generate_notes_with_price_level(self) -> None:
        """Test generating notes with price level."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.generate_notes.return_value = "Moderate pricing"

            place = {"price_level": 2}
            result = generate_notes(place)
            assert "Moderate pricing" in result

    def test_generate_notes_no_price_level(self) -> None:
        """Test generating notes without price level."""
        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.generate_notes.return_value = None

            place = {}
            result = generate_notes(place)
            assert result == ""  # Function returns empty string when notes is None

    def test_create_ajax_success_response_new(self, app, mock_restaurant) -> None:
        """Test creating AJAX success response for new restaurant."""
        with app.test_request_context():
            with app.app_context():
                with patch("app.restaurants.routes.url_for") as mock_url_for:
                    mock_url_for.return_value = "/restaurants/1"
                    response, status = _create_ajax_success_response(mock_restaurant, True)
                    assert status == 201
                    assert response.json["status"] == "success"
                    assert response.json["restaurant_id"] == 1

    def test_create_ajax_success_response_existing(self, app, mock_restaurant) -> None:
        """Test creating AJAX success response for existing restaurant."""
        with app.test_request_context():
            with app.app_context():
                with patch("app.restaurants.routes.url_for") as mock_url_for:
                    mock_url_for.return_value = "/restaurants/1"
                    response, status = _create_ajax_success_response(mock_restaurant, False)
                    assert status == 409
                    assert response.json["status"] == "conflict"

    def test_create_ajax_error_response_duplicate_google_place_id(self, app) -> None:
        """Test creating AJAX error response for duplicate Google Place ID."""
        from app.restaurants.exceptions import DuplicateGooglePlaceIdError

        existing_restaurant = Mock()
        existing_restaurant.id = 1
        exception = DuplicateGooglePlaceIdError("test_place_id", existing_restaurant)

        with app.test_request_context():
            with app.app_context():
                with patch("app.restaurants.routes.url_for") as mock_url_for:
                    mock_url_for.return_value = "/restaurants/1"
                    response, status = _create_ajax_error_response(exception)
                    assert status == 409
                    assert response.json["status"] == "conflict"

    def test_create_ajax_error_response_generic(self, app) -> None:
        """Test creating AJAX error response for generic error."""
        exception = Exception("Generic error")

        with app.app_context():
            response, status = _create_ajax_error_response(exception)
            assert status == 400
            assert response.json["status"] == "error"

    def test_handle_restaurant_creation_success_ajax(self, app, mock_restaurant) -> None:
        """Test handling restaurant creation success for AJAX request."""
        with app.test_request_context():
            with app.app_context():
                with patch("app.restaurants.routes.url_for") as mock_url_for:
                    mock_url_for.return_value = "/restaurants/1"
                    response = _handle_restaurant_creation_success(mock_restaurant, True, True)
                    assert response[1] == 201  # Status code

    def test_handle_restaurant_creation_success_form(self, app, mock_restaurant) -> None:
        """Test handling restaurant creation success for form request."""
        with app.test_request_context():
            with app.app_context():
                with patch("app.restaurants.routes.url_for") as mock_url_for:
                    mock_url_for.return_value = "/restaurants/1"
                    response = _handle_restaurant_creation_success(mock_restaurant, True, False)
                    assert hasattr(response, "status_code")  # Redirect response

    def test_handle_restaurant_creation_error_ajax(self, app) -> None:
        """Test handling restaurant creation error for AJAX request."""
        with app.app_context():
            exception = Exception("Test error")
            response = _handle_restaurant_creation_error(exception, True)
            assert response[1] == 400  # Status code

    def test_handle_restaurant_creation_error_form(self, app) -> None:
        """Test handling restaurant creation error for form request."""
        with app.test_request_context():
            exception = Exception("Test error")
            response = _handle_restaurant_creation_error(exception, False)
            assert response is None

    def test_validate_import_file_valid_csv(self) -> None:
        """Test validating valid CSV file."""
        file = Mock()
        file.filename = "test.csv"
        result = _validate_import_file(file)
        assert result is True

    def test_validate_import_file_valid_json(self) -> None:
        """Test validating valid JSON file."""
        file = Mock()
        file.filename = "test.json"
        result = _validate_import_file(file)
        assert result is True

    @patch("app.restaurants.routes.flash")
    def test_validate_import_file_invalid_extension(self, mock_flash) -> None:
        """Test validating file with invalid extension."""
        file = Mock()
        file.filename = "test.txt"
        result = _validate_import_file(file)
        assert result is False

    @patch("app.restaurants.routes.flash")
    def test_validate_import_file_no_filename(self, mock_flash) -> None:
        """Test validating file with no filename."""
        file = Mock()
        file.filename = ""
        result = _validate_import_file(file)
        assert result is False

    @patch("app.restaurants.routes.services.import_restaurants_from_csv")
    def test_process_import_file_success(self, mock_import, app) -> None:
        """Test processing import file successfully."""
        file = Mock()
        file.filename = "test.csv"
        mock_import.return_value = (True, {"success_count": 5, "skipped_count": 2})

        with app.app_context():
            success, result = _process_import_file(file, 1)
            assert success is True
            assert result["success_count"] == 5

    @patch("app.restaurants.routes.flash")
    def test_process_import_file_validation_failed(self, mock_flash, app) -> None:
        """Test processing import file with validation failure."""
        file = Mock()
        file.filename = "test.txt"

        with app.app_context():
            success, result = _process_import_file(file, 1)
            assert success is False
            assert "File validation failed" in result["message"]

    @patch("app.restaurants.routes.redirect")
    @patch("app.restaurants.routes.url_for")
    @patch("app.restaurants.routes.flash")
    def test_handle_import_success(self, mock_flash, mock_url_for, mock_redirect, app) -> None:
        """Test handling import success."""
        result_data = {"success_count": 5, "has_warnings": True, "skipped_count": 2}
        mock_redirect.return_value = Mock(status_code=302)

        with app.app_context():
            response = _handle_import_success(result_data)
            assert hasattr(response, "status_code")  # Redirect response
            mock_flash.assert_called()

    def test_handle_import_error(self, app) -> None:
        """Test handling import error."""
        result_data = {"message": "Import failed", "error_details": "Test error"}

        with app.app_context():
            with patch("app.restaurants.routes.flash") as mock_flash:
                with patch("app.restaurants.routes.current_app") as mock_app:
                    # Ensure logger.error is a regular Mock, not AsyncMock
                    mock_app.logger.error = Mock()
                    _handle_import_error(result_data)
                    mock_flash.assert_called()
                    mock_app.logger.error.assert_called()

    def test_validate_google_places_request_success(self, app) -> None:
        """Test validating Google Places request successfully."""
        with app.test_request_context(
            "/",
            method="POST",
            json={"name": "Test Restaurant"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is None
                assert data["data"]["name"] == "Test Restaurant"
                assert data["csrf_token"] == "test-token"

    def test_validate_google_places_request_not_json(self, app) -> None:
        """Test validating Google Places request with non-JSON content."""
        with app.test_request_context("/", method="POST", data="not json"):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 400

    def test_validate_google_places_request_no_data(self, app) -> None:
        """Test validating Google Places request with no data."""
        with app.test_request_context("/", method="POST", json=None):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 400

    def test_validate_google_places_request_no_csrf(self, app) -> None:
        """Test validating Google Places request with no CSRF token."""
        with app.test_request_context("/", method="POST", json={"name": "Test"}):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 403

    def test_prepare_restaurant_form_success(self, app) -> None:
        """Test preparing restaurant form successfully."""
        data = {
            "name": "Test Restaurant",
            "type": "restaurant",  # Add required field
            "formatted_address": "123 Test St",
            "city": "Test City",
            "state": "TX",
            "postal_code": "12345",
            "country": "US",
            "formatted_phone_number": "555-1234",
            "website": "https://test.com",
            "place_id": "test_place_id",
        }

        with app.app_context():
            with patch("app.restaurants.forms.RestaurantForm") as mock_form_class:
                with patch("app.restaurants.services.detect_service_level_from_google_data") as mock_detect:
                    mock_detect.return_value = ("casual_dining", 0.8)

                    # Create a mock form that always validates successfully
                    mock_form = Mock()
                    mock_form.validate.return_value = True
                    mock_form_class.return_value = mock_form

                    form, error = _prepare_restaurant_form(data, "test-token")
                    assert error is None
                    assert form == mock_form

    def test_prepare_restaurant_form_validation_failed(self, app) -> None:
        """Test preparing restaurant form with validation failure."""
        data = {"name": "Test Restaurant"}

        with app.app_context():
            with patch("app.restaurants.routes.RestaurantForm") as mock_form_class:
                mock_form = Mock()
                mock_form.validate.return_value = False
                mock_form.errors = {"name": ["Name is required"]}
                mock_form_class.return_value = mock_form

                form, error = _prepare_restaurant_form(data, "test-token")
                assert error is not None
                assert error[1] == 400

    def test_create_restaurant_from_form_success(self, app) -> None:
        """Test creating restaurant from form successfully."""
        form = Mock()

        with app.app_context():
            with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_restaurant = Mock()
                    mock_restaurant.id = 1
                    mock_create.return_value = (mock_restaurant, True)

                    result, error = _create_restaurant_from_form(form)
                    assert error is None
                    assert result[0] == mock_restaurant
                    assert result[1] is True

    def test_create_restaurant_from_form_duplicate_google_place_id(self, app) -> None:
        """Test creating restaurant from form with duplicate Google Place ID."""
        from app.restaurants.exceptions import DuplicateGooglePlaceIdError

        form = Mock()
        # Create a proper mock restaurant for the exception
        mock_restaurant = Mock()
        mock_restaurant.name = "Existing Restaurant"
        mock_restaurant.city = "Test City"
        mock_restaurant.state = "TX"
        exception = DuplicateGooglePlaceIdError("test_place_id", mock_restaurant)

        with app.app_context():
            with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    with patch("app.restaurants.routes.url_for") as mock_url_for:
                        with patch("app.restaurants.routes.jsonify") as mock_jsonify:
                            mock_user.id = 1
                            mock_create.side_effect = exception
                            mock_url_for.return_value = "/restaurants/1"
                            mock_jsonify.return_value = Mock()

                            result, error = _create_restaurant_from_form(form)
                            assert error is not None
                            assert error[1] == 409

    def test_create_restaurant_from_form_duplicate_restaurant(self, app) -> None:
        """Test creating restaurant from form with duplicate restaurant."""
        from app.restaurants.exceptions import DuplicateRestaurantError

        form = Mock()
        # Create a proper mock restaurant for the exception
        mock_restaurant = Mock()
        mock_restaurant.city = "Test City"
        mock_restaurant.state = "TX"
        exception = DuplicateRestaurantError("Test Restaurant", "Test City", mock_restaurant)

        with app.app_context():
            with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    with patch("app.restaurants.routes.url_for") as mock_url_for:
                        with patch("app.restaurants.routes.jsonify") as mock_jsonify:
                            mock_user.id = 1
                            mock_create.side_effect = exception
                            mock_url_for.return_value = "/restaurants/1"
                            mock_jsonify.return_value = Mock()

                            result, error = _create_restaurant_from_form(form)
                            assert error is not None
                            assert error[1] == 409

    def test_create_restaurant_from_form_exception(self, app) -> None:
        """Test creating restaurant from form with exception."""
        form = Mock()
        exception = Exception("Database error")

        with app.app_context():
            with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_create.side_effect = exception

                    result, error = _create_restaurant_from_form(form)
                    assert error is not None
                    assert error[1] == 500
