"""Service layer for merchant-related operations."""

from typing import Any, List, Optional

from sqlalchemy import func, select

from app.extensions import db
from app.merchants.models import Merchant
from app.restaurants.models import Restaurant
from app.utils.url_utils import strip_url_query_params

MERCHANT_CATEGORIES = [
    "fast_food",
    "casual_dining",
    "fine_dining",
    "coffee_shop",
    "dessert_shop",
    "bar",
    "cafe",
    "bakery",
    "delivery",
    "other",
]


def get_merchant_categories() -> list[str]:
    """Return the list of available merchant categories."""
    return MERCHANT_CATEGORIES


def get_merchants(user_id: int, filters: dict[str, Any] | None = None) -> list[Merchant]:
    """Get merchants for a user with optional filtering.

    Args:
        user_id: The ID of the user
        filters: Optional filters (search, category)

    Returns:
        List of merchants
    """
    filters = filters or {}

    # Build query - merchants are global entities and should be available
    # in picklists/autocomplete even before a restaurant links to them.
    # user_id is kept in the signature for backward compatibility.
    stmt = select(Merchant)

    # Search filter
    search = filters.get("search", "").strip()
    if search:
        stmt = stmt.filter(Merchant.name.ilike(f"%{search}%"))

    # Category filter
    category = filters.get("category")
    if category:
        stmt = stmt.filter(Merchant.category == category)

    # Order by name
    stmt = stmt.order_by(Merchant.name.asc())

    return list(db.session.execute(stmt).scalars().all())


def get_merchants_with_stats(user_id: int, filters: dict[str, Any] | None = None) -> tuple[list[Merchant], dict]:
    """Get merchants with restaurant counts.

    Args:
        user_id: The ID of the user
        filters: Optional filters

    Returns:
        Tuple of (merchants, stats dict)
    """
    filters = filters or {}

    # Get merchants with restaurant counts
    stmt = (
        select(
            Merchant,
            func.count(Restaurant.id).label("restaurant_count"),
        )
        .outerjoin(Restaurant, (Merchant.id == Restaurant.merchant_id) & (Restaurant.user_id == user_id))
        .group_by(Merchant.id)
    )

    # Search filter
    search = filters.get("search", "").strip()
    if search:
        stmt = stmt.filter(Merchant.name.ilike(f"%{search}%"))

    # Category filter
    category = filters.get("category")
    if category:
        stmt = stmt.filter(Merchant.category == category)

    # Order by restaurant count descending, then by name
    stmt = stmt.order_by(func.count(Restaurant.id).desc(), Merchant.name.asc())

    results = db.session.execute(stmt).all()

    merchants = []
    merchant_data = {}
    for merchant, count in results:
        merchants.append(merchant)
        merchant_data[merchant.id] = {"restaurant_count": count}

    stats = {
        "total_merchants": len(merchants),
        "total_restaurants": sum(count["restaurant_count"] for count in merchant_data.values()),
    }

    return merchants, {"merchants": merchants, "merchant_data": merchant_data, "stats": stats}


def get_restaurants_for_merchant(user_id: int, merchant_id: int) -> list[Restaurant]:
    """Get restaurants linked to a merchant for a user."""
    stmt = (
        select(Restaurant)
        .where(Restaurant.user_id == user_id, Restaurant.merchant_id == merchant_id)
        .order_by(Restaurant.name.asc())
    )
    return list(db.session.execute(stmt).scalars().all())


def get_merchant(merchant_id: int) -> Merchant | None:
    """Get a merchant by ID.

    Args:
        merchant_id: The merchant ID

    Returns:
        Merchant or None if not found
    """
    return db.session.get(Merchant, merchant_id)


def get_merchant_by_name(name: str) -> Merchant | None:
    """Get a merchant by name (case-insensitive).

    Args:
        name: The merchant name

    Returns:
        Merchant or None if not found
    """
    return db.session.execute(select(Merchant).filter(func.lower(Merchant.name) == name.lower())).scalar_one_or_none()


def create_merchant(user_id: int, data: dict[str, Any]) -> Merchant:
    """Create a new merchant.

    Args:
        user_id: The ID of the user creating the merchant
        data: Merchant data (name, category)

    Returns:
        Created merchant
    """
    website = data.get("website")
    merchant = Merchant(
        name=data.get("name", "").strip(),
        short_name=(data.get("short_name") or "").strip() or None,
        website=strip_url_query_params(website) if website else None,
        category=data.get("category"),
    )

    db.session.add(merchant)
    db.session.commit()

    return merchant


def update_merchant(merchant_id: int, data: dict[str, Any]) -> Merchant | None:
    """Update a merchant.

    Args:
        merchant_id: The merchant ID
        data: Updated merchant data

    Returns:
        Updated merchant or None if not found
    """
    merchant = get_merchant(merchant_id)
    if not merchant:
        return None

    if "name" in data:
        merchant.name = data["name"].strip()
    if "short_name" in data:
        short_name = data["short_name"]
        merchant.short_name = short_name.strip() if isinstance(short_name, str) and short_name.strip() else None
    if "website" in data:
        website = data["website"]
        merchant.website = strip_url_query_params(website) if website else None
    if "category" in data:
        merchant.category = data["category"]

    db.session.commit()
    return merchant


def delete_merchant(merchant_id: int) -> bool:
    """Delete a merchant.

    Args:
        merchant_id: The merchant ID

    Returns:
        True if deleted, False if not found
    """
    merchant = get_merchant(merchant_id)
    if not merchant:
        return False

    db.session.delete(merchant)
    db.session.commit()
    return True


def export_merchants_for_user(user_id: int, merchant_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """Get merchants for export with per-user restaurant counts.

    Args:
        user_id: Current user ID used for restaurant count scoping
        merchant_ids: Optional list of merchant IDs to export

    Returns:
        List of merchant export rows
    """
    if merchant_ids is not None and not merchant_ids:
        return []

    stmt = (
        select(
            Merchant,
            func.count(Restaurant.id).label("restaurant_count"),
        )
        .outerjoin(Restaurant, (Merchant.id == Restaurant.merchant_id) & (Restaurant.user_id == user_id))
        .group_by(Merchant.id)
        .order_by(Merchant.name.asc())
    )

    if merchant_ids:
        stmt = stmt.where(Merchant.id.in_(merchant_ids))

    results = db.session.execute(stmt).all()
    return [
        {
            "name": merchant.name or "",
            "short_name": merchant.short_name or "",
            "website": merchant.website or "",
            "category": merchant.category or "",
            "restaurant_count": int(restaurant_count or 0),
            "created_at": merchant.created_at.isoformat() if merchant.created_at else "",
            "updated_at": merchant.updated_at.isoformat() if merchant.updated_at else "",
        }
        for merchant, restaurant_count in results
    ]


def get_merchant_form_choices() -> list[tuple[str, str]]:
    """Get merchant choices for form dropdowns.

    Returns:
        List of (value, label) tuples
    """
    choices = [("", "-- Select Merchant --")]
    for category in MERCHANT_CATEGORIES:
        display_name = category.replace("_", " ").title()
        choices.append((category, display_name))
    return choices
