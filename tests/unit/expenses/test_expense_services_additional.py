"""Additional tests for expense services to improve coverage."""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from werkzeug.datastructures import MultiDict

from app.expenses.models import Expense
from app.expenses.services import (
    _combine_date_time_with_timezone,
    _parse_tags_json,
    _process_amount,
    _process_date,
    _sort_categories_by_default_order,
    _validate_tags_list,
    create_expense,
    get_receipt_reconciliation,
    prepare_expense_form,
    update_expense,
)
from app.receipts.models import Receipt


class MockForm:
    """Simple mock form for testing."""

    def __init__(self, **kwargs):
        defaults = {
            "cleared_date": None,
        }
        defaults.update(kwargs)
        self.data = defaults.copy()
        for key, value in defaults.items():
            setattr(self, key, type("Field", (), {"data": value})())


class TestExpenseServicesAdditional:
    """Additional tests for expense services."""

    def test_expense_form_requires_restaurant_date_and_amount(self, app) -> None:
        """Test the expense form required field contract."""
        from app.expenses.forms import ExpenseForm

        with app.test_request_context("/expenses/add", method="POST"):
            form = ExpenseForm(
                formdata=MultiDict(
                    {
                        "restaurant_id": "",
                        "date": "",
                        "amount": "",
                    }
                )
            )

            assert form.validate() is False
            assert "Restaurant is required" in form.restaurant_id.errors
            assert "Visit Date is required" in form.date.errors
            assert "Amount is required" in form.amount.errors

    def test_prepare_expense_form(self, app) -> None:
        """Test preparing expense form with data."""
        with app.app_context():
            result = prepare_expense_form(user_id=1)
            assert result is not None
            # Should return a tuple with form, restaurants, categories
            assert isinstance(result, tuple)
            assert len(result) == 3
            form, restaurants, categories = result
            assert form is not None
            assert hasattr(form, "restaurant_id")
            assert hasattr(form, "date")
            assert hasattr(form, "meal_type")
            assert hasattr(form, "amount")
            assert hasattr(form, "notes")

    def test_process_date_valid(self, app) -> None:
        """Test processing valid date."""
        with app.app_context():
            test_date = date(2024, 2, 20)

            processed_date, error = _process_date(test_date)

            assert processed_date == test_date
            assert error is None

    def test_process_date_string(self, app) -> None:
        """Test processing date string."""
        with app.app_context():
            date_str = "2024-02-20"

            processed_date, error = _process_date(date_str)

            assert processed_date == date(2024, 2, 20)
            assert error is None

    def test_process_date_invalid(self, app) -> None:
        """Test processing invalid date."""
        with app.app_context():
            invalid_date = "not-a-date"

            processed_date, error = _process_date(invalid_date)

            assert processed_date is None
            assert error is not None

    def test_process_date_future(self, app) -> None:
        """Test processing future date."""
        with app.app_context():
            future_date = date(2030, 1, 1)

            processed_date, error = _process_date(future_date)

            # The service doesn't actually validate future dates
            assert processed_date == future_date
            assert error is None

    def test_process_amount_valid(self, app) -> None:
        """Test processing valid amount."""
        with app.app_context():
            amount = Decimal("25.50")

            processed_amount, error = _process_amount(amount)

            assert processed_amount == amount
            assert error is None

    def test_process_amount_string(self, app) -> None:
        """Test processing amount string."""
        with app.app_context():
            amount_str = "25.50"

            processed_amount, error = _process_amount(amount_str)

            assert processed_amount == Decimal("25.50")
            assert error is None

    def test_process_amount_invalid(self, app) -> None:
        """Test processing invalid amount."""
        with app.app_context():
            invalid_amount = "not-a-number"

            processed_amount, error = _process_amount(invalid_amount)

            assert processed_amount is None
            assert error is not None

    def test_process_amount_negative(self, app) -> None:
        """Test processing negative amount."""
        with app.app_context():
            negative_amount = Decimal("-10.00")

            processed_amount, error = _process_amount(negative_amount)

            # The service uses abs() so negative becomes positive
            assert processed_amount == Decimal("10.00")
            assert error is None

    def test_process_amount_zero(self, app) -> None:
        """Test processing zero amount."""
        with app.app_context():
            zero_amount = Decimal("0.00")

            processed_amount, error = _process_amount(zero_amount)

            assert processed_amount == Decimal("0.00")
            assert error is None

    def test_parse_tags_json_valid(self, app) -> None:
        """Test parsing valid JSON tags."""
        with app.app_context():
            tags_json = '["business", "lunch", "client"]'

            tags, error = _parse_tags_json(tags_json)

            assert tags == ["business", "lunch", "client"]
            assert error is None

    def test_parse_tags_json_empty(self, app) -> None:
        """Test parsing empty JSON tags."""
        with app.app_context():
            tags_json = "[]"

            tags, error = _parse_tags_json(tags_json)

            assert tags == []
            assert error is None

    def test_parse_tags_json_invalid(self, app) -> None:
        """Test parsing invalid JSON tags."""
        with app.app_context():
            tags_json = '{"invalid": "json"}'

            tags, error = _parse_tags_json(tags_json)

            # The service actually parses valid JSON but it's not a list
            assert tags == {"invalid": "json"}
            # The service doesn't return an error for valid JSON, even if it's not a list
            assert error is None

    def test_validate_tags_list_valid(self) -> None:
        """Test validating valid tags list."""
        tags_list = ["business", "lunch", "client"]

        validated_tags, error = _validate_tags_list(tags_list)

        assert validated_tags == ["business", "lunch", "client"]
        assert error is None

    def test_validate_tags_list_not_list(self) -> None:
        """Test validating non-list tags."""
        tags_not_list = "business,lunch,client"

        validated_tags, error = _validate_tags_list(tags_not_list)

        assert validated_tags is None
        assert error is not None

    def test_validate_tags_list_invalid_items(self) -> None:
        """Test validating tags list with invalid items."""
        tags_with_invalid = ["business", 123, "client"]

        validated_tags, error = _validate_tags_list(tags_with_invalid)

        assert validated_tags is None
        assert error is not None
        assert "Invalid tag format" in error

    def test_validate_tags_list_empty_strings(self) -> None:
        """Test validating tags list with empty strings."""
        tags_with_empty = ["business", "", "client"]

        validated_tags, error = _validate_tags_list(tags_with_empty)

        # Service filters out empty strings
        assert validated_tags == ["business", "client"]
        assert error is None

    def test_validate_tags_list_too_long(self) -> None:
        """Test validating tags list that's too long."""
        long_tags = ["tag" + str(i) for i in range(11)]  # 11 tags

        validated_tags, error = _validate_tags_list(long_tags)

        # Service allows more than 10 tags
        assert validated_tags == long_tags
        assert error is None

    def test_sort_categories_by_default_order(self) -> None:
        """Test sorting categories by default order."""
        # Mock categories with different names
        category1 = Mock()
        category1.name = "Business"
        category1.id = 1

        category2 = Mock()
        category2.name = "Personal"
        category2.id = 2

        category3 = Mock()
        category3.name = "Travel"
        category3.id = 3

        categories = [category3, category1, category2]  # Unsorted

        sorted_categories = _sort_categories_by_default_order(categories)

        # Should be sorted by name alphabetically
        assert sorted_categories[0].name == "Business"
        assert sorted_categories[1].name == "Personal"
        assert sorted_categories[2].name == "Travel"

    def test_combine_date_time_with_timezone_no_time(self, app) -> None:
        """Test combining date and time with timezone when no time is provided."""
        with app.app_context():
            test_date = date(2024, 7, 23)
            browser_timezone = "America/Chicago"  # CDT in July (UTC-5), CST in winter (UTC-6)

            result = _combine_date_time_with_timezone(test_date, None, browser_timezone)

            # Should be timezone-aware UTC datetime
            assert result.tzinfo is not None
            assert result.tzinfo == UTC
            # Should use noon in browser timezone, which converts to UTC
            # July 23, 2024 12:00:00 CDT (UTC-5) = July 23, 2024 17:00:00 UTC
            # January 23, 2024 12:00:00 CST (UTC-6) = January 23, 2024 18:00:00 UTC
            assert result.date() == test_date
            # In July, Chicago is in CDT (UTC-5), so noon = 17:00 UTC
            # In January, Chicago is in CST (UTC-6), so noon = 18:00 UTC
            assert result.hour in (17, 18)  # Allow for DST variations

    def test_combine_date_time_with_timezone_with_time(self, app) -> None:
        """Test combining date and time with timezone when time is provided."""
        with app.app_context():
            test_date = date(2024, 7, 23)
            test_time = time(19, 27)  # 7:27 PM
            browser_timezone = "America/Chicago"  # CST (UTC-6)

            result = _combine_date_time_with_timezone(test_date, test_time, browser_timezone)

            # Should be timezone-aware UTC datetime
            assert result.tzinfo is not None
            assert result.tzinfo == UTC
            # July 23, 2024 19:27:00 CDT = July 24, 2024 00:27:00 UTC (next day!)
            # But we want to preserve the date, so the date should be July 23
            # Actually, 19:27 CDT = 00:27 UTC next day, so date shifts
            # This is expected behavior - the time is interpreted in browser timezone
            assert result.hour == 0  # 19:27 CDT = 00:27 UTC
            assert result.minute == 27

    def test_date_preservation_when_editing_expense_cst(
        self, app, test_expense, test_restaurant, test_category
    ) -> None:
        """Test that date is preserved correctly when editing expense in CST timezone.

        This test specifically addresses the issue where editing an expense
        would change the date due to timezone conversion issues.
        """
        from app.expenses.forms import ExpenseForm
        from app.expenses.models import Expense
        from app.extensions import db

        with app.app_context():
            # Create an expense with a specific date/time in UTC
            # July 23, 2024 18:00:00 UTC = July 23, 2024 12:00:00 CST
            original_utc_datetime = datetime(2024, 7, 23, 18, 0, 0, tzinfo=UTC)
            expense = Expense(
                amount=Decimal("75.95"),
                date=original_utc_datetime,
                notes="Test expense",
                user_id=test_expense.user_id,
                restaurant_id=test_restaurant.id,
                category_id=test_category.id,
            )
            db.session.add(expense)
            db.session.commit()
            db.session.refresh(expense)

            # Create a form with the same date (as it would appear in browser timezone)
            # In CST, July 23, 2024 18:00:00 UTC displays as July 23, 2024 12:00:00
            # So the form should show July 23, 2024
            form = ExpenseForm()
            form.date.data = date(2024, 7, 23)  # Same date as original
            form.time.data = time(19, 27)  # Different time
            form.amount.data = Decimal("75.95")
            form.notes.data = "Updated expense"
            form.restaurant_id.data = test_restaurant.id
            form.category_id.data = test_category.id
            form.meal_type.data = None
            form.order_type.data = None
            form.party_size.data = None
            form.tags.data = ""

            # Mock browser timezone as CST
            with patch("app.utils.timezone_utils.get_browser_timezone", return_value="America/Chicago"):
                with patch("app.utils.timezone_utils.normalize_timezone", return_value="America/Chicago"):
                    updated_expense, error = update_expense(expense, form)

            assert error is None, f"Update failed with error: {error}"
            assert updated_expense is not None

            # Verify the date is preserved correctly
            # The date should still be July 23, 2024 when converted back to browser timezone
            from app.utils.timezone_utils import convert_to_browser_timezone

            updated_date_browser_tz = convert_to_browser_timezone(updated_expense.date, "America/Chicago")
            assert updated_date_browser_tz.date() == date(2024, 7, 23), (
                f"Date changed! Expected July 23, got {updated_date_browser_tz.date()}. "
                f"UTC date: {updated_expense.date.date()}, UTC datetime: {updated_expense.date}"
            )

    def test_date_preservation_when_editing_expense_early_utc(
        self, app, test_expense, test_restaurant, test_category
    ) -> None:
        """Test date preservation when expense has early UTC time that would shift date in CST.

        This tests the edge case where an expense stored as 2024-01-15 01:00:00 UTC
        displays as 2024-01-14 19:00:00 in CST, but the date should be preserved
        as 2024-01-14 when editing.
        """
        from app.expenses.forms import ExpenseForm
        from app.expenses.models import Expense
        from app.extensions import db

        with app.app_context():
            # Create an expense with early UTC time
            # January 15, 2024 01:00:00 UTC = January 14, 2024 19:00:00 CST
            original_utc_datetime = datetime(2024, 1, 15, 1, 0, 0, tzinfo=UTC)
            expense = Expense(
                amount=Decimal("50.00"),
                date=original_utc_datetime,
                notes="Early UTC expense",
                user_id=test_expense.user_id,
                restaurant_id=test_restaurant.id,
                category_id=test_category.id,
            )
            db.session.add(expense)
            db.session.commit()
            db.session.refresh(expense)

            # In CST, this displays as January 14, 2024
            # So the form should show January 14, 2024 (browser timezone date)
            form = ExpenseForm()
            form.date.data = date(2024, 1, 14)  # Browser timezone date (what user sees)
            form.time.data = None  # No time specified
            form.amount.data = Decimal("50.00")
            form.notes.data = "Updated expense"
            form.restaurant_id.data = test_restaurant.id
            form.category_id.data = test_category.id
            form.meal_type.data = None
            form.order_type.data = None
            form.party_size.data = None
            form.tags.data = ""

            # Mock browser timezone as CST
            with patch("app.utils.timezone_utils.get_browser_timezone", return_value="America/Chicago"):
                with patch("app.utils.timezone_utils.normalize_timezone", return_value="America/Chicago"):
                    updated_expense, error = update_expense(expense, form)

            assert error is None, f"Update failed with error: {error}"
            assert updated_expense is not None

            # Verify the date is preserved correctly in browser timezone
            # When displayed in CST, it should still show January 14, 2024
            from app.utils.timezone_utils import convert_to_browser_timezone

            updated_date_browser_tz = convert_to_browser_timezone(updated_expense.date, "America/Chicago")
            assert updated_date_browser_tz.date() == date(2024, 1, 14), (
                f"Date changed! Expected January 14, got {updated_date_browser_tz.date()}. "
                f"UTC date: {updated_expense.date.date()}, UTC datetime: {updated_expense.date}"
            )

    def test_date_preservation_when_editing_expense_pst(
        self, app, test_expense, test_restaurant, test_category
    ) -> None:
        """Test date preservation when editing expense in PST timezone."""
        from app.expenses.forms import ExpenseForm
        from app.expenses.models import Expense
        from app.extensions import db

        with app.app_context():
            # Create an expense with a specific date/time in UTC
            # July 23, 2024 18:00:00 UTC = July 23, 2024 11:00:00 PST
            original_utc_datetime = datetime(2024, 7, 23, 18, 0, 0, tzinfo=UTC)
            expense = Expense(
                amount=Decimal("100.00"),
                date=original_utc_datetime,
                notes="PST test expense",
                user_id=test_expense.user_id,
                restaurant_id=test_restaurant.id,
                category_id=test_category.id,
            )
            db.session.add(expense)
            db.session.commit()
            db.session.refresh(expense)

            # Create a form with the same date
            form = ExpenseForm()
            form.date.data = date(2024, 7, 23)  # Same date as original
            form.time.data = None  # No time specified
            form.amount.data = Decimal("100.00")
            form.notes.data = "Updated expense"
            form.restaurant_id.data = test_restaurant.id
            form.category_id.data = test_category.id
            form.meal_type.data = None
            form.order_type.data = None
            form.party_size.data = None
            form.tags.data = ""

            # Mock browser timezone as PST
            with patch("app.utils.timezone_utils.get_browser_timezone", return_value="America/Los_Angeles"):
                with patch("app.utils.timezone_utils.normalize_timezone", return_value="America/Los_Angeles"):
                    updated_expense, error = update_expense(expense, form)

            assert error is None, f"Update failed with error: {error}"
            assert updated_expense is not None

            # Verify the date is preserved correctly
            from app.utils.timezone_utils import convert_to_browser_timezone

            updated_date_browser_tz = convert_to_browser_timezone(updated_expense.date, "America/Los_Angeles")
            assert updated_date_browser_tz.date() == date(2024, 7, 23), (
                f"Date changed! Expected July 23, got {updated_date_browser_tz.date()}. "
                f"UTC date: {updated_expense.date.date()}, UTC datetime: {updated_expense.date}"
            )

    def test_get_receipt_reconciliation_marks_reconciled_records(
        self, app, session, test_user, test_restaurant, test_category, tmp_path
    ) -> None:
        """Test reconciliation rows when storage, receipt rows, and expense links align."""
        with app.app_context():
            app.config["UPLOAD_FOLDER"] = str(tmp_path)
            receipt_path = "local-receipt.png"
            (Path(tmp_path) / receipt_path).write_bytes(b"receipt")

            expense = Expense(
                amount=Decimal("23.45"),
                date=datetime.now(UTC),
                notes="Reconciled receipt",
                user_id=test_user.id,
                restaurant_id=test_restaurant.id,
                category_id=test_category.id,
                receipt_image=receipt_path,
            )
            session.add(expense)
            session.commit()
            session.refresh(expense)

            receipt = Receipt(
                user_id=test_user.id,
                expense_id=expense.id,
                file_uri=receipt_path,
                ocr_total=Decimal("23.45"),
            )
            session.add(receipt)
            session.commit()

            rows, summary = get_receipt_reconciliation(test_user.id)

            assert summary["total_receipts"] == 1
            assert summary["reconciled"] == 1
            assert len(rows) == 1
            assert rows[0]["status"] == "reconciled"
            assert rows[0]["storage_exists"] is True
            assert rows[0]["linked_expense_ids"] == [expense.id]
            assert rows[0]["receipt_row_ids"] == [receipt.id]

    def test_get_receipt_reconciliation_flags_missing_db_row(
        self, app, session, test_user, test_expense, tmp_path
    ) -> None:
        """Test reconciliation rows when an expense image exists without a structured receipt row."""
        from app.extensions import db

        with app.app_context():
            app.config["UPLOAD_FOLDER"] = str(tmp_path)
            expense = db.session.get(Expense, test_expense.id)
            assert expense is not None
            expense.receipt_image = "missing-row.png"
            db.session.commit()

            rows, summary = get_receipt_reconciliation(test_user.id)

            assert summary["missing_receipt_row"] == 1
            assert len(rows) == 1
            assert rows[0]["status"] == "missing_receipt_row"
            assert "Missing receipt DB row" in rows[0]["issues"]

    def test_create_expense_creates_structured_receipt_row(
        self, app, session, test_user, test_restaurant, test_category
    ) -> None:
        """Test uploaded receipts are stored as structured Receipt rows."""
        form = MockForm(
            category_id=test_category.id,
            restaurant_id=test_restaurant.id,
            date=date(2024, 7, 23),
            time=None,
            amount=Decimal("19.50"),
            notes="Structured receipt create",
            meal_type="lunch",
            order_type=None,
            party_size=None,
            tags="[]",
        )
        receipt_file = Mock()
        receipt_file.filename = "receipt.png"

        with app.app_context():
            with patch("app.utils.timezone_utils.get_browser_timezone", return_value="UTC"):
                with patch("app.utils.timezone_utils.normalize_timezone", return_value="UTC"):
                    with patch(
                        "app.expenses.utils.save_receipt_to_storage", return_value=("receipts/create.png", None)
                    ):
                        expense, error = create_expense(test_user.id, form, receipt_file)

            assert error is None
            assert expense is not None
            assert expense.receipt_storage_path == "receipts/create.png"

            receipt = session.query(Receipt).filter_by(expense_id=expense.id, user_id=test_user.id).one()
            assert receipt.file_uri == "receipts/create.png"
            assert receipt.receipt_type == "paper"

    def test_update_expense_deletes_structured_receipt_row(
        self, app, session, test_user, test_expense, test_restaurant, test_category
    ) -> None:
        """Test deleting a receipt removes the structured Receipt row as well."""
        with app.app_context():
            test_expense.receipt_image = "receipts/existing.png"
            receipt = Receipt(
                user_id=test_user.id,
                expense_id=test_expense.id,
                restaurant_id=test_restaurant.id,
                file_uri="receipts/existing.png",
                receipt_type="paper",
            )
            session.add(receipt)
            session.commit()

            form = MockForm(
                category_id=test_category.id,
                restaurant_id=test_restaurant.id,
                date=test_expense.date.date(),
                time=None,
                amount=test_expense.amount,
                notes=test_expense.notes,
                meal_type=test_expense.meal_type,
                order_type=test_expense.order_type,
                party_size=test_expense.party_size,
                tags="[]",
            )

            with patch("app.utils.timezone_utils.get_browser_timezone", return_value="UTC"):
                with patch("app.utils.timezone_utils.normalize_timezone", return_value="UTC"):
                    with patch("app.expenses.utils.delete_receipt_from_storage", return_value=None):
                        updated_expense, error = update_expense(test_expense, form, delete_receipt=True)

            assert error is None
            assert updated_expense is not None
            assert updated_expense.receipt_storage_path is None
            assert session.query(Receipt).filter_by(expense_id=test_expense.id, user_id=test_user.id).count() == 0
