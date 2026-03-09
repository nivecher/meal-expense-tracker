"""Tests for admin user backup export/import helpers."""

from datetime import UTC, date, datetime
from decimal import Decimal
import io
import json
import uuid

import pytest

from app.admin.backup_service import export_user_backup, import_user_backup
from app.auth.models import User
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.merchants.models import Merchant
from app.receipts.models import Receipt
from app.restaurants.models import Restaurant
from app.visits.models import Visit


def _build_user_backup_fixture(session, suffix: str) -> User:
    user = User(
        username=f"backup_{suffix}",
        email=f"backup_{suffix}@example.com",
        first_name="Backup",
        last_name="User",
        display_name="Backup User",
        bio="Round-trip backup test",
        phone="555-0101",
        timezone="America/Chicago",
        advanced_features_enabled=True,
    )
    user.set_password("password123")
    session.add(user)
    session.flush()

    merchant = Merchant(name=f"Merchant {suffix}", website=f"https://merchant-{suffix}.example.com")
    session.add(merchant)
    session.flush()

    category = Category(
        name=f"Category {suffix}",
        description="Test category",
        color="#123456",
        icon="fa-utensils",
        is_default=False,
        user_id=user.id,
    )
    tag = Tag(
        name=f"Tag-{suffix}",
        color="#abcdef",
        description="Test tag",
        user_id=user.id,
    )
    restaurant = Restaurant(
        name=f"Restaurant {suffix}",
        location_name="Downtown",
        city="Chicago",
        state="IL",
        country="United States",
        cuisine="American",
        service_level="casual_dining",
        user_id=user.id,
        merchant_id=merchant.id,
    )
    session.add_all([category, tag, restaurant])
    session.flush()

    visit = Visit(
        restaurant_id=restaurant.id,
        user_id=user.id,
        datetime_start=datetime(2025, 1, 10, 18, 30, tzinfo=UTC),
        datetime_end=datetime(2025, 1, 10, 19, 15, tzinfo=UTC),
        visit_type="dine_in",
        notes="Visit notes",
    )
    session.add(visit)
    session.flush()

    expense = Expense(
        amount=Decimal("42.50"),
        notes="Expense notes",
        meal_type="dinner",
        order_type="dine_in",
        party_size=2,
        date=datetime(2025, 1, 10, 18, 45, tzinfo=UTC),
        cleared_date=date(2025, 1, 11),
        receipt_image="receipts/source.png",
        receipt_verified=True,
        user_id=user.id,
        restaurant_id=restaurant.id,
        category_id=category.id,
        visit_id=visit.id,
    )
    session.add(expense)
    session.flush()

    expense_tag = ExpenseTag(expense_id=expense.id, tag_id=tag.id, added_by=user.id)
    receipt = Receipt(
        expense_id=expense.id,
        restaurant_id=restaurant.id,
        visit_id=visit.id,
        user_id=user.id,
        file_uri="s3://bucket/receipt.png",
        receipt_type="paper",
        ocr_total=Decimal("42.50"),
        ocr_tax=Decimal("3.50"),
        ocr_tip=Decimal("8.00"),
        ocr_confidence=Decimal("0.9876"),
    )
    session.add_all([expense_tag, receipt])
    session.commit()
    session.refresh(user)
    return user


def _advance_user_identity(session, suffix: str) -> None:
    filler = User(
        username=f"filler_{suffix}",
        email=f"filler_{suffix}@example.com",
    )
    filler.set_password("password123")
    session.add(filler)
    session.commit()


class TestBackupService:
    def test_export_import_round_trip(self, session) -> None:
        source_user = _build_user_backup_fixture(session, uuid.uuid4().hex[:8])

        payload = export_user_backup(source_user, exported_by=source_user)
        json.dumps(payload)

        session.delete(source_user)
        session.commit()
        _advance_user_identity(session, uuid.uuid4().hex[:8])

        restored_user = import_user_backup(payload)
        session.commit()
        session.refresh(restored_user)

        assert restored_user.username == payload["user"]["username"]
        assert restored_user.email == payload["user"]["email"]
        assert restored_user.check_password("password123") is True
        assert restored_user.categories.count() == 1  # type: ignore[call-arg]
        assert restored_user.tags.count() == 1  # type: ignore[call-arg]
        assert restored_user.restaurants.count() == 1  # type: ignore[call-arg]
        assert restored_user.visits.count() == 1  # type: ignore[call-arg]
        assert restored_user.expenses.count() == 1  # type: ignore[call-arg]
        assert restored_user.receipts.count() == 1  # type: ignore[call-arg]

        restored_expense = restored_user.expenses.first()
        assert restored_expense is not None
        assert restored_expense.amount == Decimal("42.50")
        assert restored_expense.cleared_date == date(2025, 1, 11)
        assert restored_expense.restaurant is not None
        assert restored_expense.restaurant.merchant is not None
        assert restored_expense.restaurant.merchant.name.startswith("Merchant ")
        assert [tag.name for tag in restored_expense.tags] == [payload["tags"][0]["name"]]

    def test_import_requires_replace_existing_for_conflicts(self, session) -> None:
        source_user = _build_user_backup_fixture(session, uuid.uuid4().hex[:8])
        payload = export_user_backup(source_user, exported_by=source_user)

        with pytest.raises(ValueError, match="already exists"):
            import_user_backup(payload)


class TestBackupRoutes:
    def test_users_page_renders_with_per_page_filter(self, client, auth, session) -> None:
        admin = User(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            is_admin=True,
        )
        admin.set_password("password123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        auth.login(admin.username, "password123")
        response = client.get("/admin/users?per_page=20")

        assert response.status_code == 200
        assert b"Per Page" in response.data

    def test_export_route_returns_attachment(self, client, auth, session) -> None:
        admin = User(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            is_admin=True,
        )
        admin.set_password("password123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        backup_user = _build_user_backup_fixture(session, uuid.uuid4().hex[:8])

        auth.login(admin.username, "password123")
        response = client.get(f"/admin/users/{backup_user.id}/export")

        assert response.status_code == 200
        assert response.mimetype == "application/json"
        assert "attachment; filename=" in response.headers["Content-Disposition"]

        payload = response.get_json()
        assert payload["user"]["username"] == backup_user.username
        assert payload["counts"]["expenses"] == 1
        assert payload["expenses"][0]["cleared_date"] == "2025-01-11"

    def test_import_route_restores_backup(self, client, auth, session) -> None:
        admin = User(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            is_admin=True,
        )
        admin.set_password("password123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        source_user = _build_user_backup_fixture(session, uuid.uuid4().hex[:8])
        payload = export_user_backup(source_user, exported_by=admin)

        session.delete(source_user)
        session.commit()
        _advance_user_identity(session, uuid.uuid4().hex[:8])

        auth.login(admin.username, "password123")
        response = client.post(
            "/admin/users/import",
            data={
                "backup_file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "backup.json"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302

        restored = User.query.filter_by(username=payload["user"]["username"]).first()
        assert restored is not None
        assert restored.expenses.count() == 1  # type: ignore[call-arg]
        assert restored.restaurants.count() == 1  # type: ignore[call-arg]
        assert restored.receipts.count() == 1  # type: ignore[call-arg]

    def test_import_route_can_create_new_user_from_backup(self, client, auth, session) -> None:
        admin = User(
            username=f"admin_{uuid.uuid4().hex[:8]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            is_admin=True,
        )
        admin.set_password("password123")
        session.add(admin)
        session.commit()
        session.refresh(admin)

        source_user = _build_user_backup_fixture(session, uuid.uuid4().hex[:8])
        payload = export_user_backup(source_user, exported_by=admin)

        auth.login(admin.username, "password123")
        new_username = f"imported_{uuid.uuid4().hex[:8]}"
        new_email = f"{new_username}@example.com"
        response = client.post(
            "/admin/users/import",
            data={
                "import_mode": "create_new",
                "new_username": new_username,
                "new_email": new_email,
                "new_password": "newpass123",
                "activate_new_user": "on",
                "preserve_advanced_features": "on",
                "backup_file": (io.BytesIO(json.dumps(payload).encode("utf-8")), "backup.json"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert response.status_code == 302

        cloned_user = User.query.filter_by(username=new_username).first()
        assert cloned_user is not None
        assert cloned_user.email == new_email
        assert cloned_user.check_password("newpass123") is True
        assert cloned_user.expenses.count() == 1  # type: ignore[call-arg]
        assert cloned_user.restaurants.count() == 1  # type: ignore[call-arg]
        assert cloned_user.receipts.count() == 1  # type: ignore[call-arg]
