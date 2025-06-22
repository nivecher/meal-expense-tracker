"""Expense category model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.expenses.models import Expense


class Category(db.Model):
    """Expense category model."""

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    expenses: Mapped[list["Expense"]] = relationship("Expense", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category {self.name}>"
