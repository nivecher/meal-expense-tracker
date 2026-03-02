from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.expenses.models import Expense
    from app.restaurants.models import Restaurant


class Visit(BaseModel):
    """Visit model for tracking restaurant visits independent of spending.

    Represents a visit to a restaurant, which may have multiple expenses
    or no expenses at all. Supports different visit types.

    Attributes:
        restaurant_id: Reference to the restaurant visited
        user_id: Reference to the user who made the visit
        datetime_start: When the visit started
        datetime_end: When the visit ended (optional)
        visit_type: Type of visit (dine_in, pickup, delivery, etc.)
        notes: Optional notes about the visit
    """

    __tablename__ = "visit"  # type: ignore[assignment]
    __table_args__ = {"comment": "Restaurant visits independent of spending"}

    # Visit details
    restaurant_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("restaurant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the restaurant visited",
    )
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who made this visit",
    )
    datetime_start: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(UTC),
        comment="When the visit started",
    )
    datetime_end: Mapped[datetime | None] = mapped_column(
        db.DateTime(timezone=True),
        nullable=True,
        comment="When the visit ended",
    )
    visit_type: Mapped[str | None] = mapped_column(
        db.String(20),
        nullable=True,
        index=True,
        comment="Type of visit (dine_in, pickup, delivery, drive_thru, unknown)",
    )
    notes: Mapped[str | None] = mapped_column(
        db.Text,
        nullable=True,
        comment="Optional notes about the visit",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="visits", lazy="select")
    restaurant: Mapped[Restaurant] = relationship("Restaurant", back_populates="visits", lazy="select")
    expenses: Mapped[list[Expense]] = relationship(
        "Expense",
        back_populates="visit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="dynamic",
    )

    @property
    def duration_minutes(self) -> int | None:
        """Calculate visit duration in minutes.

        Returns:
            Duration in minutes, or None if end time not set
        """
        if self.datetime_end is None:
            return None
        return int((self.datetime_end - self.datetime_start).total_seconds() / 60)

    @property
    def is_ongoing(self) -> bool:
        """Check if visit is currently ongoing.

        Returns:
            True if visit has no end time, False otherwise
        """
        return self.datetime_end is None

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the visit.

        Returns:
            Dict containing visit data with calculated fields
        """
        return {
            "id": self.id,
            "restaurant_id": self.restaurant_id,
            "user_id": self.user_id,
            "datetime_start": self.datetime_start.isoformat() if self.datetime_start else None,
            "datetime_end": self.datetime_end.isoformat() if self.datetime_end else None,
            "visit_type": self.visit_type,
            "notes": self.notes,
            "duration_minutes": self.duration_minutes,
            "is_ongoing": self.is_ongoing,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Visit(id={self.id}, restaurant_id={self.restaurant_id}, user_id={self.user_id})>"
