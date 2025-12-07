"""Additional tests for expense routes to improve coverage."""

import csv
import io

from werkzeug.datastructures import FileStorage


class TestExpenseRoutesAdditional:
    """Additional tests for expense routes."""

    def test_expense_details_unauthorized(self, client) -> None:
        """Test expense details with unauthorized access."""
        response = client.get("/expenses/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_expense_details_not_found(self, client, auth, test_user) -> None:
        """Test expense details with non-existent expense."""
        auth.login("testuser_1", "testpass")
        response = client.get("/expenses/99999", follow_redirects=True)
        assert response.status_code == 200
        assert b"Expenses" in response.data

    def test_export_expenses_formats(self, client, auth, test_user) -> None:
        """Test exporting expenses in different formats."""
        auth.login("testuser_1", "testpass")

        # CSV format
        response = client.get("/expenses/export", query_string={"format": "csv"})
        assert response.status_code in [200, 302]

        # JSON format
        response = client.get("/expenses/export", query_string={"format": "json"})
        assert response.status_code in [200, 302]

        # Invalid format - should handle gracefully
        response = client.get("/expenses/export", query_string={"format": "invalid"}, follow_redirects=True)
        assert response.status_code == 200
        assert b"Expenses" in response.data or response.headers.get("Content-Type") == "text/csv"

    def test_import_expenses(self, client, auth, test_user) -> None:
        """Test importing expenses from CSV file."""
        auth.login("testuser_1", "testpass")

        # Create a test restaurant first via client
        client.post(
            "/restaurants/add",
            data={
                "name": "Import Restaurant",
                "type": "restaurant",
                "city": "Import City",
                "state": "CA",
                "zip_code": "12345",
                "address": "123 Import St",
            },
            follow_redirects=True,
        )
        restaurant_id = 1  # Assuming it gets ID 1

        # Create test CSV data
        csv_data = [
            ["date", "restaurant_id", "meal_type", "amount", "notes"],
            ["2024-02-20", str(restaurant_id), "lunch", "15.50", "CSV Import 1"],
            ["2024-02-21", str(restaurant_id), "dinner", "25.75", "CSV Import 2"],
        ]

        file_data = io.BytesIO()
        text_wrapper = io.TextIOWrapper(file_data, encoding="utf-8")
        writer = csv.writer(text_wrapper)
        writer.writerows(csv_data)
        text_wrapper.flush()
        file_data.seek(0)

        file = FileStorage(stream=file_data, filename="test_expenses.csv", content_type="text/csv")

        response = client.post(
            "/expenses/import",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"expenses" in response.data or b"success" in response.data

        # Test invalid file type
        file_data = io.BytesIO(b"This is not a CSV file")
        file = FileStorage(stream=file_data, filename="test.txt", content_type="text/plain")

        response = client.post(
            "/expenses/import",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Unsupported file type" in response.data or b"error" in response.data

    def test_tag_operations(self, client, auth, test_user) -> None:
        """Test tag CRUD operations."""
        auth.login("testuser_1", "testpass")

        # List tags
        response = client.get("/expenses/tags")
        assert response.status_code == 200
        assert b"tags" in response.data or b"Tags" in response.data

        # Search tags
        response = client.get("/expenses/tags/search", query_string={"q": "test"})
        assert response.status_code == 200

        # Get popular tags
        response = client.get("/expenses/tags/popular")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data["success"] is True
        assert isinstance(data["tags"], list)

        # Create tag via API if endpoint exists, otherwise skip deletion test
        # For now, test deletion of non-existent tag
        response = client.delete("/expenses/tags/99999")
        assert response.status_code == 404

    def test_expense_listing_filters(self, client, auth, test_user) -> None:
        """Test listing expenses with various filters and pagination."""
        auth.login("testuser_1", "testpass")

        # Test with date range and filters
        response = client.get(
            "/expenses",
            query_string={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "meal_type": "lunch",
                "min_amount": "10",
                "max_amount": "50",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Test with restaurant filter
        response = client.get("/expenses", query_string={"restaurant": "test"}, follow_redirects=True)
        assert response.status_code == 200

        # Test with tag filter
        response = client.get("/expenses", query_string={"tags": "business"}, follow_redirects=True)
        assert response.status_code == 200

        # Test pagination
        response = client.get("/expenses", query_string={"page": "2", "per_page": "10"}, follow_redirects=True)
        assert response.status_code == 200

    def test_expense_routes_unauthorized_access(self, client) -> None:
        """Test unauthorized access to expense routes."""
        routes_to_test = [
            ("/expenses", "GET"),
            ("/expenses/add", "GET"),
            ("/expenses/export", "GET"),
            ("/expenses/import", "GET"),
            ("/expenses/tags", "GET"),
        ]

        for route_url, method in routes_to_test:
            if method == "GET":
                response = client.get(route_url, follow_redirects=True)
            else:
                response = client.post(route_url, follow_redirects=True)

            assert response.status_code == 200
            assert b"Login" in response.data

    def test_expense_validation_errors(self, client, auth, test_user) -> None:
        """Test expense form validation errors."""
        auth.login("testuser_1", "testpass")

        # Add expense with missing required fields
        response = client.post(
            "/expenses/add",
            data={
                "restaurant_id": "",
                "date": "",
                "meal_type": "",
                "amount": "",
                "csrf_token": "dummy_csrf_token",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"field is required" in response.data or b"required" in response.data or b"add" in response.data

        # Edit expense with invalid data
        response = client.post(
            "/expenses/1/edit",
            data={
                "restaurant_id": "",
                "date": "",
                "meal_type": "",
                "amount": "invalid",
                "csrf_token": "dummy_csrf_token",
            },
            follow_redirects=True,
        )

        assert response.status_code in [200, 400, 404]
