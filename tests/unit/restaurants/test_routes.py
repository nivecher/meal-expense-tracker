"""Tests for restaurants routes module."""

import json
from unittest.mock import Mock, patch, MagicMock

import pytest
from flask import Flask, url_for
from werkzeug.datastructures import FileStorage

from app.restaurants.routes import (
    _get_page_size_from_cookie,
    _extract_location_from_query,
    _get_regional_bias_from_request,
    _build_search_params,
    _build_photo_urls,
    _build_reviews_summary,
    _get_place_details,
    _process_place_data,
    _validate_search_params,
    _filter_place_by_criteria,
    _process_search_result_place,
    parse_address_components,
    get_cuisine_choices,
    _get_specific_cuisine_types,
    _detect_cuisine_from_types,
    _detect_service_level_from_types,
    analyze_restaurant_types,
    _matches_cuisine_pattern,
    detect_cuisine_from_name,
    detect_chain_restaurant,
    generate_description,
    generate_notes,
    _create_ajax_success_response,
    _create_ajax_error_response,
    _handle_restaurant_creation_success,
    _handle_restaurant_creation_error,
    _process_restaurant_form_submission,
    _validate_import_file,
    _parse_import_file,
    _process_import_file,
    _handle_import_success,
    _handle_import_error,
    _validate_google_places_request,
    _prepare_restaurant_form,
    _create_restaurant_from_form,
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

    def test_get_page_size_from_cookie_valid(self, app):
        """Test getting valid page size from cookie."""
        with app.test_request_context(cookies={"restaurant_page_size": "25"}):
            result = _get_page_size_from_cookie()
            assert result == 25

    def test_get_page_size_from_cookie_invalid(self, app):
        """Test getting invalid page size from cookie."""
        with app.test_request_context(cookies={"restaurant_page_size": "15"}):
            result = _get_page_size_from_cookie()
            assert result == 10  # Default

    def test_get_page_size_from_cookie_missing(self, app):
        """Test getting page size when cookie is missing."""
        with app.test_request_context():
            result = _get_page_size_from_cookie()
            assert result == 10  # Default

    def test_get_page_size_from_cookie_show_all(self, app):
        """Test getting show all page size from cookie."""
        with app.test_request_context(cookies={"restaurant_page_size": "-1"}):
            result = _get_page_size_from_cookie()
            assert result == -1  # SHOW_ALL

    def test_extract_location_from_query_in_pattern(self):
        """Test extracting location from query with 'in' pattern."""
        business, location = _extract_location_from_query("McDonald's in Dallas, TX")
        assert business == "McDonald's"
        assert location == "Dallas, TX"

    def test_extract_location_from_query_near_pattern(self):
        """Test extracting location from query with 'near' pattern."""
        business, location = _extract_location_from_query("Pizza near Austin")
        assert business == "Pizza"
        assert location == "Austin"

    def test_extract_location_from_query_at_pattern(self):
        """Test extracting location from query with 'at' pattern."""
        business, location = _extract_location_from_query("Starbucks at Dallas")
        assert business == "Starbucks"
        assert location == "Dallas"

    def test_extract_location_from_query_city_state_pattern(self):
        """Test extracting location from query with city, state pattern."""
        business, location = _extract_location_from_query("McDonald's Dallas, TX")
        assert business == "McDonald's"
        assert location == "Dallas, TX"

    def test_extract_location_from_query_no_location(self):
        """Test extracting location from query without location."""
        business, location = _extract_location_from_query("Starbucks")
        assert business == "Starbucks"
        assert location is None

    def test_get_regional_bias_from_request(self):
        """Test getting regional bias from request."""
        result = _get_regional_bias_from_request()
        assert result == "us"

    def test_build_search_params_with_location(self, app):
        """Test building search parameters with location."""
        with app.app_context():
            url, params = _build_search_params(
                "McDonald's Dallas", "American", "32.7767", "-96.7970", "5", "test-key"
            )
            assert "nearbysearch" in url
            assert "location" in params
            assert "32.7767,-96.7970" in params["location"]

    def test_build_search_params_without_location(self, app):
        """Test building search parameters without location."""
        with app.app_context():
            url, params = _build_search_params("McDonald's", "American", None, None, "5", "test-key")
            assert "textsearch" in url
            assert "query" in params
            assert "McDonald's" in params["query"]

    def test_build_photo_urls(self):
        """Test building photo URLs."""
        photos = [
            {"photo_reference": "ref1"},
            {"photo_reference": "ref2"},
            {"photo_reference": "ref3"},
            {"photo_reference": "ref4"},  # Should be limited to 3
        ]
        result = _build_photo_urls(photos, "test-key")
        assert len(result) == 3
        assert "ref1" in result[0]["photo_reference"]
        assert "test-key" in result[0]["url"]

    def test_build_photo_urls_empty(self):
        """Test building photo URLs with empty list."""
        result = _build_photo_urls([], "test-key")
        assert result == []

    def test_build_reviews_summary(self):
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
        result = _build_reviews_summary(reviews)
        assert len(result) == 2
        assert result[0]["author_name"] == "John Doe"
        assert len(result[0]["text"]) <= 203  # 200 + "..."
        assert "..." in result[0]["text"]

    def test_build_reviews_summary_empty(self):
        """Test building reviews summary with empty list."""
        result = _build_reviews_summary([])
        assert result == []

    @patch("app.restaurants.routes.requests.get")
    def test_get_place_details_success(self, mock_get, app):
        """Test getting place details successfully."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "OK",
            "result": {
                "place_id": "test_id",
                "name": "Test Restaurant",
                "formatted_address": "123 Test St",
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with app.app_context():
            result = _get_place_details("test_id", "test-key")
            assert result is not None
            assert result["place_id"] == "test_id"
            assert result["name"] == "Test Restaurant"

    @patch("app.restaurants.routes.requests.get")
    def test_get_place_details_failure(self, mock_get, app):
        """Test getting place details with API failure."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "INVALID_REQUEST"}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with app.app_context():
            result = _get_place_details("test_id", "test-key")
            assert result is None

    @patch("app.restaurants.routes.requests.get")
    def test_get_place_details_exception(self, mock_get, app):
        """Test getting place details with exception."""
        mock_get.side_effect = Exception("Network error")

        with app.app_context():
            result = _get_place_details("test_id", "test-key")
            assert result is None

    def test_process_place_data(self, app):
        """Test processing place data."""
        place = {
            "place_id": "test_id",
            "name": "Test Restaurant",
            "formatted_address": "123 Test St",
            "address_components": [
                {"types": ["street_number"], "long_name": "123"},
                {"types": ["route"], "long_name": "Test St"},
                {"types": ["locality"], "long_name": "Test City"},
                {"types": ["administrative_area_level_1"], "long_name": "TX"},
                {"types": ["postal_code"], "long_name": "12345"},
                {"types": ["country"], "long_name": "US"},
            ],
            "rating": 4.5,
            "user_ratings_total": 100,
            "price_level": 2,
            "types": ["restaurant", "food"],
            "photos": [{"photo_reference": "ref1"}],
            "reviews": [{"author_name": "John", "rating": 5, "text": "Great!"}],
        }

        with app.app_context():
            with patch("app.restaurants.routes.parse_address_components") as mock_parse:
                mock_parse.return_value = {
                    "street_address": "123 Test St",
                    "city": "Test City",
                    "state": "TX",
                    "postal_code": "12345",
                    "country": "US",
                }
                result = _process_place_data(place, "test-key")
                assert result["place_id"] == "test_id"
                assert result["name"] == "Test Restaurant"
                assert result["address"] == "123 Test St"
                assert result["city"] == "Test City"

    def test_validate_search_params_success(self, app):
        """Test validating search parameters successfully."""
        with app.test_request_context("/?query=test&lat=32.7767&lng=-96.7970"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is None
                assert params["query"] == "test"
                assert params["lat"] == "32.7767"

    def test_validate_search_params_missing_query(self, app):
        """Test validating search parameters with missing query."""
        with app.test_request_context("/"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is not None
                assert status == 400

    def test_validate_search_params_missing_api_key(self, app):
        """Test validating search parameters with missing API key."""
        app.config["GOOGLE_MAPS_API_KEY"] = None
        with app.test_request_context("/?query=test"):
            with app.app_context():
                params, error, status = _validate_search_params()
                assert error is not None
                assert status == 500

    def test_filter_place_by_criteria_rating(self):
        """Test filtering place by rating criteria."""
        place = {"rating": 3.5, "price_level": 2}
        result = _filter_place_by_criteria(place, "4.0", None)
        assert result is False

        result = _filter_place_by_criteria(place, "3.0", None)
        assert result is True

    def test_filter_place_by_criteria_price_level(self):
        """Test filtering place by price level criteria."""
        place = {"rating": 4.0, "price_level": 3}
        result = _filter_place_by_criteria(place, None, "2")
        assert result is False

        result = _filter_place_by_criteria(place, None, "4")
        assert result is True

    def test_filter_place_by_criteria_no_filters(self):
        """Test filtering place with no filters."""
        place = {"rating": 4.0, "price_level": 2}
        result = _filter_place_by_criteria(place, None, None)
        assert result is True

    @patch("app.restaurants.routes._get_place_details")
    def test_process_search_result_place_success(self, mock_get_details, app):
        """Test processing search result place successfully."""
        place = {"place_id": "test_id", "name": "Test Restaurant"}
        mock_get_details.return_value = {"place_id": "test_id", "name": "Test Restaurant"}

        with app.app_context():
            with patch("app.restaurants.routes._process_place_data") as mock_process:
                mock_process.return_value = {"place_id": "test_id", "name": "Test Restaurant"}
                result = _process_search_result_place(place, "test-key")
                assert result is not None
                assert result["place_id"] == "test_id"

    def test_process_search_result_place_no_place_id(self, app):
        """Test processing search result place without place_id."""
        place = {"name": "Test Restaurant"}

        with app.app_context():
            result = _process_search_result_place(place, "test-key")
            assert result is None

    def test_parse_address_components(self):
        """Test parsing address components."""
        components = [
            {"types": ["street_number"], "long_name": "123"},
            {"types": ["route"], "long_name": "Main St"},
            {"types": ["locality"], "long_name": "Dallas"},
            {"types": ["administrative_area_level_1"], "long_name": "Texas"},
            {"types": ["postal_code"], "long_name": "75201"},
            {"types": ["country"], "long_name": "United States"},
        ]
        result = parse_address_components(components)
        assert result["street_address"] == "123 Main St"
        assert result["city"] == "Dallas"
        assert result["state"] == "Texas"
        assert result["postal_code"] == "75201"
        assert result["country"] == "United States"

    def test_get_cuisine_choices(self):
        """Test getting cuisine choices."""
        choices = get_cuisine_choices()
        assert "American" in choices
        assert "Chinese" in choices
        assert "Italian" in choices
        assert len(choices) > 10

    def test_get_specific_cuisine_types(self):
        """Test getting specific cuisine types mapping."""
        types = _get_specific_cuisine_types()
        assert "chinese_restaurant" in types
        assert types["chinese_restaurant"] == "Chinese"
        assert "italian_restaurant" in types
        assert types["italian_restaurant"] == "Italian"

    def test_detect_cuisine_from_types_specific(self):
        """Test detecting cuisine from specific types."""
        types_lower = ["chinese_restaurant", "food", "establishment"]
        result = _detect_cuisine_from_types(types_lower)
        assert result == "Chinese"

    def test_detect_cuisine_from_types_keywords(self):
        """Test detecting cuisine from keyword types."""
        types_lower = ["restaurant", "food", "pizza", "italian"]
        result = _detect_cuisine_from_types(types_lower)
        assert result == "Italian"

    def test_detect_cuisine_from_types_bar(self):
        """Test detecting cuisine from bar types."""
        types_lower = ["bar", "restaurant", "food"]
        result = _detect_cuisine_from_types(types_lower)
        assert result == "Pub"

    def test_detect_cuisine_from_types_no_match(self):
        """Test detecting cuisine with no matching types."""
        types_lower = ["establishment", "point_of_interest"]
        result = _detect_cuisine_from_types(types_lower)
        assert result is None

    def test_detect_service_level_from_types_quick_service(self):
        """Test detecting quick service level."""
        types_lower = ["fast_food_restaurant", "meal_takeaway"]
        result = _detect_service_level_from_types(types_lower)
        assert result == "quick_service"

    def test_detect_service_level_from_types_fast_casual(self):
        """Test detecting fast casual service level."""
        types_lower = ["fast_casual_restaurant", "food"]
        result = _detect_service_level_from_types(types_lower)
        assert result == "fast_casual"

    def test_detect_service_level_from_types_fine_dining(self):
        """Test detecting fine dining service level."""
        types_lower = ["fine_dining_restaurant", "upscale_restaurant"]
        result = _detect_service_level_from_types(types_lower)
        assert result == "fine_dining"

    def test_detect_service_level_from_types_casual_dining(self):
        """Test detecting casual dining service level."""
        types_lower = ["restaurant", "food"]
        result = _detect_service_level_from_types(types_lower)
        assert result == "casual_dining"

    def test_detect_service_level_from_types_unknown(self):
        """Test detecting unknown service level."""
        types_lower = ["establishment", "point_of_interest"]
        result = _detect_service_level_from_types(types_lower)
        assert result is None

    def test_analyze_restaurant_types(self, app):
        """Test analyzing restaurant types."""
        types = ["chinese_restaurant", "restaurant", "food"]
        with app.app_context():
            cuisine, service_level = analyze_restaurant_types(types)
            assert cuisine == "Chinese"
            assert service_level == "casual_dining"

    def test_matches_cuisine_pattern_word_boundary(self):
        """Test matching cuisine pattern with word boundary."""
        result = _matches_cuisine_pattern("barbecue restaurant", "bar")
        assert result is False  # Should not match "bar" in "barbecue"

    def test_matches_cuisine_pattern_substring(self):
        """Test matching cuisine pattern with substring."""
        result = _matches_cuisine_pattern("italian restaurant", "italian")
        assert result is True

    def test_detect_cuisine_from_name_japanese(self):
        """Test detecting Japanese cuisine from name."""
        result = detect_cuisine_from_name("Sushi Palace")
        assert result == "Japanese"

    def test_detect_cuisine_from_name_chinese(self):
        """Test detecting Chinese cuisine from name."""
        result = detect_cuisine_from_name("Golden Dragon Chinese Restaurant")
        assert result == "Chinese"

    def test_detect_cuisine_from_name_italian(self):
        """Test detecting Italian cuisine from name."""
        result = detect_cuisine_from_name("Mario's Pizza")
        assert result == "Italian"

    def test_detect_cuisine_from_name_american_chain(self):
        """Test detecting American cuisine from chain name."""
        result = detect_cuisine_from_name("McDonald's")
        assert result == "American"

    def test_detect_cuisine_from_name_pub(self):
        """Test detecting pub from name with food indicators."""
        result = detect_cuisine_from_name("The Sports Bar & Grill")
        assert result == "Pub"

    def test_detect_cuisine_from_name_no_match(self):
        """Test detecting cuisine with no matching patterns."""
        result = detect_cuisine_from_name("Generic Restaurant")
        assert result is None

    def test_detect_chain_restaurant_mcdonalds(self):
        """Test detecting McDonald's as chain."""
        result = detect_chain_restaurant("McDonald's")
        assert result is True

    def test_detect_chain_restaurant_starbucks(self):
        """Test detecting Starbucks as chain."""
        result = detect_chain_restaurant("Starbucks Coffee")
        assert result is True

    def test_detect_chain_restaurant_local(self):
        """Test detecting local restaurant as non-chain."""
        result = detect_chain_restaurant("Local Family Restaurant")
        assert result is False

    def test_generate_description_with_rating(self):
        """Test generating description with rating."""
        place = {
            "rating": 4.5,
            "user_ratings_total": 100,
            "price_level": 2,
            "types": ["restaurant", "food"],
        }
        result = generate_description(place)
        assert "Google Rating: 4.5/5 (100 reviews)" in result
        assert "Price Level: $$" in result

    def test_generate_description_with_editorial_summary(self):
        """Test generating description with editorial summary."""
        place = {
            "editorial_summary": {"overview": "Great local restaurant"},
            "rating": 4.0,
        }
        result = generate_description(place)
        assert "Great local restaurant" in result

    def test_generate_description_minimal(self):
        """Test generating description with minimal data."""
        place = {}
        result = generate_description(place)
        assert result == "Restaurant from Google Places"

    def test_generate_notes_with_price_level(self):
        """Test generating notes with price level."""
        place = {"price_level": 2}
        result = generate_notes(place)
        assert "Moderate pricing" in result

    def test_generate_notes_no_price_level(self):
        """Test generating notes without price level."""
        place = {}
        result = generate_notes(place)
        assert result is None

    def test_create_ajax_success_response_new(self, app, mock_restaurant):
        """Test creating AJAX success response for new restaurant."""
        with app.app_context():
            response, status = _create_ajax_success_response(mock_restaurant, True)
            assert status == 201
            assert response.json["status"] == "success"
            assert response.json["restaurant_id"] == 1

    def test_create_ajax_success_response_existing(self, app, mock_restaurant):
        """Test creating AJAX success response for existing restaurant."""
        with app.app_context():
            response, status = _create_ajax_success_response(mock_restaurant, False)
            assert status == 409
            assert response.json["status"] == "conflict"

    def test_create_ajax_error_response_duplicate_google_place_id(self, app):
        """Test creating AJAX error response for duplicate Google Place ID."""
        from app.restaurants.exceptions import DuplicateGooglePlaceIdError

        existing_restaurant = Mock()
        existing_restaurant.id = 1
        exception = DuplicateGooglePlaceIdError("test_place_id", existing_restaurant)

        with app.app_context():
            response, status = _create_ajax_error_response(exception)
            assert status == 409
            assert response.json["status"] == "conflict"

    def test_create_ajax_error_response_generic(self, app):
        """Test creating AJAX error response for generic error."""
        exception = Exception("Generic error")

        with app.app_context():
            response, status = _create_ajax_error_response(exception)
            assert status == 400
            assert response.json["status"] == "error"

    def test_handle_restaurant_creation_success_ajax(self, app, mock_restaurant):
        """Test handling restaurant creation success for AJAX request."""
        with app.app_context():
            response = _handle_restaurant_creation_success(mock_restaurant, True, True)
            assert response[1] == 201  # Status code

    def test_handle_restaurant_creation_success_form(self, app, mock_restaurant):
        """Test handling restaurant creation success for form request."""
        with app.app_context():
            response = _handle_restaurant_creation_success(mock_restaurant, True, False)
            assert hasattr(response, "status_code")  # Redirect response

    def test_handle_restaurant_creation_error_ajax(self, app):
        """Test handling restaurant creation error for AJAX request."""
        exception = Exception("Test error")
        response = _handle_restaurant_creation_error(exception, True)
        assert response[1] == 400  # Status code

    def test_handle_restaurant_creation_error_form(self, app):
        """Test handling restaurant creation error for form request."""
        exception = Exception("Test error")
        response = _handle_restaurant_creation_error(exception, False)
        assert response is None

    def test_validate_import_file_valid_csv(self):
        """Test validating valid CSV file."""
        file = Mock()
        file.filename = "test.csv"
        result = _validate_import_file(file)
        assert result is True

    def test_validate_import_file_valid_json(self):
        """Test validating valid JSON file."""
        file = Mock()
        file.filename = "test.json"
        result = _validate_import_file(file)
        assert result is True

    def test_validate_import_file_invalid_extension(self):
        """Test validating file with invalid extension."""
        file = Mock()
        file.filename = "test.txt"
        result = _validate_import_file(file)
        assert result is False

    def test_validate_import_file_no_filename(self):
        """Test validating file with no filename."""
        file = Mock()
        file.filename = ""
        result = _validate_import_file(file)
        assert result is False

    def test_parse_import_file_json(self):
        """Test parsing JSON import file."""
        file = Mock()
        file.filename = "test.json"
        file.seek.return_value = None
        file.read.return_value = '[{"name": "Test Restaurant"}]'

        with patch("app.restaurants.routes.json.load") as mock_load:
            mock_load.return_value = [{"name": "Test Restaurant"}]
            result = _parse_import_file(file)
            assert result == [{"name": "Test Restaurant"}]

    def test_parse_import_file_csv(self):
        """Test parsing CSV import file."""
        file = Mock()
        file.filename = "test.csv"
        file.seek.return_value = None
        file.read.return_value = "name,city\nTest Restaurant,Test City"

        with patch("app.restaurants.routes.csv.DictReader") as mock_reader:
            mock_reader.return_value = [{"name": "Test Restaurant", "city": "Test City"}]
            result = _parse_import_file(file)
            assert result == [{"name": "Test Restaurant", "city": "Test City"}]

    def test_parse_import_file_unicode_error(self):
        """Test parsing import file with Unicode error."""
        file = Mock()
        file.filename = "test.csv"
        file.seek.return_value = None
        file.read.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        result = _parse_import_file(file)
        assert result is None

    def test_parse_import_file_exception(self):
        """Test parsing import file with exception."""
        file = Mock()
        file.filename = "test.json"
        file.seek.side_effect = Exception("File error")

        result = _parse_import_file(file)
        assert result is None

    @patch("app.restaurants.routes.services.import_restaurants_from_csv")
    def test_process_import_file_success(self, mock_import, app):
        """Test processing import file successfully."""
        file = Mock()
        file.filename = "test.csv"
        mock_import.return_value = (True, {"success_count": 5, "skipped_count": 2})

        with app.app_context():
            success, result = _process_import_file(file, 1)
            assert success is True
            assert result["success_count"] == 5

    def test_process_import_file_validation_failed(self, app):
        """Test processing import file with validation failure."""
        file = Mock()
        file.filename = "test.txt"

        with app.app_context():
            success, result = _process_import_file(file, 1)
            assert success is False
            assert "File validation failed" in result["message"]

    def test_handle_import_success(self, app):
        """Test handling import success."""
        result_data = {"success_count": 5, "has_warnings": True, "skipped_count": 2}

        with app.app_context():
            with patch("app.restaurants.routes.flash") as mock_flash:
                response = _handle_import_success(result_data)
                assert hasattr(response, "status_code")  # Redirect response
                mock_flash.assert_called()

    def test_handle_import_error(self, app):
        """Test handling import error."""
        result_data = {"message": "Import failed", "error_details": "Test error"}

        with app.app_context():
            with patch("app.restaurants.routes.flash") as mock_flash:
                with patch("app.restaurants.routes.current_app") as mock_app:
                    _handle_import_error(result_data)
                    mock_flash.assert_called()
                    mock_app.logger.error.assert_called()

    def test_validate_google_places_request_success(self, app):
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

    def test_validate_google_places_request_not_json(self, app):
        """Test validating Google Places request with non-JSON content."""
        with app.test_request_context("/", method="POST", data="not json"):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 400

    def test_validate_google_places_request_no_data(self, app):
        """Test validating Google Places request with no data."""
        with app.test_request_context("/", method="POST", json=None):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 400

    def test_validate_google_places_request_no_csrf(self, app):
        """Test validating Google Places request with no CSRF token."""
        with app.test_request_context("/", method="POST", json={"name": "Test"}):
            with app.app_context():
                data, error = _validate_google_places_request()
                assert error is not None
                assert error[1] == 403

    def test_prepare_restaurant_form_success(self, app):
        """Test preparing restaurant form successfully."""
        data = {
            "name": "Test Restaurant",
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
            with patch("app.restaurants.routes.RestaurantForm") as mock_form_class:
                mock_form = Mock()
                mock_form.validate.return_value = True
                mock_form_class.return_value = mock_form

                form, error = _prepare_restaurant_form(data, "test-token")
                assert error is None
                assert form == mock_form

    def test_prepare_restaurant_form_invalid_data(self, app):
        """Test preparing restaurant form with invalid data."""
        data = "not a dictionary"

        with app.app_context():
            form, error = _prepare_restaurant_form(data, "test-token")
            assert error is not None
            assert error[1] == 400

    def test_prepare_restaurant_form_validation_failed(self, app):
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

    def test_create_restaurant_from_form_success(self, app):
        """Test creating restaurant from form successfully."""
        form = Mock()

        with app.app_context():
            with patch("app.restaurants.routes.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_restaurant = Mock()
                    mock_restaurant.id = 1
                    mock_create.return_value = (mock_restaurant, True)

                    result, error = _create_restaurant_from_form(form)
                    assert error is None
                    assert result[0] == mock_restaurant
                    assert result[1] is True

    def test_create_restaurant_from_form_duplicate_google_place_id(self, app):
        """Test creating restaurant from form with duplicate Google Place ID."""
        from app.restaurants.exceptions import DuplicateGooglePlaceIdError

        form = Mock()
        exception = DuplicateGooglePlaceIdError("test_place_id", Mock())

        with app.app_context():
            with patch("app.restaurants.routes.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_create.side_effect = exception

                    result, error = _create_restaurant_from_form(form)
                    assert error is not None
                    assert error[1] == 409

    def test_create_restaurant_from_form_duplicate_restaurant(self, app):
        """Test creating restaurant from form with duplicate restaurant."""
        from app.restaurants.exceptions import DuplicateRestaurantError

        form = Mock()
        exception = DuplicateRestaurantError("Test Restaurant", "Test City", Mock())

        with app.app_context():
            with patch("app.restaurants.routes.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_create.side_effect = exception

                    result, error = _create_restaurant_from_form(form)
                    assert error is not None
                    assert error[1] == 409

    def test_create_restaurant_from_form_exception(self, app):
        """Test creating restaurant from form with exception."""
        form = Mock()
        exception = Exception("Database error")

        with app.app_context():
            with patch("app.restaurants.routes.create_restaurant") as mock_create:
                with patch("app.restaurants.routes.current_user") as mock_user:
                    mock_user.id = 1
                    mock_create.side_effect = exception

                    result, error = _create_restaurant_from_form(form)
                    assert error is not None
                    assert error[1] == 500
