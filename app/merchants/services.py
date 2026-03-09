"""Service layer for merchant-related operations."""

import csv
from decimal import Decimal
import json
import re
from typing import Any

from sqlalchemy import distinct, func, or_, select
from sqlalchemy.sql.elements import ColumnElement
from werkzeug.datastructures import FileStorage

from app.constants.cuisines import get_cuisine_names
from app.expenses.models import Expense
from app.extensions import db
from app.merchants.models import Merchant
from app.restaurants.models import Restaurant
from app.utils.url_utils import (
    canonicalize_website_for_storage,
    extract_base_website_url,
    extract_comparable_website_host,
    validate_favicon_url,
)

MERCHANT_CATEGORIES = [
    "standard_restaurant",
    "fast_food_unit",
    "drive_in",
    "diner",
    "buffet_cafeteria",
    "deli_cafe",
    "bakery_specialty",
    "convenience_gas_station",
    "mall_food_court",
    "food_truck_mobile",
    "ghost_kitchen",
    "kiosk_pop_up",
    "dinner_theater_cinema",
    "pub_tavern_bar",
    "clubhouse_private_venue",
    "other",
]

MERCHANT_SERVICE_LEVELS = [
    "fine_dining",
    "casual_dining",
    "fast_casual",
    "quick_service",
]

MERCHANT_FORMAT_CATEGORY_LABELS = {
    "standard_restaurant": "Standard Restaurant",
    "fast_food_unit": "Fast Food Unit",
    "drive_in": "Drive-In",
    "diner": "Diner",
    "buffet_cafeteria": "Buffet / Cafeteria",
    "deli_cafe": "Deli / Cafe",
    "cafe_bakery": "Deli / Cafe",
    "convenience_gas_station": "Convenience / Gas Station",
    "convenience_retail": "Convenience / Gas Station",
    "bakery_specialty": "Bakery / Specialty",
    "mall_food_court": "Mall / Food Court",
    "food_truck_mobile": "Food Truck / Mobile",
    "ghost_kitchen": "Ghost Kitchen",
    "kiosk_pop_up": "Kiosk / Pop-Up",
    "dinner_theater_cinema": "Dinner Theater / Cinema",
    "pub_tavern_bar": "Pub / Tavern / Bar",
    "pub_tavern": "Pub / Tavern / Bar",
    "clubhouse_private_venue": "Clubhouse / Private",
    "other": "Other",
}

MERCHANT_FORMAT_CATEGORY_GROUPS = [
    {
        "label": "Traditional Physical Formats",
        "options": [
            {
                "value": "standard_restaurant",
                "label": "Standard Restaurant",
                "definition": "A permanent building designed for indoor, table-based dining (e.g., Chili's, Texas Roadhouse).",
            },
            {
                "value": "fast_food_unit",
                "label": "Fast Food Unit",
                "definition": "A high-efficiency building optimized for speed, featuring a walk-up counter and a drive-through (e.g., McDonald's, Chick-fil-A).",
            },
            {
                "value": "drive_in",
                "label": "Drive-In",
                "definition": "A specialized format where customers park in designated stalls and are served in their vehicles (e.g., Sonic Drive-In).",
            },
            {
                "value": "diner",
                "label": "Diner",
                "definition": "Small-to-medium standalone buildings with counter/booth seating and an all-day comfort menu (e.g., Waffle House, IHOP).",
            },
            {
                "value": "buffet_cafeteria",
                "label": "Buffet / Cafeteria",
                "definition": "A facility designed for self-service or line-service where customers move through a queue (e.g., Golden Corral, Spring Creek Barbeque).",
            },
        ],
    },
    {
        "label": "Retail & Specialty Formats",
        "options": [
            {
                "value": "deli_cafe",
                "label": "Deli / Cafe",
                "definition": "Smaller footprints centered on display cases and high-volume beverage or cold-prep service (e.g., Jason's Deli, Starbucks).",
            },
            {
                "value": "bakery_specialty",
                "label": "Bakery / Specialty",
                "definition": "A retail-heavy format focused on the production and sale of specific baked or frozen goods (e.g., Shipley Do-Nuts, Ben & Jerry's).",
            },
            {
                "value": "convenience_gas_station",
                "label": "Convenience / Gas Station",
                "definition": "Food operations integrated into a retail fueling center or convenience store (e.g., Fuel City, 7-Eleven).",
            },
            {
                "value": "mall_food_court",
                "label": "Mall / Food Court",
                "definition": "A counter-only unit located within a shared dining area of a larger retail complex (e.g., Panda Express).",
            },
        ],
    },
    {
        "label": "Mobile & Digital Formats",
        "options": [
            {
                "value": "food_truck_mobile",
                "label": "Food Truck / Mobile",
                "definition": "A fully functional kitchen on wheels that operates from varying locations (e.g., Tacos Los Compadres).",
            },
            {
                "value": "ghost_kitchen",
                "label": "Ghost Kitchen",
                "definition": "A professional cooking facility with no customer-facing area, used exclusively for delivery-app orders.",
            },
            {
                "value": "kiosk_pop_up",
                "label": "Kiosk / Pop-Up",
                "definition": "An ultra-small or temporary footprint (stand/cart) in high-traffic hubs (e.g., Dutch Bros, Auntie Anne's).",
            },
        ],
    },
    {
        "label": "Leisure & Specialty Formats",
        "options": [
            {
                "value": "dinner_theater_cinema",
                "label": "Dinner Theater / Cinema",
                "definition": "A hybrid format where full-service dining is integrated into an entertainment venue (e.g., Star Cinema Grill).",
            },
            {
                "value": "pub_tavern_bar",
                "label": "Pub / Tavern / Bar",
                "definition": "A beverage-forward environment where the bar is the primary architectural feature (e.g., BJ's, Buffalo Wild Wings).",
            },
            {
                "value": "clubhouse_private_venue",
                "label": "Clubhouse / Private",
                "definition": "Dining facilities located within private clubs or golf courses with restricted access (e.g., Woodbridge Golf Club).",
            },
        ],
    },
]

MERCHANT_SERVICE_LEVEL_LABELS = {
    "fine_dining": "Fine Dining",
    "casual_dining": "Casual Dining",
    "fast_casual": "Fast Casual",
    "quick_service": "Quick Service",
}

_GENERIC_MERCHANT_SUFFIXES = {
    "bar",
    "bars",
    "cafe",
    "coffee",
    "coffeehouse",
    "diner",
    "eatery",
    "fish",
    "grill",
    "house",
    "kitchen",
    "restaurant",
    "saloon",
    "shop",
}

_RESTAURANT_TYPE_TO_MERCHANT_CATEGORY: dict[str, str] = {
    "restaurant": "standard_restaurant",
    "restaurants": "standard_restaurant",
    "fast_food_restaurant": "fast_food_unit",
    "drive_in": "drive_in",
    "drive_through": "fast_food_unit",
    "diner": "diner",
    "coffee_shop": "deli_cafe",
    "cafe": "deli_cafe",
    "bakery": "bakery_specialty",
    "donut_shop": "bakery_specialty",
    "dessert_shop": "bakery_specialty",
    "ice_cream_shop": "bakery_specialty",
    "sandwich_shop": "deli_cafe",
    "food_court": "mall_food_court",
    "mall_food_court": "mall_food_court",
    "convenience_store": "convenience_gas_station",
    "gas_station": "convenience_gas_station",
    "food_truck": "food_truck_mobile",
    "food_trailer": "food_truck_mobile",
    "ghost_kitchen": "ghost_kitchen",
    "kiosk": "kiosk_pop_up",
    "pop_up": "kiosk_pop_up",
    "movie_theater": "dinner_theater_cinema",
    "cinema": "dinner_theater_cinema",
    "bar": "pub_tavern_bar",
    "pub": "pub_tavern_bar",
    "wine_bar": "pub_tavern_bar",
    "country_club": "clubhouse_private_venue",
    "golf_club": "clubhouse_private_venue",
}


def get_merchant_categories() -> list[str]:
    """Return the list of available merchant format categories."""
    return MERCHANT_CATEGORIES


def get_merchant_format_categories() -> list[str]:
    """Return the list of available merchant format categories."""
    return MERCHANT_CATEGORIES


def get_merchant_format_category_groups() -> list[dict[str, Any]]:
    """Return grouped merchant format categories with labels and definitions."""
    return MERCHANT_FORMAT_CATEGORY_GROUPS


def get_merchant_service_levels() -> list[str]:
    """Return the list of available merchant service levels."""
    return MERCHANT_SERVICE_LEVELS


def get_merchant_format_category_label(value: str | None) -> str:
    """Return a display label for a merchant format category."""
    if not value:
        return ""
    return MERCHANT_FORMAT_CATEGORY_LABELS.get(value, value.replace("_", " ").title())


def get_merchant_service_level_label(value: str | None) -> str:
    """Return a display label for a merchant service level."""
    if not value:
        return ""
    return MERCHANT_SERVICE_LEVEL_LABELS.get(value, value.replace("_", " ").title())


def infer_merchant_category_from_restaurant(restaurant: Restaurant) -> str:
    """Infer a merchant format category from restaurant fields for form prefills."""
    candidates = [
        restaurant.type,
        restaurant.primary_type,
    ]
    for value in candidates:
        normalized = (value or "").strip().lower().replace(" ", "_")
        if normalized in _RESTAURANT_TYPE_TO_MERCHANT_CATEGORY:
            return _RESTAURANT_TYPE_TO_MERCHANT_CATEGORY[normalized]
        if normalized in MERCHANT_CATEGORIES:
            return normalized

    service_level = (restaurant.service_level or "").strip().lower().replace(" ", "_")
    if service_level == "quick_service":
        return "fast_food_unit"
    if service_level == "fast_casual":
        restaurant_type = (restaurant.type or "").strip().lower().replace(" ", "_")
        if restaurant_type in {"coffee_shop", "cafe", "sandwich_shop"}:
            return "deli_cafe"
        if restaurant_type in {"bakery", "donut_shop", "dessert_shop", "ice_cream_shop"}:
            return "bakery_specialty"
        return "standard_restaurant"
    if service_level in {"casual_dining", "fine_dining"}:
        return "standard_restaurant"
    return "other"


def infer_merchant_format_category_from_restaurant(restaurant: Restaurant) -> str:
    """Infer a merchant format category from restaurant fields for form prefills."""
    return infer_merchant_category_from_restaurant(restaurant)


def infer_merchant_service_level_from_restaurant(restaurant: Restaurant) -> str:
    """Infer a merchant service level from restaurant fields for form prefills."""
    service_level = (restaurant.service_level or "").strip().lower().replace(" ", "_")
    if service_level in MERCHANT_SERVICE_LEVELS:
        return service_level
    return ""


def infer_merchant_cuisine_from_restaurant(restaurant: Restaurant) -> str:
    """Infer merchant cuisine from restaurant cuisine when present."""
    cuisine = (restaurant.cuisine or "").strip()
    return cuisine if cuisine in get_cuisine_names() else cuisine


def _to_title_case(value: str) -> str:
    """Convert text to display-friendly title case without mangling apostrophes."""
    words: list[str] = []
    for word in value.split():
        parts = word.split("-")
        normalized_parts = []
        for part in parts:
            if not part:
                continue
            normalized_parts.append(part[:1].upper() + part[1:].lower())
        words.append("-".join(normalized_parts))
    return " ".join(words)


def derive_short_name_from_merchant_name(name: str) -> str:
    """Derive a concise merchant short name from the merchant name."""
    cleaned_name = (name or "").split(" - ", 1)[0].strip()
    if not cleaned_name:
        return ""

    words = [word for word in cleaned_name.split() if word]
    if not words:
        return ""

    first_word = words[0]
    if "'" in first_word:
        return _to_title_case(first_word)

    for index, word in enumerate(words):
        normalized = re.sub(r"[^a-z0-9']", "", word.lower())
        if normalized in _GENERIC_MERCHANT_SUFFIXES and index > 0:
            return _to_title_case(" ".join(words[:index]))

    if len(words) <= 2:
        return _to_title_case(" ".join(words))

    return _to_title_case(words[0])


def derive_short_name_from_merchant_name_and_website(name: str, website: str | None = None) -> str:
    """Derive a concise merchant short name, preferring a website-derived subset when available."""
    cleaned_name = (name or "").split(" - ", 1)[0].strip()
    if not cleaned_name:
        return ""

    website_host = extract_comparable_website_host(website)
    website_label = website_host.split(".", 1)[0] if website_host else ""
    normalized_website_label = re.sub(r"[^a-z0-9]+", "", website_label.lower())

    words = [word for word in cleaned_name.split() if word]
    if normalized_website_label and words:
        best_match = ""
        for start_index in range(len(words)):
            for end_index in range(start_index + 1, len(words) + 1):
                candidate_words = words[start_index:end_index]
                candidate_normalized = re.sub(r"[^a-z0-9]+", "", "".join(candidate_words).lower())
                if candidate_normalized != normalized_website_label:
                    continue

                candidate_text = " ".join(candidate_words)
                if len(candidate_text) > len(best_match):
                    best_match = candidate_text

        if best_match:
            return best_match

    return derive_short_name_from_merchant_name(cleaned_name)


def normalize_short_name(name: str | None, short_name: str | None) -> str | None:
    """Normalize short_name and drop it when it matches the merchant name."""

    normalized_name = (name or "").strip()
    normalized_short_name = (short_name or "").strip()
    if not normalized_short_name:
        return None

    comparable_name = " ".join(normalized_name.split()).casefold()
    comparable_short_name = " ".join(normalized_short_name.split()).casefold()
    if comparable_name and comparable_name == comparable_short_name:
        return None

    return normalized_short_name


def get_create_merchant_prefill_for_restaurant(restaurant: Restaurant) -> dict[str, str]:
    """Build merchant form defaults from a restaurant record."""
    restaurant_name = (restaurant.name or "").strip()
    merchant_name = restaurant_name.split(" - ", 1)[0].strip() if restaurant_name else ""
    base_website = extract_base_website_url(restaurant.website)
    short_name = normalize_short_name(
        merchant_name,
        derive_short_name_from_merchant_name_and_website(merchant_name, base_website or restaurant.website),
    )

    return {
        "name": merchant_name or restaurant.display_name or restaurant.name or "",
        "short_name": short_name or "",
        "website": base_website,
        "description": "",
        "category": infer_merchant_category_from_restaurant(restaurant),
        "menu_focus": "",
        "cuisine": infer_merchant_cuisine_from_restaurant(restaurant),
        "service_level": infer_merchant_service_level_from_restaurant(restaurant),
    }


def merchant_is_chain(merchant: Merchant | None) -> bool:
    """Return whether a merchant should be treated as a chain."""
    return bool(merchant and merchant.is_chain)


def merchant_has_chain_suggestion(merchant: Merchant | None, restaurant_count: int | None = None) -> bool:
    """Return whether merchant should be suggested as a chain based on linked location count."""
    if not merchant or merchant.is_chain:
        return False
    return int(restaurant_count or 0) > 1


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
        stmt = stmt.filter(
            or_(
                Merchant.name.ilike(f"%{search}%"),
                Merchant.short_name.ilike(f"%{search}%"),
                Merchant.website.ilike(f"%{search}%"),
                Merchant.description.ilike(f"%{search}%"),
                Merchant.cuisine.ilike(f"%{search}%"),
                Merchant.menu_focus.ilike(f"%{search}%"),
                func.replace(Merchant.service_level, "_", " ").ilike(f"%{search}%"),
                func.replace(Merchant.category, "_", " ").ilike(f"%{search}%"),
            )
        )

    # Format filter
    category = filters.get("category")
    if category:
        stmt = stmt.filter(Merchant.category == category)
    service_level = filters.get("service_level")
    if service_level:
        stmt = stmt.filter(Merchant.service_level == service_level)
    cuisine = filters.get("cuisine")
    if cuisine:
        stmt = stmt.filter(Merchant.cuisine == cuisine)
    menu_focus = filters.get("menu_focus")
    if menu_focus:
        stmt = stmt.filter(Merchant.menu_focus == menu_focus)
    is_chain = filters.get("is_chain")
    if is_chain:
        stmt = stmt.filter(Merchant.is_chain == (str(is_chain).lower() == "true"))
    has_description = filters.get("has_description")
    if has_description == "yes":
        stmt = stmt.filter(Merchant.description.isnot(None), Merchant.description != "")
    elif has_description == "no":
        stmt = stmt.filter(or_(Merchant.description.is_(None), Merchant.description == ""))

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
        stmt = stmt.filter(
            or_(
                Merchant.name.ilike(f"%{search}%"),
                Merchant.short_name.ilike(f"%{search}%"),
                Merchant.website.ilike(f"%{search}%"),
                Merchant.description.ilike(f"%{search}%"),
                Merchant.cuisine.ilike(f"%{search}%"),
                Merchant.menu_focus.ilike(f"%{search}%"),
                func.replace(Merchant.service_level, "_", " ").ilike(f"%{search}%"),
                func.replace(Merchant.category, "_", " ").ilike(f"%{search}%"),
            )
        )

    # Format and service-level filters
    category = filters.get("category")
    if category:
        stmt = stmt.filter(Merchant.category == category)
    service_level = filters.get("service_level")
    if service_level:
        stmt = stmt.filter(Merchant.service_level == service_level)
    cuisine = filters.get("cuisine")
    if cuisine:
        stmt = stmt.filter(Merchant.cuisine == cuisine)
    menu_focus = filters.get("menu_focus")
    if menu_focus:
        stmt = stmt.filter(Merchant.menu_focus == menu_focus)
    is_chain = filters.get("is_chain")
    if is_chain:
        stmt = stmt.filter(Merchant.is_chain == (str(is_chain).lower() == "true"))
    has_description = filters.get("has_description")
    if has_description == "yes":
        stmt = stmt.filter(Merchant.description.isnot(None), Merchant.description != "")
    elif has_description == "no":
        stmt = stmt.filter(or_(Merchant.description.is_(None), Merchant.description == ""))
    restaurant_status = filters.get("restaurant_status")
    if restaurant_status == "without_restaurants":
        stmt = stmt.having(func.count(Restaurant.id) == 0)
    elif restaurant_status == "with_restaurants":
        stmt = stmt.having(func.count(Restaurant.id) > 0)

    # Order by name by default for consistent list display
    stmt = stmt.order_by(Merchant.name.asc())

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


def get_merchants_with_detailed_stats(
    user_id: int | None, filters: dict[str, Any] | None = None
) -> tuple[list[Merchant], dict]:
    """Get merchants with restaurant count, expense count, and total amount.

    When user_id is set, stats are scoped to that user's restaurants and expenses.
    When user_id is None, stats are across all users.

    Returns:
        Tuple of (merchants, data dict with merchant_data and stats)
    """
    filters = filters or {}

    if user_id is not None:
        join_restaurant: ColumnElement[bool] = (Merchant.id == Restaurant.merchant_id) & (Restaurant.user_id == user_id)
        join_expense: ColumnElement[bool] = (Restaurant.id == Expense.restaurant_id) & (Expense.user_id == user_id)
    else:
        join_restaurant = Merchant.id == Restaurant.merchant_id
        join_expense = Restaurant.id == Expense.restaurant_id

    stmt = (
        select(
            Merchant,
            func.count(distinct(Restaurant.id)).label("restaurant_count"),
            func.count(Expense.id).label("expense_count"),
            func.coalesce(func.sum(Expense.amount), Decimal("0")).label("total_amount"),
            func.max(Expense.date).label("last_expense_date"),
        )
        .select_from(Merchant)
        .outerjoin(Restaurant, join_restaurant)
        .outerjoin(Expense, join_expense)
        .group_by(Merchant.id)
    )

    # Search and merchant classification filters
    search = filters.get("search", "").strip()
    if search:
        stmt = stmt.filter(
            or_(
                Merchant.name.ilike(f"%{search}%"),
                Merchant.short_name.ilike(f"%{search}%"),
                Merchant.website.ilike(f"%{search}%"),
                Merchant.description.ilike(f"%{search}%"),
                Merchant.cuisine.ilike(f"%{search}%"),
                Merchant.menu_focus.ilike(f"%{search}%"),
                func.replace(Merchant.service_level, "_", " ").ilike(f"%{search}%"),
                func.replace(Merchant.category, "_", " ").ilike(f"%{search}%"),
            )
        )
    category = filters.get("category")
    if category:
        stmt = stmt.filter(Merchant.category == category)
    service_level = filters.get("service_level")
    if service_level:
        stmt = stmt.filter(Merchant.service_level == service_level)
    cuisine = filters.get("cuisine")
    if cuisine:
        stmt = stmt.filter(Merchant.cuisine == cuisine)
    menu_focus = filters.get("menu_focus")
    if menu_focus:
        stmt = stmt.filter(Merchant.menu_focus == menu_focus)
    is_chain = filters.get("is_chain")
    if is_chain:
        stmt = stmt.filter(Merchant.is_chain == (str(is_chain).lower() == "true"))
    has_description = filters.get("has_description")
    if has_description == "yes":
        stmt = stmt.filter(Merchant.description.isnot(None), Merchant.description != "")
    elif has_description == "no":
        stmt = stmt.filter(or_(Merchant.description.is_(None), Merchant.description == ""))
    restaurant_status = filters.get("restaurant_status")
    restaurant_count_expr = func.count(distinct(Restaurant.id))
    if restaurant_status == "without_restaurants":
        stmt = stmt.having(restaurant_count_expr == 0)
    elif restaurant_status == "with_restaurants":
        stmt = stmt.having(restaurant_count_expr > 0)

    sort_by = (filters.get("sort") or "name").strip().lower()
    sort_order = (filters.get("order") or "asc").strip().lower()
    is_desc = sort_order == "desc"

    sort_mapping = {
        "name": Merchant.name,
        "restaurants": func.count(distinct(Restaurant.id)),
        "expenses": func.count(Expense.id),
        "spend": func.coalesce(func.sum(Expense.amount), Decimal("0")),
        "last_activity": func.max(Expense.date),
    }
    sort_column = sort_mapping.get(sort_by, Merchant.name)
    stmt = stmt.order_by(sort_column.desc() if is_desc else sort_column.asc(), Merchant.name.asc())

    results = db.session.execute(stmt).all()

    merchants = []
    merchant_data = {}
    total_amount_sum = 0.0
    for merchant, rest_count, exp_count, total_amt, last_expense_date in results:
        merchants.append(merchant)
        total_val = float(total_amt) if total_amt is not None else 0.0
        expense_count = exp_count or 0
        merchant_data[merchant.id] = {
            "restaurant_count": rest_count or 0,
            "expense_count": expense_count,
            "total_amount": total_val,
            "avg_expense_amount": (total_val / expense_count) if expense_count else 0.0,
            "last_expense_date": last_expense_date,
        }
        total_amount_sum += total_val

    stats = {
        "total_merchants": len(merchants),
        "total_restaurants": sum(d["restaurant_count"] for d in merchant_data.values()),
        "total_expenses": sum(d["expense_count"] for d in merchant_data.values()),
        "total_amount": total_amount_sum,
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


def get_restaurants_for_merchant_with_stats(user_id: int, merchant_id: int) -> list[dict[str, Any]]:
    """Get restaurants linked to a merchant along with expense rollups."""
    stmt = (
        select(
            Restaurant,
            func.count(Expense.id).label("expense_count"),
            func.coalesce(func.sum(Expense.amount), Decimal("0")).label("total_amount"),
            func.max(Expense.date).label("last_expense_date"),
        )
        .outerjoin(
            Expense,
            (Expense.restaurant_id == Restaurant.id) & (Expense.user_id == user_id),
        )
        .where(Restaurant.user_id == user_id, Restaurant.merchant_id == merchant_id)
        .group_by(Restaurant.id)
        .order_by(Restaurant.name.asc())
    )

    results = db.session.execute(stmt).all()
    restaurants: list[dict[str, Any]] = []
    for restaurant, expense_count, total_amount, last_expense_date in results:
        total_value = float(total_amount) if total_amount is not None else 0.0
        count_value = expense_count or 0
        restaurants.append(
            {
                "restaurant": restaurant,
                "expense_count": count_value,
                "total_amount": total_value,
                "avg_expense_amount": (total_value / count_value) if count_value else 0.0,
                "last_expense_date": last_expense_date,
            }
        )

    return restaurants


def get_merchant_summary(user_id: int, merchant_id: int) -> dict[str, Any]:
    """Get summary metrics for a single merchant."""
    restaurant_count_stmt = select(func.count(Restaurant.id)).where(
        Restaurant.user_id == user_id,
        Restaurant.merchant_id == merchant_id,
    )
    restaurant_count = db.session.scalar(restaurant_count_stmt) or 0

    expense_summary = get_merchant_expense_summary(user_id, merchant_id)

    last_expense_stmt = (
        select(func.max(Expense.date))
        .select_from(Expense)
        .join(Restaurant, Expense.restaurant_id == Restaurant.id)
        .where(
            Restaurant.user_id == user_id,
            Restaurant.merchant_id == merchant_id,
            Expense.user_id == user_id,
        )
    )
    last_expense_date = db.session.scalar(last_expense_stmt)

    expense_count = int(expense_summary["expense_count"])
    total_amount = float(expense_summary["total_amount"])

    return {
        "restaurant_count": restaurant_count,
        "expense_count": expense_count,
        "total_amount": total_amount,
        "avg_expense_amount": (total_amount / expense_count) if expense_count else 0.0,
        "last_expense_date": last_expense_date,
    }


def get_unique_merchant_cuisines() -> list[str]:
    """Return distinct merchant cuisines for filter dropdowns."""
    return [
        cuisine
        for cuisine in db.session.scalars(
            select(Merchant.cuisine).where(Merchant.cuisine.isnot(None)).distinct().order_by(Merchant.cuisine.asc())
        )
        if cuisine
    ]


def get_unique_merchant_categories() -> list[str]:
    """Return distinct merchant format categories currently used by merchants."""
    values = [
        category
        for category in db.session.scalars(select(Merchant.category).where(Merchant.category.isnot(None)).distinct())
        if category
    ]
    return sorted(values, key=lambda value: get_merchant_format_category_label(value).lower())


def get_unique_merchant_service_levels() -> list[str]:
    """Return distinct merchant service levels currently used by merchants."""
    values = [
        service_level
        for service_level in db.session.scalars(
            select(Merchant.service_level).where(Merchant.service_level.isnot(None)).distinct()
        )
        if service_level
    ]
    return sorted(values, key=lambda value: get_merchant_service_level_label(value).lower())


def get_unique_merchant_menu_focuses() -> list[str]:
    """Return distinct merchant menu focus values for filter dropdowns."""
    return [
        menu_focus
        for menu_focus in db.session.scalars(
            select(Merchant.menu_focus)
            .where(Merchant.menu_focus.isnot(None))
            .distinct()
            .order_by(Merchant.menu_focus.asc())
        )
        if menu_focus
    ]


def get_unlinked_restaurants_with_suggestions(user_id: int) -> list[dict[str, Any]]:
    """Return unlinked restaurants with merchant suggestions when available."""
    restaurants = db.session.scalars(
        select(Restaurant)
        .where(Restaurant.user_id == user_id, Restaurant.merchant_id.is_(None))
        .order_by(Restaurant.name.asc())
    ).all()

    results: list[dict[str, Any]] = []
    for restaurant in restaurants:
        suggested_merchant = find_merchant_for_restaurant(
            restaurant_name=restaurant.name or "",
            website=restaurant.website,
        )
        results.append(
            {
                "restaurant": restaurant,
                "suggested_merchant": suggested_merchant,
            }
        )

    return results


def associate_restaurants_to_suggested_merchants(
    user_id: int,
    restaurant_ids: list[int] | None = None,
) -> tuple[int, list[Restaurant]]:
    """Link unlinked restaurants to their suggested merchants."""
    suggestion_rows = get_unlinked_restaurants_with_suggestions(user_id)
    allowed_ids = set(restaurant_ids or [])
    updated: list[Restaurant] = []

    for row in suggestion_rows:
        restaurant = row["restaurant"]
        suggested_merchant = row["suggested_merchant"]
        if not suggested_merchant:
            continue
        if restaurant_ids is not None and restaurant.id not in allowed_ids:
            continue
        restaurant.merchant_id = suggested_merchant.id
        updated.append(restaurant)

    if updated:
        db.session.commit()

    return len(updated), updated


def get_merchant_expense_summary(user_id: int | None, merchant_id: int) -> dict[str, int | float]:
    """Get expense count and total amount for a merchant, optionally scoped by user.

    Returns:
        Dict with expense_count and total_amount.
    """
    stmt = (
        select(
            func.count(Expense.id).label("expense_count"),
            func.coalesce(func.sum(Expense.amount), Decimal("0")).label("total_amount"),
        )
        .select_from(Expense)
        .join(Restaurant, Expense.restaurant_id == Restaurant.id)
        .where(Restaurant.merchant_id == merchant_id)
    )
    if user_id is not None:
        stmt = stmt.where(Restaurant.user_id == user_id, Expense.user_id == user_id)
    row = db.session.execute(stmt).one()
    total = row.total_amount
    return {
        "expense_count": row.expense_count or 0,
        "total_amount": float(total) if total is not None else 0.0,
    }


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


def get_merchant_by_name_or_short_name(identifier: str, exclude_id: int | None = None) -> Merchant | None:
    """Get a merchant by exact name or short_name (case-insensitive)."""
    normalized = (identifier or "").strip().lower()
    if not normalized:
        return None

    stmt = select(Merchant).where(
        or_(
            func.lower(Merchant.name) == normalized,
            func.lower(Merchant.short_name) == normalized,
        )
    )
    if exclude_id is not None:
        stmt = stmt.where(Merchant.id != exclude_id)
    return db.session.execute(stmt).scalars().first()


def find_conflicting_merchant(
    name: str, short_name: str | None = None, exclude_id: int | None = None
) -> Merchant | None:
    """Find merchant that conflicts with proposed name/short_name values."""
    seen_identifiers: set[str] = set()
    identifiers: list[str] = []
    for value in (name, short_name):
        cleaned = (value or "").strip()
        normalized = cleaned.lower()
        if cleaned and normalized not in seen_identifiers:
            identifiers.append(cleaned)
            seen_identifiers.add(normalized)

    for identifier in identifiers:
        conflict = get_merchant_by_name_or_short_name(identifier, exclude_id=exclude_id)
        if conflict:
            return conflict
    return None


def _normalize_for_name_match(value: str | None) -> str:
    """Normalize names for resilient brand matching."""
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def find_merchant_for_restaurant_name(restaurant_name: str) -> Merchant | None:
    """Find best merchant match from a restaurant name.

    Matching rules:
    - Compare against merchant short_name and full name
    - Accept exact match or prefix match with common separators
    - Prefer short_name matches, then longer/more specific match text
    """
    normalized_restaurant_name = _normalize_for_name_match(restaurant_name)
    if not normalized_restaurant_name:
        return None

    merchants = db.session.execute(select(Merchant)).scalars().all()
    candidates: list[tuple[int, int, int, Merchant]] = []
    # tuple fields:
    # 0: match type rank (0=short_name exact/prefix, 1=name exact/prefix)
    # 1: exact match rank (0=exact, 1=prefix)
    # 2: negative length for longest-first sorting
    # 3: merchant

    for merchant in merchants:
        for is_short_name, raw_value in ((True, merchant.short_name), (False, merchant.name)):
            value = _normalize_for_name_match(raw_value)
            if not value:
                continue

            is_exact = normalized_restaurant_name == value
            is_prefix = normalized_restaurant_name.startswith(f"{value} ")
            if not (is_exact or is_prefix):
                continue

            candidates.append(
                (
                    0 if is_short_name else 1,
                    0 if is_exact else 1,
                    -len(value),
                    merchant,
                )
            )

    if not candidates:
        return None

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    best = candidates[0][3]
    # Avoid ambiguous association when top-ranked matches tie on score but point to different merchants.
    best_score = candidates[0][:3]
    tied_merchants = {candidate[3].id for candidate in candidates if candidate[:3] == best_score}
    if len(tied_merchants) > 1:
        return None
    return best


def find_merchant_for_website(website: str | None) -> Merchant | None:
    """Find merchant by normalized website host."""
    comparable_host = extract_comparable_website_host(website)
    if not comparable_host:
        return None

    merchants = db.session.execute(select(Merchant)).scalars().all()
    matches = [
        merchant for merchant in merchants if extract_comparable_website_host(merchant.website) == comparable_host
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def find_merchant_for_restaurant(*, restaurant_name: str, website: str | None = None) -> Merchant | None:
    """Find the best merchant using website first, then restaurant-name rules."""
    merchant = find_merchant_for_website(website)
    if merchant:
        return merchant
    return find_merchant_for_restaurant_name(restaurant_name)


def _restaurant_matches_merchant(restaurant_name: str, merchant: Merchant) -> bool:
    """Check whether a restaurant name matches a merchant name/short_name rule."""
    normalized_restaurant_name = _normalize_for_name_match(restaurant_name)
    if not normalized_restaurant_name:
        return False

    for raw_value in (merchant.short_name, merchant.name):
        normalized_merchant_value = _normalize_for_name_match(raw_value)
        if not normalized_merchant_value:
            continue
        if normalized_restaurant_name == normalized_merchant_value:
            return True
        if normalized_restaurant_name.startswith(f"{normalized_merchant_value} "):
            return True
    return False


def get_unlinked_matching_restaurants_for_merchant(user_id: int, merchant_id: int) -> list[Restaurant]:
    """Get unlinked restaurants for a user that match the merchant by name rules."""
    merchant = get_merchant(merchant_id)
    if not merchant:
        return []

    restaurants = db.session.scalars(
        select(Restaurant)
        .where(
            Restaurant.user_id == user_id,
            Restaurant.merchant_id.is_(None),
        )
        .order_by(Restaurant.name.asc())
    ).all()
    return [restaurant for restaurant in restaurants if _restaurant_matches_merchant(restaurant.name or "", merchant)]


def associate_unlinked_matching_restaurants(
    user_id: int,
    merchant_id: int,
    restaurant_ids: list[int] | None = None,
) -> tuple[int, list[Restaurant]]:
    """Associate matching unlinked restaurants with the merchant.

    Args:
        user_id: Current user ID for ownership filtering
        merchant_id: Target merchant ID
        restaurant_ids: Optional subset of candidate restaurant IDs

    Returns:
        Tuple of (updated_count, updated_restaurants)
    """
    candidates = get_unlinked_matching_restaurants_for_merchant(user_id, merchant_id)
    if not candidates:
        return 0, []

    allowed_ids = {restaurant.id for restaurant in candidates if restaurant.id is not None}
    if restaurant_ids:
        allowed_ids = allowed_ids.intersection(set(restaurant_ids))

    selected = [restaurant for restaurant in candidates if restaurant.id in allowed_ids]
    if not selected:
        return 0, []

    for restaurant in selected:
        restaurant.merchant_id = merchant_id

    db.session.commit()
    return len(selected), selected


def create_merchant(user_id: int, data: dict[str, Any]) -> Merchant:
    """Create a new merchant.

    Args:
        user_id: The ID of the user creating the merchant
        data: Merchant data (name, format category, menu focus, cuisine, service level)

    Returns:
        Created merchant
    """
    name = data.get("name", "").strip()
    short_name = normalize_short_name(name, data.get("short_name"))
    conflict = find_conflicting_merchant(name, short_name=short_name)
    if conflict:
        raise ValueError("Merchant name or alias already exists")

    website = data.get("website")
    favicon_url = validate_favicon_url(data.get("favicon_url")) if data.get("favicon_url") else None
    merchant = Merchant(
        name=name,
        short_name=short_name,
        website=canonicalize_website_for_storage(website) if website else None,
        description=data.get("description"),
        favicon_url=favicon_url,
        category=data.get("category"),
        menu_focus=data.get("menu_focus"),
        cuisine=data.get("cuisine"),
        service_level=data.get("service_level"),
        is_chain=bool(data.get("is_chain", False)),
    )

    db.session.add(merchant)
    db.session.commit()

    return merchant


def get_or_create_merchant_for_import_restaurant_name(restaurant_name: str) -> Merchant | None:
    """Find or create a merchant for an imported restaurant name without committing.

    This is intended for import workflows that are already managing their own transaction.
    """
    cleaned_restaurant_name = (restaurant_name or "").strip()
    if not cleaned_restaurant_name:
        return None

    existing = find_merchant_for_restaurant_name(cleaned_restaurant_name)
    if existing:
        return existing

    merchant_name = cleaned_restaurant_name.split(" - ", 1)[0].strip() or cleaned_restaurant_name
    conflict = find_conflicting_merchant(merchant_name)
    if conflict:
        return conflict

    short_name = normalize_short_name(merchant_name, derive_short_name_from_merchant_name(merchant_name))
    merchant = Merchant(
        name=merchant_name,
        short_name=short_name,
        website=None,
        description=None,
        favicon_url=None,
        category=None,
        menu_focus=None,
        cuisine=None,
        service_level=None,
        is_chain=False,
    )
    db.session.add(merchant)
    db.session.flush()
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

    proposed_name = data["name"].strip() if "name" in data else merchant.name
    if "short_name" in data:
        proposed_short_name = normalize_short_name(proposed_name, data["short_name"])
    else:
        proposed_short_name = merchant.short_name

    conflict = find_conflicting_merchant(proposed_name, short_name=proposed_short_name, exclude_id=merchant_id)
    if conflict:
        raise ValueError("Merchant name or alias already exists")

    if "name" in data:
        merchant.name = proposed_name
    if "short_name" in data:
        merchant.short_name = proposed_short_name
    if "website" in data:
        website = data["website"]
        merchant.website = canonicalize_website_for_storage(website) if website else None
    if "description" in data:
        merchant.description = data["description"]
    if "favicon_url" in data:
        raw = data["favicon_url"]
        merchant.favicon_url = validate_favicon_url(raw) if raw else None
    if "category" in data:
        merchant.category = data["category"]
        merchant.format_category = data["category"]
    if "menu_focus" in data:
        merchant.menu_focus = data["menu_focus"]
    if "cuisine" in data:
        merchant.cuisine = data["cuisine"]
    if "service_level" in data:
        merchant.service_level = data["service_level"]
    if "is_chain" in data:
        merchant.is_chain = bool(data["is_chain"])

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

    linked_restaurants = db.session.scalars(select(Restaurant).where(Restaurant.merchant_id == merchant_id)).all()
    for restaurant in linked_restaurants:
        restaurant.merchant_id = None

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
            "description": merchant.description or "",
            "favicon_url": merchant.favicon_url or "",
            "category": merchant.category or "",
            "menu_focus": merchant.menu_focus or "",
            "cuisine": merchant.cuisine or "",
            "service_level": merchant.service_level or "",
            "restaurant_count": int(restaurant_count or 0),
            "created_at": merchant.created_at.isoformat() if merchant.created_at else "",
            "updated_at": merchant.updated_at.isoformat() if merchant.updated_at else "",
        }
        for merchant, restaurant_count in results
    ]


def _coerce_import_bool(value: Any) -> bool:
    """Coerce loose CSV/JSON truthy values into a boolean."""
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}


def _clean_import_value(row: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty string value for the provided keys."""
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            return cleaned
    return ""


def _read_merchant_import_rows(file: FileStorage) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Parse merchant import rows from a CSV or JSON upload."""
    filename = (file.filename or "").lower()
    try:
        raw_bytes = file.read()
    except Exception as exc:
        return None, f"Unable to read file: {exc}"

    if not raw_bytes:
        return None, "The uploaded file is empty."

    try:
        decoded = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None, "The file must be UTF-8 encoded."

    if filename.endswith(".json"):
        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError as exc:
            return None, f"Invalid JSON file: {exc}"
        if not isinstance(parsed, list):
            return None, "JSON import must contain a list of merchant objects."
        rows = [row for row in parsed if isinstance(row, dict)]
        if not rows:
            return None, "No merchant rows were found in the JSON file."
        return rows, None

    if filename.endswith(".csv"):
        reader = csv.DictReader(decoded.splitlines())
        if not reader.fieldnames:
            return None, "CSV file must include a header row."
        rows = list(reader)
        if not rows:
            return None, "No merchant rows were found in the CSV file."
        return rows, None

    return None, "Unsupported file type. Please upload a CSV or JSON file."


def import_merchants_from_file(file: FileStorage, user_id: int) -> tuple[bool, dict[str, Any]]:
    """Import merchants from a CSV or JSON file."""
    try:
        rows, error = _read_merchant_import_rows(file)
        if error:
            return False, {"message": error, "has_errors": True, "error_details": [error]}
        if rows is None:
            return False, {"message": "Failed to read import file.", "has_errors": True, "error_details": []}

        success_count = 0
        skipped_count = 0
        errors: list[str] = []

        for index, row in enumerate(rows, start=2):
            line_label = f"Row {index}"
            name = _clean_import_value(row, "name", "merchant_name", "brand", "merchant_brand")
            if not name:
                errors.append(f"{line_label}: name is required.")
                continue

            short_name = normalize_short_name(name, _clean_import_value(row, "short_name", "alias"))
            if find_conflicting_merchant(name, short_name=short_name):
                skipped_count += 1
                continue

            try:
                create_merchant(
                    user_id,
                    {
                        "name": name,
                        "short_name": short_name,
                        "website": _clean_import_value(row, "website"),
                        "description": _clean_import_value(row, "description") or None,
                        "favicon_url": _clean_import_value(row, "favicon_url") or None,
                        "category": _clean_import_value(row, "category", "format_category") or None,
                        "menu_focus": _clean_import_value(row, "menu_focus") or None,
                        "cuisine": _clean_import_value(row, "cuisine") or None,
                        "service_level": _clean_import_value(row, "service_level") or None,
                        "is_chain": _coerce_import_bool(row.get("is_chain")),
                    },
                )
                success_count += 1
            except ValueError as exc:
                errors.append(f"{line_label}: {exc}")
            except Exception as exc:
                db.session.rollback()
                errors.append(f"{line_label}: {exc}")

        result_data = {
            "success_count": success_count,
            "skipped_count": skipped_count,
            "error_count": len(errors),
            "errors": errors,
            "has_warnings": skipped_count > 0,
            "has_errors": bool(errors),
        }

        parts: list[str] = []
        if success_count:
            parts.append(f"{success_count} merchants imported successfully")
        if skipped_count:
            parts.append(f"{skipped_count} duplicates skipped")
        if errors:
            parts.append(f"{len(errors)} errors occurred")
        result_data["message"] = ". ".join(parts) + "." if parts else "No merchants processed."

        if errors:
            result_data["error_details"] = errors[:5] + (
                [f"... and {len(errors) - 5} more errors"] if len(errors) > 5 else []
            )

        return len(errors) == 0, result_data
    except Exception as exc:
        db.session.rollback()
        error_message = f"Error processing merchant import file: {exc}"
        return False, {"message": error_message, "has_errors": True, "error_details": [error_message]}


def get_merchant_form_choices() -> list[tuple[str, str]]:
    """Get merchant choices for form dropdowns.

    Returns:
        List of (value, label) tuples
    """
    choices = [("", "-- Select Merchant --")]
    for category in MERCHANT_CATEGORIES:
        display_name = get_merchant_format_category_label(category)
        choices.append((category, display_name))
    return choices
