from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.auth.models import User
    from app.restaurants.models import Restaurant


class Expense(db.Model):
    __tablename__ = "expense"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meal_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False
    )

    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    restaurant_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("restaurant.id", ondelete="SET NULL"), index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("category.id", ondelete="SET NULL"), index=True
    )

    # Relationships with string literals to avoid circular imports
    user: Mapped["User"] = relationship("User", back_populates="expenses")
    restaurant: Mapped[Optional["Restaurant"]] = relationship("Restaurant", back_populates="expenses")
    # Using string literal for Category to avoid circular imports
    category = relationship("Category", back_populates="expenses")

    def __repr__(self) -> str:
        return f"<Expense {self.amount} on {self.date} by {self.user_id}>"


class Category(db.Model):
    __tablename__ = "category"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(
        String(20), default="#6c757d", nullable=False, comment="Hex color code for the category"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False
    )

    # Relationships
    expenses = relationship("Expense", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
