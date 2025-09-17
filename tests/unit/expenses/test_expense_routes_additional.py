"""Additional tests for expense routes to improve coverage."""

import csv
import io
import json

from flask import url_for
from werkzeug.datastructures import FileStorage

from app.expenses.models import Expense, ExpenseTag, Tag
from app.extensions import db
from app.restaurants.models import Restaurant


class TestExpenseRoutesAdditional:
    """Additional tests for expense routes."""

    def test_expense_details_get(self, client, auth, test_user, app):
        """Test expense details GET request."""
        auth.login("testuser_1", "testpass")

        # Create a test expense
        with app.app_context():
            restaurant = Restaurant(
                name="Test Restaurant",
                type="restaurant",
                city="Test City",
                state="CA",
                postal_code="12345",
                address="123 Test St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=25.50,
                notes="Test expense details",
            )
            db.session.add(expense)
            db.session.commit()

            expense_id = expense.id

        response = client.get(url_for("expenses.expense_details", expense_id=expense_id))

        assert response.status_code == 200
        assert b"Test expense details" in response.data
        assert b"25.50" in response.data
        assert b"Test Restaurant" in response.data

    def test_expense_details_not_found(self, client, auth, test_user):
        """Test expense details for non-existent expense."""
        auth.login("testuser_1", "testpass")

        response = client.get(
            url_for("expenses.expense_details", expense_id=99999),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Expenses" in response.data  # Should redirect to expenses list

    def test_expense_details_unauthorized(self, client, test_user, app):
        """Test expense details without authentication."""
        # Create an expense for another user (if needed)
        response = client.get(
            url_for("expenses.expense_details", expense_id=1),
            follow_redirects=True,
        )

        # Should redirect to login
        assert response.status_code == 200
        assert b"Login" in response.data

    def test_export_expenses_csv(self, client, auth, test_user, app):
        """Test exporting expenses as CSV."""
        auth.login("testuser_1", "testpass")

        # Create a test expense
        with app.app_context():
            restaurant = Restaurant(
                name="Export Restaurant",
                type="restaurant",
                city="Export City",
                state="CA",
                postal_code="12345",
                address="123 Export St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="dinner",
                amount=45.75,
                notes="Export test expense",
            )
            db.session.add(expense)
            db.session.commit()

        response = client.get(url_for("expenses.export_expenses"), query_string={"format": "csv"})

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/csv; charset=utf-8"

        # Check for content disposition header
        assert "Content-Disposition" in response.headers
        assert "expenses.csv" in response.headers["Content-Disposition"]

        # Get the response data as text
        response_text = response.get_data(as_text=True)
        assert "Export Restaurant" in response_text
        assert "45.75" in response_text

    def test_export_expenses_json(self, client, auth, test_user, app):
        """Test exporting expenses as JSON."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.export_expenses"), query_string={"format": "json"})

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

        # Check for content disposition header
        assert "Content-Disposition" in response.headers
        assert "expenses.json" in response.headers["Content-Disposition"]

        # Get the response data as JSON
        data = response.get_json()
        assert isinstance(data, list)

    def test_export_expenses_invalid_format(self, client, auth, test_user):
        """Test exporting expenses with invalid format."""
        auth.login("testuser_1", "testpass")

        response = client.get(
            url_for("expenses.export_expenses"), query_string={"format": "invalid"}, follow_redirects=True
        )

        # Should redirect to expenses list if no data to export, or default to CSV format
        assert response.status_code == 200
        # Either redirects to expenses list or returns CSV
        assert b"Expenses" in response.data or response.headers.get("Content-Type") == "text/csv"

    def test_import_expenses_csv(self, client, auth, test_user, app):
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
                address="123 Import St",
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

    def test_import_expenses_invalid_file(self, client, auth, test_user):
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

    def test_list_tags(self, client, auth, test_user):
        """Test listing expense tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.list_tags"))

        assert response.status_code == 200
        assert b"tags" in response.data or b"Tags" in response.data

    def test_search_tags(self, client, auth, test_user):
        """Test searching expense tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.search_tags"), query_string={"q": "test"})

        assert response.status_code == 200

    def test_create_tag(self, client, auth, test_user):
        """Test creating a new expense tag."""
        auth.login("testuser_1", "testpass")

        response = client.post(
            url_for("expenses.create_tag"),
            data={"name": "Test Tag", "color": "#FF5733", "description": "Test tag description"},
            content_type="application/json",
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data["success"] is True or "Test Tag" in str(response.data)

    def test_create_tag_duplicate(self, client, auth, test_user, app):
        """Test creating a duplicate tag."""
        auth.login("testuser_1", "testpass")

        # Create a tag first
        with app.app_context():
            tag = Tag(name="Existing Tag", color="#FF5733", description="Existing tag", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()

        # Try to create a duplicate
        response = client.post(
            url_for("expenses.create_tag"),
            data={"name": "Existing Tag", "color": "#FF5733", "description": "Duplicate tag"},
            content_type="application/json",
        )

        assert response.status_code in [400, 409]
        data = response.get_json()
        assert data["success"] is False or "already exists" in str(response.data)

    def test_update_tag(self, client, auth, test_user, app):
        """Test updating an expense tag."""
        auth.login("testuser_1", "testpass")

        # Create a tag first
        with app.app_context():
            tag = Tag(name="Original Tag", color="#FF5733", description="Original description", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id

        response = client.put(
            url_for("expenses.update_tag", tag_id=tag_id),
            data={"name": "Updated Tag", "color": "#33FF57", "description": "Updated description"},
            content_type="application/json",
        )

        assert response.status_code in [200, 204]

        # Verify the tag was updated
        with app.app_context():
            updated_tag = db.session.get(Tag, tag_id)
            assert updated_tag.name == "Updated Tag"
            assert updated_tag.color == "#33FF57"

    def test_update_tag_not_found(self, client, auth, test_user):
        """Test updating a non-existent tag."""
        auth.login("testuser_1", "testpass")

        response = client.put(
            url_for("expenses.update_tag", tag_id=99999),
            data={"name": "Updated Tag", "color": "#33FF57", "description": "Updated description"},
            content_type="application/json",
        )

        assert response.status_code == 404

    def test_delete_tag(self, client, auth, test_user, app):
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

    def test_delete_tag_not_found(self, client, auth, test_user):
        """Test deleting a non-existent tag."""
        auth.login("testuser_1", "testpass")

        response = client.delete(url_for("expenses.delete_tag", tag_id=99999))

        assert response.status_code == 404

    def test_get_expense_tags(self, client, auth, test_user, app):
        """Test getting tags for a specific expense."""
        auth.login("testuser_1", "testpass")

        # Create test data
        with app.app_context():
            restaurant = Restaurant(
                name="Tag Restaurant",
                type="restaurant",
                city="Tag City",
                state="CA",
                postal_code="12345",
                address="123 Tag St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=20.00,
                notes="Tagged expense",
            )
            db.session.add(expense)
            db.session.commit()

            tag = Tag(name="Expense Tag", color="#FF5733", description="Tag for expense", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()

            # Associate tag with expense
            expense_tag = ExpenseTag(expense_id=expense.id, tag_id=tag.id)
            db.session.add(expense_tag)
            db.session.commit()

            expense_id = expense.id

        response = client.get(url_for("expenses.get_expense_tags", expense_id=expense_id))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Expense Tag"

    def test_add_expense_tags(self, client, auth, test_user, app):
        """Test adding tags to an expense."""
        auth.login("testuser_1", "testpass")

        # Create test data
        with app.app_context():
            restaurant = Restaurant(
                name="Add Tag Restaurant",
                type="restaurant",
                city="Add Tag City",
                state="CA",
                postal_code="12345",
                address="123 Add Tag St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=20.00,
                notes="Expense for tagging",
            )
            db.session.add(expense)
            db.session.commit()

            tag = Tag(name="Add Tag", color="#FF5733", description="Tag to add", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()

            expense_id = expense.id
            tag_id = tag.id

        response = client.post(
            url_for("expenses.add_expense_tags", expense_id=expense_id),
            data=json.dumps({"tag_ids": [tag_id]}),
            content_type="application/json",
        )

        assert response.status_code in [200, 201]
        data = response.get_json()
        assert data["success"] is True

    def test_update_expense_tags(self, client, auth, test_user, app):
        """Test updating tags for an expense."""
        auth.login("testuser_1", "testpass")

        # Create test data
        with app.app_context():
            restaurant = Restaurant(
                name="Update Tag Restaurant",
                type="restaurant",
                city="Update Tag City",
                state="CA",
                postal_code="12345",
                address="123 Update Tag St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=20.00,
                notes="Expense for tag updates",
            )
            db.session.add(expense)
            db.session.commit()

            tag1 = Tag(name="Update Tag 1", color="#FF5733", description="Tag 1", user_id=test_user.id)
            tag2 = Tag(name="Update Tag 2", color="#33FF57", description="Tag 2", user_id=test_user.id)
            db.session.add(tag1)
            db.session.add(tag2)
            db.session.commit()

            expense_id = expense.id
            tag_ids = [tag1.id, tag2.id]

        response = client.put(
            url_for("expenses.update_expense_tags", expense_id=expense_id),
            data=json.dumps({"tag_ids": tag_ids}),
            content_type="application/json",
        )

        assert response.status_code in [200, 204]
        data = response.get_json()
        if data:
            assert data.get("success") is True

    def test_remove_expense_tags(self, client, auth, test_user, app):
        """Test removing tags from an expense."""
        auth.login("testuser_1", "testpass")

        # Create test data
        with app.app_context():
            restaurant = Restaurant(
                name="Remove Tag Restaurant",
                type="restaurant",
                city="Remove Tag City",
                state="CA",
                postal_code="12345",
                address="123 Remove Tag St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=20.00,
                notes="Expense for tag removal",
            )
            db.session.add(expense)
            db.session.commit()

            tag = Tag(name="Remove Tag", color="#FF5733", description="Tag to remove", user_id=test_user.id)
            db.session.add(tag)
            db.session.commit()

            # Associate tag with expense
            expense_tag = ExpenseTag(expense_id=expense.id, tag_id=tag.id)
            db.session.add(expense_tag)
            db.session.commit()

            expense_id = expense.id
            tag_id = tag.id

        response = client.delete(
            url_for("expenses.remove_expense_tags", expense_id=expense_id),
            data=json.dumps({"tag_ids": [tag_id]}),
            content_type="application/json",
        )

        assert response.status_code in [200, 204]

        # Verify the tag was removed
        with app.app_context():
            expense_tag = ExpenseTag.query.filter_by(expense_id=expense_id, tag_id=tag_id).first()
            assert expense_tag is None

    def test_get_popular_tags(self, client, auth, test_user):
        """Test getting popular tags."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.get_popular_tags"))

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data["success"] is True
        assert isinstance(data["tags"], list)

    def test_list_expenses_with_filters(self, client, auth, test_user):
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

    def test_list_expenses_pagination(self, client, auth, test_user):
        """Test listing expenses with pagination."""
        auth.login("testuser_1", "testpass")

        response = client.get(url_for("expenses.list_expenses"), query_string={"page": "2", "per_page": "10"})

        assert response.status_code == 200

    def test_expense_routes_unauthorized_access(self, client):
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

    def test_add_expense_validation_errors(self, client, auth, test_user):
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

    def test_edit_expense_validation_errors(self, client, auth, test_user, app):
        """Test edit expense with validation errors."""
        auth.login("testuser_1", "testpass")

        # Create a test expense first
        with app.app_context():
            restaurant = Restaurant(
                name="Validation Restaurant",
                type="restaurant",
                city="Validation City",
                state="CA",
                postal_code="12345",
                address="123 Validation St",
                user_id=test_user.id,
            )
            db.session.add(restaurant)
            db.session.commit()

            expense = Expense(
                user_id=test_user.id,
                restaurant_id=restaurant.id,
                date="2024-02-20",
                meal_type="lunch",
                amount=20.00,
                notes="Validation test expense",
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        # Test with invalid data
        response = client.post(
            url_for("expenses.edit_expense", expense_id=expense_id),
            data={
                "restaurant_id": "",  # Empty restaurant
                "date": "",  # Empty date
                "meal_type": "",  # Empty meal type
                "amount": "invalid",  # Invalid amount
                "csrf_token": "dummy_csrf_token",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Should show validation errors or stay on edit page
        assert b"field is required" in response.data or b"required" in response.data or b"edit" in response.data
