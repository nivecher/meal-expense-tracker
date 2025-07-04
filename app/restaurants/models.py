from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, UniqueConstraint, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

if TYPE_CHECKING:
    from app.auth.models import User  # noqa: F401
    from app.expenses.models import Expense


class Restaurant(db.Model):
    __tablename__ = "restaurant"
    __allow_unmapped__ = True

    __table_args__ = (UniqueConstraint("name", "city", "user_id", name="uix_restaurant_name_city_user"),)

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("user.id"), nullable=False, index=True)

    # Basic Information
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Location Information
    address: Mapped[Optional[str]] = mapped_column(String(200))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    latitude: Mapped[Optional[float]] = mapped_column(Float, comment="Geographic latitude")
    longitude: Mapped[Optional[float]] = mapped_column(Float, comment="Geographic longitude")

    # Contact Information
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    website: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(100))

    # Business Details
    price_range: Mapped[Optional[int]]
    cuisine: Mapped[Optional[str]] = mapped_column(String(100))
    rating: Mapped[Optional[float]]
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Google Places Integration
    google_place_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    place_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="restaurants", lazy="select")  # type: ignore[valid-type]
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="restaurant", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        """Return the restaurant's full name including city if available."""
        return f"{self.name} - {self.city}" if self.city else self.name

    @property
    def full_address(self) -> Optional[str]:
        """Return the restaurant's full address as a formatted string."""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts) if parts else None

    @property
    def google_search(self) -> Optional[str]:
        """Return a string suitable for a Google Maps search."""
        parts = []
        if self.name:
            parts.append(self.name)
        if address := self.full_address:
            parts.append(address)
        return ", ".join(parts) if parts else None

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
