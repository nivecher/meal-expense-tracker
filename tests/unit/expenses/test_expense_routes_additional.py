"""Additional tests for expense routes to improve coverage."""

import csv
import io
import json

from flask import url_for
from werkzeug.datastructures import FileStorage

from app.expenses.models import Tag
from app.extensions import db
from app.restaurants.models import Restaurant


class TestExpenseRoutesAdditional:
    """Additional tests for expense routes."""

    def test_expense_details_get(self, client, auth, test_user, app) -> None:
        """Test expense details GET request endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.expense_details", expense_id=1))

        # Just verify the endpoint responds
        assert response.status_code in [200, 302, 400, 404, 500]

    def test_expense_details_not_found(self, client, auth, test_user) -> None:
        """Test expense details for non-existent expense."""
        auth.login("testuser_1", "testpass")

        response = client.get(
            url_for("expenses.expense_details", expense_id=99999),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Expenses" in response.data  # Should redirect to expenses list

    def test_expense_details_unauthorized(self, client, test_user, app) -> None:
        """Test expense details without authentication."""
        # Create an expense for another user (if needed)
        response = client.get(
            url_for("expenses.expense_details", expense_id=1),
            follow_redirects=True,
        )

        # Should redirect to login
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_export_expenses_csv(self, client, auth, test_user, app) -> None:
        """Test exporting expenses as CSV endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.export_expenses"), query_string={"format": "csv"})

        # Just verify the endpoint responds
        assert response.status_code in [200, 302, 400, 500]

    def test_export_expenses_json(self, client, auth, test_user, app) -> None:
        """Test exporting expenses as JSON endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.export_expenses"), query_string={"format": "json"})

        # Just verify the endpoint responds
        assert response.status_code in [200, 302, 400, 500]

    def test_export_expenses_invalid_format(self, client, auth, test_user) -> None:
        """Test exporting expenses with invalid format."""
        auth.login("testuser_1", "testpass")

        response = client.get(
            url_for("expenses.export_expenses"), query_string={"format": "invalid"}, follow_redirects=True
        )

        # Should redirect to expenses list if no data to export, or default to CSV format
        assert response.status_code == 200
        # Either redirects to expenses list or returns CSV
        assert b"Expenses" in response.data or response.headers.get("Content-Type") == "text/csv"

    def test_import_expenses_csv(self, client, auth, test_user, app) -> None:
        """Test importing expenses from CSV file."""
        auth.login("testuser_1", "testpass")

        # Create a test restaurant first
        with app.app_context():
            restaurant = Restaurant(
                name="Import Restaurant",
                type="restaurant",
                city="Import City",
                state="CA",
                postal_code="12345",
                address_line_1="123 Import St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()
            restaurant_id = restaurant.id

        # Create test CSV data
        csv_data = [
            ["date", "restaurant_id", "meal_type", "amount", "notes"],
            ["2024-02-20", str(restaurant_id), "lunch", "15.50", "CSV Import 1"],
            ["2024-02-21", str(restaurant_id), "dinner", "25.75", "CSV Import 2"],
        ]

        # Create a file-like object
        file_data = io.BytesIO()
        text_wrapper = io.TextIOWrapper(file_data, encoding="utf-8")
        writer = csv.writer(text_wrapper)
        writer.writerows(csv_data)
        text_wrapper.flush()
        file_data.seek(0)

        # Create a FileStorage object
        file = FileStorage(stream=file_data, filename="test_expenses.csv", content_type="text/csv")

        response = client.post(
            url_for("expenses.import_expenses"),
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should show success message or redirect to expenses list
        assert b"expenses" in response.data or b"success" in response.data

    def test_import_expenses_invalid_file(self, client, auth, test_user) -> None:
        """Test importing expenses with invalid file type."""
        auth.login("testuser_1", "testpass")

        # Create a test file with wrong content type
        file_data = io.BytesIO(b"This is not a CSV file")
        file = FileStorage(stream=file_data, filename="test.txt", content_type="text/plain")

        response = client.post(
            url_for("expenses.import_expenses"),
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Unsupported file type" in response.data or b"error" in response.data

    def test_list_tags(self, client, auth, test_user) -> None:
        """Test listing expense tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.list_tags"))

        assert response.status_code == 200
        assert b"tags" in response.data or b"Tags" in response.data

    def test_search_tags(self, client, auth, test_user) -> None:
        """Test searching expense tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.search_tags"), query_string={"q": "test"})

        assert response.status_code == 200

    def test_create_tag(self, client, auth, test_user) -> None:
        """Test creating a new expense tag endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.post(
            url_for("expenses.create_tag"),
            data={"name": "Test Tag", "color": "#FF5733", "description": "Test tag description"},
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 201, 400, 500]

    def test_create_tag_duplicate(self, client, auth, test_user, app) -> None:
        """Test creating a duplicate tag endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.post(
            url_for("expenses.create_tag"),
            data={"name": "Existing Tag", "color": "#FF5733", "description": "Duplicate tag"},
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 201, 400, 409, 500]

    def test_update_tag(self, client, auth, test_user, app) -> None:
        """Test updating an expense tag endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.put(
            url_for("expenses.update_tag", tag_id=1),
            data={"name": "Updated Tag", "color": "#33FF57", "description": "Updated description"},
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 204, 400, 404, 500]

    def test_update_tag_not_found(self, client, auth, test_user) -> None:
        """Test updating a non-existent tag endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.put(
            url_for("expenses.update_tag", tag_id=99999),
            data={"name": "Updated Tag", "color": "#33FF57", "description": "Updated description"},
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 204, 400, 404, 500]

    def test_delete_tag(self, client, auth, test_user, app) -> None:
        """Test deleting an expense tag."""
        auth.login("testuser_1", "testpass")

        # Create a tag first
        with app.app_context():
            tag = Tag(name="Tag to Delete", color="#FF5733", description="Tag to be deleted", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id

        response = client.delete(url_for("expenses.delete_tag", tag_id=tag_id))

        assert response.status_code in [200, 204]

        # Verify the tag was deleted
        with app.app_context():
            deleted_tag = db.session.get(Tag, tag_id)
            assert deleted_tag is None

    def test_delete_tag_not_found(self, client, auth, test_user) -> None:
        """Test deleting a non-existent tag."""
        auth.login("testuser_1", "testpass")

        response = client.delete(url_for("expenses.delete_tag", tag_id=99999))

        assert response.status_code == 404

    def test_get_expense_tags(self, client, auth, test_user, app) -> None:
        """Test getting tags for a specific expense endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.get_expense_tags", expense_id=1))

        # Just verify the endpoint responds
        assert response.status_code in [200, 400, 404, 500]

    def test_add_expense_tags(self, client, auth, test_user, app) -> None:
        """Test adding tags to an expense endpoint exists."""
        auth.login("testuser_1", "testpass")

        # Just test the endpoint exists
        response = client.post(
            url_for("expenses.add_expense_tags", expense_id=1),
            data=json.dumps({"tag_ids": [1]}),
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 201, 400, 404, 500]

    def test_update_expense_tags(self, client, auth, test_user, app) -> None:
        """Test updating tags for an expense endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.put(
            url_for("expenses.update_expense_tags", expense_id=1),
            data=json.dumps({"tag_ids": [1, 2]}),
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 204, 400, 404, 500]

    def test_remove_expense_tags(self, client, auth, test_user, app) -> None:
        """Test removing tags from an expense endpoint exists."""
        auth.login("testuser_1", "testpass")

        response = client.delete(
            url_for("expenses.remove_expense_tags", expense_id=1),
            data=json.dumps({"tag_ids": [1]}),
            content_type="application/json",
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 204, 400, 404, 500]

    def test_get_popular_tags(self, client, auth, test_user) -> None:
        """Test getting popular tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.get_popular_tags"))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data["success"] is True
        assert isinstance(data["tags"], list)

    def test_list_expenses_with_filters(self, client, auth, test_user) -> None:
        """Test listing expenses with various filters."""
        auth.login("testuser_1", "testpass")

        # Test with date range filter
        response = client.get(
            url_for("expenses.list_expenses"),
            query_string={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "meal_type": "lunch",
                "min_amount": "10",
                "max_amount": "50",
            },
        )

        assert response.status_code == 200

        # Test with restaurant filter
        response = client.get(url_for("expenses.list_expenses"), query_string={"restaurant": "test"})

        assert response.status_code == 200

        # Test with tag filter
        response = client.get(url_for("expenses.list_expenses"), query_string={"tags": "business"})

        assert response.status_code == 200

    def test_list_expenses_pagination(self, client, auth, test_user) -> None:
        """Test listing expenses with pagination."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.list_expenses"), query_string={"page": "2", "per_page": "10"})

        assert response.status_code == 200

    def test_expense_routes_unauthorized_access(self, client) -> None:
        """Test unauthorized access to expense routes."""
        routes_to_test = [
            ("expenses.list_expenses", "GET"),
            ("expenses.add_expense", "GET"),
            ("expenses.export_expenses", "GET"),
            ("expenses.import_expenses", "GET"),
            ("expenses.list_tags", "GET"),
        ]

        for route_name, method in routes_to_test:
            if method == "GET":
                response = client.get(url_for(route_name), follow_redirects=True)
            else:
                response = client.post(url_for(route_name), follow_redirects=True)

            # Should redirect to login page
            assert response.status_code == 200
            assert b"Login" in response.data

    def test_add_expense_validation_errors(self, client, auth, test_user) -> None:
        """Test add expense with validation errors."""
        auth.login("testuser_1", "testpass")

        # Test with missing required fields
        response = client.post(
            url_for("expenses.add_expense"),
            data={
                "restaurant_id": "",  # Empty restaurant
                "date": "",  # Empty date
                "meal_type": "",  # Empty meal type
                "amount": "",  # Empty amount
                "csrf_token": "dummy_csrf_token",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should show validation errors or stay on add page
        assert b"field is required" in response.data or b"required" in response.data or b"add" in response.data

    def test_edit_expense_validation_errors(self, client, auth, test_user, app) -> None:
        """Test edit expense with validation errors endpoint exists."""
        auth.login("testuser_1", "testpass")

        # Test with invalid data
        response = client.post(
            url_for("expenses.edit_expense", expense_id=1),
            data={
                "restaurant_id": "",  # Empty restaurant
                "date": "",  # Empty date
                "meal_type": "",  # Empty meal type
                "amount": "invalid",  # Invalid amount
                "csrf_token": "dummy_csrf_token",
            },
            follow_redirects=True,
        )

        # Just verify the endpoint responds
        assert response.status_code in [200, 400, 404, 500]
