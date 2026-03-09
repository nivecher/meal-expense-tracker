"""Admin helpers for exporting and importing full user backups."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select

from app.auth.models import User
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.extensions import db
from app.merchants.models import Merchant
from app.receipts.models import Receipt
from app.restaurants.models import Restaurant
from app.visits.models import Visit

BACKUP_SCHEMA_VERSION = 1
BACKUP_KIND = "user_full_backup"
IMPORT_MODE_RESTORE = "restore"
IMPORT_MODE_REPLACE = "replace_existing"
IMPORT_MODE_CREATE_NEW = "create_new"


def _serialize_scalar(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _serialize_model(instance: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    excluded = exclude or set()
    return {
        column.name: _serialize_scalar(getattr(instance, column.name))
        for column in instance.__table__.columns
        if column.name not in excluded
    }


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError(f"Invalid datetime value: {value!r}")


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Invalid date value: {value!r}")


def _parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))


def _restore_timestamps(instance: Any, data: dict[str, Any]) -> None:
    instance.created_at = _parse_datetime(data.get("created_at"))
    instance.updated_at = _parse_datetime(data.get("updated_at"))


def export_user_backup(
    user: User,
    *,
    exported_by: User | None = None,
) -> dict[str, Any]:
    """Export a complete backup for a single user and all owned records."""
    restaurants = list(
        db.session.scalars(select(Restaurant).where(Restaurant.user_id == user.id).order_by(Restaurant.id.asc())).all()
    )
    merchant_ids = sorted({restaurant.merchant_id for restaurant in restaurants if restaurant.merchant_id is not None})
    merchants = (
        list(
            db.session.scalars(select(Merchant).where(Merchant.id.in_(merchant_ids)).order_by(Merchant.id.asc())).all()
        )
        if merchant_ids
        else []
    )
    visits = list(db.session.scalars(select(Visit).where(Visit.user_id == user.id).order_by(Visit.id.asc())).all())
    categories = list(
        db.session.scalars(select(Category).where(Category.user_id == user.id).order_by(Category.id.asc())).all()
    )
    tags = list(db.session.scalars(select(Tag).where(Tag.user_id == user.id).order_by(Tag.id.asc())).all())
    expenses = list(
        db.session.scalars(select(Expense).where(Expense.user_id == user.id).order_by(Expense.id.asc())).all()
    )
    receipts = list(
        db.session.scalars(select(Receipt).where(Receipt.user_id == user.id).order_by(Receipt.id.asc())).all()
    )
    expense_ids = [expense.id for expense in expenses]
    expense_tags = (
        ExpenseTag.query.filter(ExpenseTag.expense_id.in_(expense_ids)).order_by(ExpenseTag.id.asc()).all()
        if expense_ids
        else []
    )

    return {
        "kind": BACKUP_KIND,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "exported_by": (
            {
                "id": exported_by.id,
                "username": exported_by.username,
                "email": exported_by.email,
            }
            if exported_by is not None
            else None
        ),
        "counts": {
            "merchants": len(merchants),
            "categories": len(categories),
            "tags": len(tags),
            "restaurants": len(restaurants),
            "visits": len(visits),
            "expenses": len(expenses),
            "expense_tags": len(expense_tags),
            "receipts": len(receipts),
        },
        "user": _serialize_model(user),
        "merchants": [_serialize_model(merchant) for merchant in merchants],
        "categories": [_serialize_model(category) for category in categories],
        "tags": [_serialize_model(tag) for tag in tags],
        "restaurants": [_serialize_model(restaurant) for restaurant in restaurants],
        "visits": [_serialize_model(visit) for visit in visits],
        "expenses": [_serialize_model(expense) for expense in expenses],
        "expense_tags": [_serialize_model(expense_tag) for expense_tag in expense_tags],
        "receipts": [_serialize_model(receipt) for receipt in receipts],
    }


def _validate_backup_payload(payload: dict[str, Any]) -> None:
    if payload.get("kind") != BACKUP_KIND:
        raise ValueError("Unsupported backup type")
    if payload.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise ValueError("Unsupported backup schema version")
    user_data = payload.get("user")
    if not isinstance(user_data, dict):
        raise ValueError("Backup is missing user data")
    if not user_data.get("username") or not user_data.get("email"):
        raise ValueError("Backup user record is missing username or email")


def _find_existing_backup_user(username: str, email: str) -> list[User]:
    return list(
        db.session.scalars(
            select(User).where(or_(User.username == username, User.email == email)).order_by(User.id.asc())
        ).all()
    )


def _match_or_create_merchant(merchant_data: dict[str, Any]) -> Merchant:
    merchant = None
    merchant_name = merchant_data.get("name")
    merchant_website = merchant_data.get("website")

    if merchant_name:
        query = Merchant.query.filter(Merchant.name == merchant_name)
        if merchant_website:
            merchant = query.filter(Merchant.website == merchant_website).first()
        if merchant is None:
            merchant = query.order_by(Merchant.id.asc()).first()

    if merchant is None:
        merchant = Merchant(
            name=merchant_name,
            short_name=merchant_data.get("short_name"),
            website=merchant_website,
            description=merchant_data.get("description"),
            favicon_url=merchant_data.get("favicon_url"),
            category=merchant_data.get("category"),
            menu_focus=merchant_data.get("menu_focus"),
            cuisine=merchant_data.get("cuisine"),
            format_category=merchant_data.get("format_category"),
            service_level=merchant_data.get("service_level"),
            is_chain=bool(merchant_data.get("is_chain", False)),
        )
        db.session.add(merchant)
        db.session.flush()
        _restore_timestamps(merchant, merchant_data)

    return merchant


def import_user_backup(
    payload: dict[str, Any],
    *,
    mode: str = IMPORT_MODE_RESTORE,
    new_username: str | None = None,
    new_email: str | None = None,
    new_password_hash: str | None = None,
    is_admin: bool | None = None,
    is_active: bool | None = None,
    advanced_features_enabled: bool | None = None,
) -> User:
    """Import a complete user backup into the current database session."""
    _validate_backup_payload(payload)

    user_data = payload["user"]
    source_username = str(user_data["username"]).strip()
    source_email = str(user_data["email"]).strip()

    if mode not in {IMPORT_MODE_RESTORE, IMPORT_MODE_REPLACE, IMPORT_MODE_CREATE_NEW}:
        raise ValueError("Unsupported import mode")

    if mode == IMPORT_MODE_CREATE_NEW:
        username = (new_username or "").strip()
        email = (new_email or "").strip()
        if not username or not email:
            raise ValueError("New username and email are required when creating a new user from backup")
        existing_users = _find_existing_backup_user(username, email)
        if existing_users:
            raise ValueError("A user with the new username or email already exists")
    else:
        username = source_username
        email = source_email
        existing_users = _find_existing_backup_user(username, email)

    if mode == IMPORT_MODE_RESTORE and existing_users:
        raise ValueError("A user with the same username or email already exists")

    if mode == IMPORT_MODE_REPLACE:
        distinct_ids = {user.id for user in existing_users}
        if len(distinct_ids) > 1:
            raise ValueError("Backup matches multiple existing users; resolve the conflict manually before importing")
        for existing_user in existing_users:
            db.session.delete(existing_user)
        if existing_users:
            db.session.flush()

    merchant_map: dict[int, Merchant] = {}
    for merchant_data in payload.get("merchants", []):
        old_merchant_id = merchant_data.get("id")
        if old_merchant_id is None:
            continue
        merchant_map[int(old_merchant_id)] = _match_or_create_merchant(merchant_data)

    user = User(
        username=username,
        email=email,
        password_hash=user_data.get("password_hash") if new_password_hash is None else new_password_hash,
        is_active=bool(user_data.get("is_active", True)) if is_active is None else bool(is_active),
        is_admin=bool(user_data.get("is_admin", False)) if is_admin is None else bool(is_admin),
        advanced_features_enabled=(
            bool(user_data.get("advanced_features_enabled", False))
            if advanced_features_enabled is None
            else bool(advanced_features_enabled)
        ),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        display_name=user_data.get("display_name"),
        bio=user_data.get("bio"),
        avatar_url=user_data.get("avatar_url"),
        phone=user_data.get("phone"),
        timezone=user_data.get("timezone"),
    )
    db.session.add(user)
    db.session.flush()
    _restore_timestamps(user, user_data)

    category_map: dict[int, Category] = {}
    for category_data in payload.get("categories", []):
        category = Category(
            name=category_data["name"],
            description=category_data.get("description"),
            color=category_data.get("color") or "#6c757d",
            icon=category_data.get("icon"),
            is_default=bool(category_data.get("is_default", False)),
            user_id=user.id,
        )
        db.session.add(category)
        db.session.flush()
        _restore_timestamps(category, category_data)
        category_map[int(category_data["id"])] = category

    tag_map: dict[int, Tag] = {}
    for tag_data in payload.get("tags", []):
        tag = Tag(
            name=tag_data["name"],
            color=tag_data.get("color") or "#6c757d",
            description=tag_data.get("description"),
            user_id=user.id,
        )
        db.session.add(tag)
        db.session.flush()
        _restore_timestamps(tag, tag_data)
        tag_map[int(tag_data["id"])] = tag

    restaurant_map: dict[int, Restaurant] = {}
    for restaurant_data in payload.get("restaurants", []):
        old_merchant_id = restaurant_data.get("merchant_id")
        merchant = merchant_map.get(int(old_merchant_id)) if old_merchant_id is not None else None
        restaurant = Restaurant(
            name=restaurant_data["name"],
            location_name=restaurant_data.get("location_name"),
            type=restaurant_data.get("type"),
            located_within=restaurant_data.get("located_within"),
            description=restaurant_data.get("description"),
            address_line_1=restaurant_data.get("address_line_1"),
            address_line_2=restaurant_data.get("address_line_2"),
            city=restaurant_data.get("city"),
            state=restaurant_data.get("state"),
            postal_code=restaurant_data.get("postal_code"),
            country=restaurant_data.get("country"),
            phone=restaurant_data.get("phone"),
            website=restaurant_data.get("website"),
            email=restaurant_data.get("email"),
            google_place_id=restaurant_data.get("google_place_id"),
            cuisine=restaurant_data.get("cuisine"),
            service_level=restaurant_data.get("service_level"),
            rating=restaurant_data.get("rating"),
            price_level=restaurant_data.get("price_level"),
            primary_type=restaurant_data.get("primary_type"),
            latitude=restaurant_data.get("latitude"),
            longitude=restaurant_data.get("longitude"),
            notes=restaurant_data.get("notes"),
            user_id=user.id,
            merchant_id=merchant.id if merchant is not None else None,
        )
        db.session.add(restaurant)
        db.session.flush()
        _restore_timestamps(restaurant, restaurant_data)
        restaurant_map[int(restaurant_data["id"])] = restaurant

    visit_map: dict[int, Visit] = {}
    for visit_data in payload.get("visits", []):
        old_restaurant_id = visit_data.get("restaurant_id")
        visit_restaurant: Restaurant | None = (
            restaurant_map.get(int(old_restaurant_id)) if old_restaurant_id is not None else None
        )
        if visit_restaurant is None:
            raise ValueError("Backup visit references a missing restaurant")
        visit = Visit(
            restaurant_id=visit_restaurant.id,
            user_id=user.id,
            datetime_start=_parse_datetime(visit_data.get("datetime_start")),
            datetime_end=_parse_datetime(visit_data.get("datetime_end")),
            visit_type=visit_data.get("visit_type"),
            notes=visit_data.get("notes"),
        )
        db.session.add(visit)
        db.session.flush()
        _restore_timestamps(visit, visit_data)
        visit_map[int(visit_data["id"])] = visit

    expense_map: dict[int, Expense] = {}
    for expense_data in payload.get("expenses", []):
        old_restaurant_id = expense_data.get("restaurant_id")
        old_category_id = expense_data.get("category_id")
        old_visit_id = expense_data.get("visit_id")
        expense = Expense(
            amount=_parse_decimal(expense_data.get("amount")) or Decimal("0.00"),
            notes=expense_data.get("notes"),
            meal_type=expense_data.get("meal_type"),
            order_type=expense_data.get("order_type"),
            party_size=expense_data.get("party_size"),
            date=_parse_datetime(expense_data.get("date")),
            cleared_date=_parse_date(expense_data.get("cleared_date")),
            receipt_image=expense_data.get("receipt_image"),
            receipt_verified=bool(expense_data.get("receipt_verified", False)),
            user_id=user.id,
            restaurant_id=restaurant_map[int(old_restaurant_id)].id if old_restaurant_id is not None else None,
            category_id=category_map[int(old_category_id)].id if old_category_id is not None else None,
            visit_id=visit_map[int(old_visit_id)].id if old_visit_id is not None else None,
        )
        db.session.add(expense)
        db.session.flush()
        _restore_timestamps(expense, expense_data)
        expense_map[int(expense_data["id"])] = expense

    for expense_tag_data in payload.get("expense_tags", []):
        old_expense_id = expense_tag_data.get("expense_id")
        old_tag_id = expense_tag_data.get("tag_id")
        if old_expense_id is None or old_tag_id is None:
            raise ValueError("Backup expense tag is missing expense_id or tag_id")
        expense_tag = ExpenseTag(
            expense_id=expense_map[int(old_expense_id)].id,
            tag_id=tag_map[int(old_tag_id)].id,
            added_by=user.id,
        )
        db.session.add(expense_tag)
        db.session.flush()
        _restore_timestamps(expense_tag, expense_tag_data)

    for receipt_data in payload.get("receipts", []):
        old_expense_id = receipt_data.get("expense_id")
        old_restaurant_id = receipt_data.get("restaurant_id")
        old_visit_id = receipt_data.get("visit_id")
        receipt = Receipt(
            expense_id=expense_map[int(old_expense_id)].id if old_expense_id is not None else None,
            restaurant_id=restaurant_map[int(old_restaurant_id)].id if old_restaurant_id is not None else None,
            visit_id=visit_map[int(old_visit_id)].id if old_visit_id is not None else None,
            user_id=user.id,
            file_uri=receipt_data["file_uri"],
            receipt_type=receipt_data.get("receipt_type"),
            ocr_total=_parse_decimal(receipt_data.get("ocr_total")),
            ocr_tax=_parse_decimal(receipt_data.get("ocr_tax")),
            ocr_tip=_parse_decimal(receipt_data.get("ocr_tip")),
            ocr_confidence=_parse_decimal(receipt_data.get("ocr_confidence")),
        )
        db.session.add(receipt)
        db.session.flush()
        _restore_timestamps(receipt, receipt_data)

    db.session.flush()
    return user
