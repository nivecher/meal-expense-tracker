from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.restaurants.models import Restaurant


class Merchant(BaseModel):
    """Merchant model for restaurant brands and franchises.

    Represents a restaurant brand/franchise independent of specific locations.
    Examples: Starbucks, McDonald's, local restaurant groups.

    Attributes:
        name: Name of the merchant/brand
        short_name: Optional short display name used in restaurant display names
        website: Optional merchant website URL
        category: Optional category classification (e.g., fast_food, casual_dining, coffee_shop)
    """

    __tablename__ = "merchant"  # type: ignore[assignment]
    __table_args__ = {"comment": "Restaurant brands and franchises"}

    # Merchant details
    name: Mapped[str] = mapped_column(
        db.String(100),
        nullable=False,
        index=True,
        comment="Name of the merchant/brand",
    )
    short_name: Mapped[str | None] = mapped_column(
        db.String(100),
        nullable=True,
        comment="Optional short display name used in restaurant display names",
    )
    website: Mapped[str | None] = mapped_column(
        db.String(500),
        nullable=True,
        comment="Merchant website URL",
    )
    category: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Optional category classification (e.g., fast_food, casual_dining, coffee_shop)",
    )

    # Relationships
    restaurants: Mapped[list[Restaurant]] = relationship(
        "Restaurant",
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the merchant.

        Returns:
            Dict containing merchant data
        """
        return {
            "id": self.id,
            "name": self.name,
            "short_name": self.short_name,
            "website": self.website,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Merchant(id={self.id}, name='{self.name}')>"
