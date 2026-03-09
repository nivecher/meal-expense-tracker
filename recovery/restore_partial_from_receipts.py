from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from app import create_app
from app.auth.models import User
from app.expenses.models import Category, Expense, Tag
from app.extensions import db
from app.merchants.models import Merchant
from app.receipts.models import Receipt
from app.restaurants.models import Restaurant
from app.visits.models import Visit


RECOVERY_USERNAME = "mtd37"
RECOVERY_EMAIL = "mtd37@hotmail.com"
RECOVERY_PASSWORD = "Recover-2026-03-07!"
RECOVERY_NOTE = "Recovered from surviving receipt PDFs after SQLite reset on 2026-03-07."


@dataclass(frozen=True)
class RecoveredExpense:
    merchant_name: str
    restaurant_name: str
    merchant_category: str
    amount: str
    date_text: str
    date_format: str
    city: str | None
    state: str | None
    website: str | None
    receipt_file: str
    notes: str


RECOVERED_EXPENSES = [
    RecoveredExpense(
        merchant_name="Just Salad",
        restaurant_name="Just Salad",
        merchant_category="casual_dining",
        amount="33.49",
        date_text="Apr 24, 2025",
        date_format="%b %d, %Y",
        city=None,
        state=None,
        website=None,
        receipt_file="20251120_024249_2025-04-24 Just Salad.pdf",
        notes="Recovered from Chase transaction PDF. Original location detail not available.",
    ),
    RecoveredExpense(
        merchant_name="Hawaiian Bros",
        restaurant_name="Hawaiian Bros - Murphy",
        merchant_category="casual_dining",
        amount="17.06",
        date_text="10/5/25",
        date_format="%m/%d/%y",
        city="Murphy",
        state="TX",
        website=None,
        receipt_file="20251216_171859_20251005 Hawaiian Bros.pdf",
        notes="Recovered from Toast receipt PDF for Hawaiian Bros 0033.",
    ),
    RecoveredExpense(
        merchant_name="Cotton Patch Cafe",
        restaurant_name="Cotton Patch Cafe - Wylie",
        merchant_category="casual_dining",
        amount="75.95",
        date_text="07/23/2022",
        date_format="%m/%d/%Y",
        city="Wylie",
        state="TX",
        website=None,
        receipt_file="20251216_180254_20220723 Cotton Patch Cafe - Wylie.pdf",
        notes="Recovered from receipt PDF for Cotton Patch Cafe - Wylie.",
    ),
]


def _ensure_expected_db_uri(app) -> None:
    uri = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
    if not uri.endswith("/instance/app-development.db"):
        raise RuntimeError(f"Refusing recovery against unexpected database URI: {uri}")


def _clear_user_owned_data() -> None:
    for model in (Receipt, Expense, Visit, Restaurant, Merchant, Category, Tag, User):
        db.session.query(model).delete()
    db.session.commit()


def _create_user() -> User:
    user = User(
        username=RECOVERY_USERNAME,
        email=RECOVERY_EMAIL,
        advanced_features_enabled=True,
        display_name=RECOVERY_USERNAME,
        timezone="America/Chicago",
    )
    user.set_password(RECOVERY_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


def _create_default_category(user: User) -> Category:
    category = Category(
        name="Recovered Meals",
        description="Recovered from surviving receipt PDFs after database reset.",
        color="#6c757d",
        icon="receipt",
        is_default=False,
        user_id=user.id,
    )
    db.session.add(category)
    db.session.flush()
    return category


def _get_or_create_merchant(user: User, spec: RecoveredExpense) -> Merchant:
    merchant = db.session.query(Merchant).filter_by(name=spec.merchant_name).first()
    if merchant:
        return merchant

    merchant = Merchant(
        name=spec.merchant_name,
        short_name=spec.merchant_name,
        category=spec.merchant_category,
        website=spec.website,
    )
    db.session.add(merchant)
    db.session.flush()
    return merchant


def _create_restaurant(user: User, merchant: Merchant, spec: RecoveredExpense) -> Restaurant:
    restaurant = Restaurant(
        name=spec.restaurant_name,
        city=spec.city,
        state=spec.state,
        user_id=user.id,
        merchant_id=merchant.id,
        type="restaurant",
        service_level="casual_dining",
        website=spec.website,
        notes=RECOVERY_NOTE,
    )
    db.session.add(restaurant)
    db.session.flush()
    return restaurant


def _create_expense(user: User, category: Category, restaurant: Restaurant, spec: RecoveredExpense) -> Expense:
    expense_date = datetime.strptime(spec.date_text, spec.date_format)
    expense = Expense(
        amount=Decimal(spec.amount),
        notes=f"{RECOVERY_NOTE} {spec.notes}",
        date=expense_date,
        user_id=user.id,
        restaurant_id=restaurant.id,
        category_id=category.id,
        receipt_image=f"uploads/{spec.receipt_file}",
        receipt_verified=True,
    )
    db.session.add(expense)
    db.session.flush()
    return expense


def _create_receipt(user: User, restaurant: Restaurant, expense: Expense, spec: RecoveredExpense) -> None:
    receipt = Receipt(
        user_id=user.id,
        restaurant_id=restaurant.id,
        expense_id=expense.id,
        file_uri=f"uploads/{spec.receipt_file}",
        receipt_type="pdf",
        ocr_total=Decimal(spec.amount),
    )
    db.session.add(receipt)


def main() -> None:
    app = create_app()
    _ensure_expected_db_uri(app)

    with app.app_context():
        _clear_user_owned_data()
        user = _create_user()
        category = _create_default_category(user)

        for spec in RECOVERED_EXPENSES:
            merchant = _get_or_create_merchant(user, spec)
            restaurant = _create_restaurant(user, merchant, spec)
            expense = _create_expense(user, category, restaurant, spec)
            _create_receipt(user, restaurant, expense, spec)

        db.session.commit()

        print("Recovered user:", RECOVERY_USERNAME)
        print("Recovered email:", RECOVERY_EMAIL)
        print("Temporary password:", RECOVERY_PASSWORD)
        print("Restaurants:", db.session.query(Restaurant).count())
        print("Merchants:", db.session.query(Merchant).count())
        print("Expenses:", db.session.query(Expense).count())
        print("Receipts:", db.session.query(Receipt).count())


if __name__ == "__main__":
    main()
