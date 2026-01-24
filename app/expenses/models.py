from __future__ import annotations

from datetime import UTC, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.restaurants.models import Restaurant


class Tag(BaseModel):
    """Tag model for custom expense labels.

    Attributes:
        name: Name of the tag (unique per user)
        color: Hex color code for the tag badge
        description: Optional description of the tag
        user_id: ID of the user who owns this tag

    Notes:
        - Each user can have their own set of tags
        - Tags are soft-deleted when a user is deleted
        - Tags follow Jira-style naming conventions (spaces replaced with hyphens, case-sensitive)
    """

    __tablename__ = "tag"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uix_tag_name_user"),
        {"comment": "Custom tags for organizing expenses"},
    )

    # Tag details
    name: Mapped[str] = mapped_column(
        db.String(50),
        nullable=False,
        index=True,
        comment="Name of the tag (unique per user, Jira-style)",
    )
    color: Mapped[str] = mapped_column(
        db.String(20),
        default="#6c757d",
        nullable=False,
        comment="Hex color code for the tag badge (e.g., #6c757d)",
    )
    description: Mapped[str | None] = mapped_column(db.Text, nullable=True, comment="Description of the tag")

    # Foreign key
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who owns this tag",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="tags", lazy="select")
    expense_tags: Mapped[list[ExpenseTag]] = relationship(
        "ExpenseTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    @property
    def expense_count(self) -> int:
        """Get the number of expenses using this tag.

        Only counts expenses that actually exist (joins with Expense table).
        """
        if hasattr(self, "_expense_count"):
            count = getattr(self, "_expense_count", 0)
            return int(count) if count else 0
        try:
            # Use a direct query with join to ensure we only count tags on existing expenses
            from sqlalchemy import func, select

            from app.extensions import db

            stmt = (
                select(func.count(ExpenseTag.id))
                .join(Expense, ExpenseTag.expense_id == Expense.id)
                .where(ExpenseTag.tag_id == self.id)
            )
            result = db.session.scalar(stmt)
            return int(result) if result else 0
        except Exception:
            return 0

    @property
    def total_amount(self) -> float:
        """Get the total amount of expenses using this tag.

        Returns:
            Total amount as float, or 0.0 if no expenses or not calculated
        """
        if hasattr(self, "_total_amount"):
            amount = getattr(self, "_total_amount", 0.0)
            return float(amount) if amount else 0.0
        return 0.0

    @property
    def last_visit(self) -> datetime | None:
        """Get the date of the last expense using this tag.

        Returns:
            Last visit date as datetime, or None if no expenses or not calculated
        """
        if hasattr(self, "_last_visit"):
            return getattr(self, "_last_visit", None)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the tag.

        Returns:
            Dict containing the tag data with related counts
        """
        result = {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "user_id": self.user_id,
            "expense_count": self.expense_count,
            "total_amount": self.total_amount,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include user info if loaded (check if relationship is loaded)
        if hasattr(self, "user") and self.user is not None:
            result["user"] = {"id": self.user.id, "username": self.user.username}

        return result

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class ExpenseTag(BaseModel):
    """Association table for expense-tag many-to-many relationship.

    Attributes:
        expense_id: ID of the expense
        tag_id: ID of the tag
        added_by: ID of the user who added the tag

    Notes:
        - This is a many-to-many relationship between expenses and tags
        - Tracks who added each tag to an expense
        - Soft-deleted when either expense or tag is deleted
    """

    __tablename__ = "expense_tag"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("expense_id", "tag_id", name="uix_expense_tag"),
        {"comment": "Association table for expense-tag relationships"},
    )

    # Foreign keys
    expense_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("expense.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the expense",
    )
    tag_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("tag.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the tag",
    )
    added_by: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who added this tag to the expense",
    )

    # Relationships
    expense: Mapped[Expense] = relationship("Expense", back_populates="expense_tags", lazy="select")
    tag: Mapped[Tag] = relationship("Tag", back_populates="expense_tags", lazy="select")
    user: Mapped[User] = relationship("User", lazy="select")

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the expense tag.

        Returns:
            Dict containing the expense tag data
        """
        result: dict[str, Any] = {
            "id": self.id,
            "expense_id": self.expense_id,
            "tag_id": self.tag_id,
            "added_by": self.added_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

        # Include related objects if loaded (check if relationships are loaded)
        # Note: tag and user are always defined but may not be loaded (lazy loading)
        tag_obj = getattr(self, "tag", None)
        if tag_obj is not None:
            tag_dict = tag_obj.to_dict()
            result["tag"] = tag_dict
        user_obj = getattr(self, "user", None)
        if user_obj is not None:
            user_dict: dict[str, Any] = {"id": user_obj.id, "username": user_obj.username}
            result["user"] = user_dict

        return result

    def __repr__(self) -> str:
        return f"<ExpenseTag(expense_id={self.expense_id}, tag_id={self.tag_id})>"


class Expense(BaseModel):
    """Expense model for tracking meal expenses.

    Attributes:
        amount: The amount of the expense (stored as Decimal with 2 decimal places)
        notes: Optional notes about the expense
        meal_type: Type of meal (e.g., breakfast, lunch, dinner)
        order_type: Type of order (e.g., dine_in, takeout, delivery)
        party_size: Number of people in the party (optional)
        date: Date and time of the expense
        user_id: ID of the user who made the expense
        restaurant_id: ID of the restaurant where the expense occurred
        category_id: ID of the expense category

    Notes:
        - Amount is stored with 2 decimal places precision
        - All monetary values are handled using Python's Decimal for precision
        - Expenses are automatically sorted by date in descending order
        - Party size is used to calculate price per person metrics
    """

    __tablename__ = "expense"  # type: ignore[assignment]
    __table_args__ = {"comment": "Track meal expenses with details about where and when they occurred"}

    # Columns
    amount: Mapped[Decimal] = mapped_column(
        db.Numeric(10, 2, asdecimal=True),
        nullable=False,
        comment="Amount of the expense (stored with 2 decimal places)",
        default=Decimal("0.00"),
    )
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True, comment="Additional notes about the expense")
    meal_type: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Type of meal (e.g., breakfast, lunch, dinner)",
    )
    order_type: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Type of order (e.g., dine_in, takeout, delivery)",
    )
    party_size: Mapped[int | None] = mapped_column(
        db.Integer,
        nullable=True,
        comment="Number of people in the party (1-50)",
    )
    date: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(UTC),
        comment="Date and time when the expense occurred",
    )

    # Receipt information
    receipt_image: Mapped[str | None] = mapped_column(
        db.String(255), nullable=True, comment="Path to the receipt image file"
    )
    receipt_verified: Mapped[bool] = mapped_column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether the receipt has been verified",
    )

    # Foreign keys with proper cascading
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who made this expense",
    )
    restaurant_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("restaurant.id", ondelete="SET NULL"),
        index=True,
        comment="Reference to the restaurant where the expense occurred",
    )
    category_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("category.id", ondelete="SET NULL"),
        index=True,
        comment="Reference to the expense category",
    )

    # Relationships with explicit join conditions and loading strategies
    user: Mapped[User] = relationship("User", back_populates="expenses", lazy="select")
    restaurant: Mapped[Restaurant | None] = relationship("Restaurant", back_populates="expenses", lazy="select")
    category: Mapped[Category | None] = relationship("Category", back_populates="expenses", lazy="select")

    # Tags relationship
    expense_tags: Mapped[list[ExpenseTag]] = relationship(
        "ExpenseTag",
        back_populates="expense",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="select",
    )

    @property
    def tags(self) -> list[Tag]:
        """Get all tags associated with this expense."""
        expense_tags_list = getattr(self, "expense_tags", [])
        return [et.tag for et in expense_tags_list if et.tag is not None]

    @property
    def formatted_amount(self) -> str:
        """Return the amount formatted as a currency string."""
        return f"${self.amount:.2f}"

    @property
    def is_recent(self) -> bool:
        """Check if the expense is from the last 7 days."""
        return bool((datetime.now(UTC) - self.date).days <= 7)

    @property
    def price_per_person(self) -> Decimal | None:
        """Calculate the price per person for this expense."""
        party_size = self.party_size
        if party_size is None:
            return None
        # Type narrowing: after None check, party_size is int
        if party_size <= 0:
            return None
        return (self.amount / party_size).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def formatted_price_per_person(self) -> str | None:
        """Return the price per person formatted as a currency string."""
        if self.price_per_person is None:
            return None
        return f"${self.price_per_person:.2f}"

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the expense.

        Returns:
            Dict containing the expense data with proper type conversion
            and related objects serialized as dictionaries.
        """
        amount_decimal = Decimal(str(self.amount)) if self.amount is not None else Decimal("0.00")

        result: dict[str, Any] = {
            "id": self.id,
            "amount": float(amount_decimal.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)),
            "notes": self.notes,
            "meal_type": self.meal_type,
            "order_type": self.order_type,
            "party_size": self.party_size,
            "date": self.date.isoformat() if self.date else None,
            "formatted_amount": self.formatted_amount,
            "price_per_person": (float(self.price_per_person) if self.price_per_person is not None else None),
            "formatted_price_per_person": self.formatted_price_per_person,
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
        # Note: restaurant and category are always defined but may not be loaded (lazy loading)
        restaurant_obj = getattr(self, "restaurant", None)
        if restaurant_obj is not None:
            result["restaurant"] = restaurant_obj.to_dict()
        category_obj = getattr(self, "category", None)
        if category_obj is not None:
            result["category"] = category_obj.to_dict()
        # Note: user is always defined but may not be loaded (lazy loading)
        user_obj = getattr(self, "user", None)
        if user_obj is not None:
            result["user"] = {
                "id": user_obj.id,
                "username": user_obj.username,
                "email": user_obj.email,
            }

        # Include tags
        result["tags"] = [tag.to_dict() for tag in self.tags]

        return result

    def __repr__(self) -> str:
        return f"<Expense(id={self.id}, amount={self.formatted_amount}, date={self.date}, user_id={self.user_id})>"


@event.listens_for(Expense, "before_insert")
@event.listens_for(Expense, "before_update")
def validate_expense(mapper: object, connection: object, target: Expense) -> None:
    """Validate expense data before insert/update."""
    # Ensure amount is properly converted to Decimal and rounded to 2 decimal places
    # Note: amount is typed as Mapped[Decimal] but may be other types at runtime (e.g., float, str)
    amount_value: Any = target.amount
    if not isinstance(amount_value, Decimal):
        # Convert to string first to avoid floating point precision issues
        amount_value = Decimal(str(amount_value))
    target.amount = amount_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Clean string fields
    if target.notes is not None:
        target.notes = target.notes.strip()
    if target.meal_type is not None:
        target.meal_type = target.meal_type.strip().lower()

    # Ensure date is timezone-aware
    # Note: Type checker sees timezone=True in column definition, but runtime may receive naive datetimes
    if target.date:
        date_value: Any = target.date
        if isinstance(date_value, datetime):
            # For datetime objects, ensure they're timezone-aware
            if date_value.tzinfo is None:
                target.date = date_value.replace(tzinfo=UTC)
        else:
            # For date objects, interpret as the user's intended date
            # Convert to UTC at noon to avoid date shifting issues
            # This preserves the user's intended date regardless of timezone
            from datetime import date as date_type

            if isinstance(date_value, date_type):
                target.date = datetime.combine(date_value, datetime.min.time().replace(hour=12), tzinfo=UTC)


@event.listens_for(Tag, "before_insert")
@event.listens_for(Tag, "before_update")
def validate_tag(mapper: object, connection: object, target: Tag) -> None:
    """Validate tag data before insert/update."""
    # Clean string fields
    # Note: name is non-nullable, so no None check needed
    name_val: str = target.name
    # Replace spaces with hyphens (preserve case)
    name_val = name_val.strip().replace(" ", "-")
    # Remove any non-alphanumeric characters except hyphens
    name_val = "".join(c for c in name_val if c.isalnum() or c == "-")
    # Ensure it starts with a letter or number
    if name_val and not name_val[0].isalnum():
        name_val = name_val[1:]
    target.name = name_val
    # Clean description if present
    description_val = target.description
    if description_val is not None:
        stripped = description_val.strip()
        target.description = stripped if stripped else None
    # Clean and format color (color is non-nullable)
    color_val = target.color
    if color_val is not None:
        color_val = color_val.lower().lstrip("#")
        if not color_val.startswith("#"):
            color_val = f"#{color_val}"
        target.color = color_val


class Category(BaseModel):
    """Category model for organizing expenses.

    Attributes:
        name: Name of the category (unique per user)
        description: Optional description of the category
        color: Hex color code for the category (default: Bootstrap gray #6c757d)
        icon: Optional icon identifier for the category
        is_default: Whether this is a default category
        user_id: ID of the user who owns this category

    Notes:
        - Each user can have their own set of categories
        - Categories are soft-deleted when a user is deleted
        - Default categories are pre-created for new users
    """

    __tablename__ = "category"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("name", "user_id", name="uix_category_name_user"),
        {"comment": "Categories for organizing expenses"},
    )

    # Category details
    name: Mapped[str] = mapped_column(
        db.String(100),
        nullable=False,
        index=True,
        comment="Name of the category (unique per user)",
    )
    description: Mapped[str | None] = mapped_column(db.Text, nullable=True, comment="Description of the category")
    color: Mapped[str] = mapped_column(
        db.String(20),
        default="#6c757d",
        nullable=False,
        comment="Hex color code for the category (e.g., #6c757d)",
    )
    icon: Mapped[str | None] = mapped_column(
        db.String(50), nullable=True, comment="Icon identifier from the icon library"
    )
    is_default: Mapped[bool] = mapped_column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether this is a default category",
    )

    # Foreign key
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who owns this category",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="categories", lazy="joined", innerjoin=True)
    expenses: Mapped[list[Expense]] = relationship(
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
            count = getattr(self, "_expense_count", 0)
            return int(count) if count else 0
        if hasattr(self, "expenses") and hasattr(self.expenses, "count"):
            count = self.expenses.count()  # type: ignore[call-arg]
            return int(count) if count else 0
        return 0

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the category.

        Returns:
            Dict containing the category data with related counts
        """
        result: dict[str, Any] = {
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
        user = getattr(self, "user", None)
        if user is not None:
            result["user"] = {"id": user.id, "username": user.username}

        return result

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', user_id={self.user_id})>"


@event.listens_for(Category, "before_insert")
@event.listens_for(Category, "before_update")
def validate_category(mapper: object, connection: object, target: Category) -> None:
    """Validate category data before insert/update."""
    # Clean string fields
    # Note: name is non-nullable, so no None check needed
    name_val: str = target.name
    target.name = name_val.strip()
    # Clean description if present
    description_val = target.description
    if description_val is not None:
        stripped = description_val.strip()
        target.description = stripped if stripped else None
    # Clean and format color (color is non-nullable)
    color_val = target.color
    if color_val is not None:
        color_val = color_val.lower().lstrip("#")
        if not color_val.startswith("#"):
            color_val = f"#{color_val}"
        target.color = color_val
    # Clean icon if present
    icon_val = target.icon
    if icon_val is not None:
        stripped_icon = icon_val.strip()
        target.icon = stripped_icon if stripped_icon else None
