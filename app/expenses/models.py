from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import UniqueConstraint, event
from sqlalchemy.orm import Mapped, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.restaurants.models import Restaurant


class Expense(BaseModel):
    """Expense model for tracking meal expenses.

    Attributes:
        amount: The amount of the expense (stored as Decimal with 2 decimal places)
        notes: Optional notes about the expense
        meal_type: Type of meal (e.g., breakfast, lunch, dinner)
        date: Date and time of the expense
        user_id: ID of the user who made the expense
        restaurant_id: ID of the restaurant where the expense occurred
        category_id: ID of the expense category

    Notes:
        - Amount is stored with 2 decimal places precision
        - All monetary values are handled using Python's Decimal for precision
        - Expenses are automatically sorted by date in descending order
    """

    __tablename__ = "expense"
    __table_args__ = {"comment": "Track meal expenses with details about where and when they occurred"}

    # Columns
    amount: Mapped[Decimal] = db.Column(
        db.Numeric(10, 2, asdecimal=True),
        nullable=False,
        comment="Amount of the expense (stored with 2 decimal places)",
        default=Decimal("0.00"),
    )
    notes: Mapped[Optional[str]] = db.Column(db.Text, nullable=True, comment="Additional notes about the expense")
    meal_type: Mapped[Optional[str]] = db.Column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Type of meal (e.g., breakfast, lunch, dinner)",
    )
    date: Mapped[datetime] = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
        comment="Date and time when the expense occurred",
    )

    # Receipt information
    receipt_image: Mapped[Optional[str]] = db.Column(
        db.String(255), nullable=True, comment="Path to the receipt image file"
    )
    receipt_verified: Mapped[bool] = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether the receipt has been verified",
    )

    # Foreign keys with proper cascading
    user_id: Mapped[int] = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who made this expense",
    )
    restaurant_id: Mapped[Optional[int]] = db.Column(
        db.Integer,
        db.ForeignKey("restaurant.id", ondelete="SET NULL"),
        index=True,
        comment="Reference to the restaurant where the expense occurred",
    )
    category_id: Mapped[Optional[int]] = db.Column(
        db.Integer,
        db.ForeignKey("category.id", ondelete="SET NULL"),
        index=True,
        comment="Reference to the expense category",
    )

    # Relationships with explicit join conditions and loading strategies
    user: Mapped["User"] = relationship("User", back_populates="expenses", lazy="joined", innerjoin=True)
    restaurant: Mapped[Optional["Restaurant"]] = relationship("Restaurant", back_populates="expenses", lazy="joined")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="expenses", lazy="joined")

    @property
    def formatted_amount(self) -> str:
        """Return the amount formatted as a currency string."""
        if self.amount is None:
            return "$0.00"
        return f"${self.amount:.2f}"

    @property
    def is_recent(self) -> bool:
        """Check if the expense is from the last 7 days."""
        if not self.date:
            return False
        return (datetime.now(timezone.utc) - self.date).days <= 7

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the expense.

        Returns:
            Dict containing the expense data with proper type conversion
            and related objects serialized as dictionaries.
        """
        amount_decimal = Decimal(str(self.amount)) if self.amount is not None else Decimal("0.00")

        result: Dict[str, Any] = {
            "id": self.id,
            "amount": float(amount_decimal.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)),
            "notes": self.notes,
            "meal_type": self.meal_type,
            "date": self.date.isoformat() if self.date else None,
            "formatted_amount": self.formatted_amount,
            "is_recent": self.is_recent,
            "receipt_image": self.receipt_image,
            "receipt_verified": self.receipt_verified,
            "user_id": self.user_id,
            "restaurant_id": self.restaurant_id,
            "category_id": self.category_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include related objects if they're loaded
        if hasattr(self, "restaurant") and self.restaurant is not None:
            result["restaurant"] = self.restaurant.to_dict()
        if hasattr(self, "category") and self.category is not None:
            result["category"] = self.category.to_dict()
        if hasattr(self, "user") and self.user is not None:
            result["user"] = {
                "id": self.user.id,
                "username": self.user.username,
                "email": self.user.email,
            }

        return result

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.formatted_amount}, date={self.date}, user_id={self.user_id})>"


@event.listens_for(Expense, "before_insert")
@event.listens_for(Expense, "before_update")
def validate_expense(mapper, connection, target):
    """Validate expense data before insert/update."""
    # Ensure amount is properly converted to Decimal and rounded to 2 decimal places
    if target.amount is not None:
        if not isinstance(target.amount, Decimal):
            # Convert to string first to avoid floating point precision issues
            target.amount = Decimal(str(target.amount))
        target.amount = target.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Clean string fields
    if target.notes:
        target.notes = target.notes.strip()
    if target.meal_type:
        target.meal_type = target.meal_type.strip().lower()

    # Ensure date is timezone-aware
    if target.date:
        from datetime import datetime, timezone

        if isinstance(target.date, datetime):
            # For datetime objects, ensure they're timezone-aware
            if target.date.tzinfo is None:
                target.date = target.date.replace(tzinfo=timezone.utc)
        else:
            # For date objects, convert to timezone-aware datetime
            target.date = datetime.combine(target.date, datetime.min.time(), tzinfo=timezone.utc)


class Category(BaseModel):
    """Category model for organizing expenses.

    Attributes:
        name: Name of the category (unique per user)
        description: Optional description of the category
        color: Hex color code for the category (default: #6c757d)
        icon: Optional icon identifier for the category
        is_default: Whether this is a default category
        user_id: ID of the user who owns this category

    Notes:
        - Each user can have their own set of categories
        - Categories are soft-deleted when a user is deleted
        - Default categories are pre-created for new users
    """

    __tablename__ = "category"
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uix_category_name_user"),
        {"comment": "Categories for organizing expenses"},
    )

    # Category details
    name: Mapped[str] = db.Column(
        db.String(100),
        nullable=False,
        index=True,
        comment="Name of the category (unique per user)",
    )
    description: Mapped[Optional[str]] = db.Column(db.Text, nullable=True, comment="Description of the category")
    color: Mapped[str] = db.Column(
        db.String(20),
        default="#6c757d",
        nullable=False,
        comment="Hex color code for the category (e.g., #6c757d)",
    )
    icon: Mapped[Optional[str]] = db.Column(
        db.String(50), nullable=True, comment="Icon identifier from the icon library"
    )
    is_default: Mapped[bool] = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a default category",
    )

    # Foreign key
    user_id: Mapped[int] = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who owns this category",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories", lazy="joined", innerjoin=True)
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense",
        back_populates="category",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="dynamic",
    )

    @property
    def expense_count(self) -> int:
        """Get the number of expenses in this category."""
        if hasattr(self, "_expense_count"):
            return self._expense_count
        if hasattr(self, "expenses") and hasattr(self.expenses, "count"):
            return self.expenses.count()
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the category.

        Returns:
            Dict containing the category data with related counts
        """
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "color": self.color,
            "icon": self.icon,
            "is_default": self.is_default,
            "user_id": self.user_id,
            "expense_count": self.expense_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include user info if loaded
        if hasattr(self, "user") and self.user is not None:
            result["user"] = {"id": self.user.id, "username": self.user.username}

        return result

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', user_id={self.user_id})>"


@event.listens_for(Category, "before_insert")
@event.listens_for(Category, "before_update")
def validate_category(mapper, connection, target):
    """Validate category data before insert/update."""
    # Clean string fields
    if target.name:
        target.name = target.name.strip()
    if target.description:
        target.description = target.description.strip()
    if target.color:
        # Ensure color is lowercase and starts with #
        target.color = target.color.lower().lstrip("#")
        if not target.color.startswith("#"):
            target.color = f"#{target.color}"
    if target.icon:
        target.icon = target.icon.strip()
