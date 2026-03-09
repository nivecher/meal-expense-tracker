from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.loyalty.models import MerchantRewardsLink
    from app.restaurants.models import Restaurant


_MERCHANT_FORMAT_CATEGORY_LABELS = {
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

_MERCHANT_SERVICE_LEVEL_LABELS = {
    "fine_dining": "Fine Dining",
    "casual_dining": "Casual Dining",
    "fast_casual": "Fast Casual",
    "quick_service": "Quick Service",
}


class Merchant(BaseModel):
    """Merchant model for restaurant brands and franchises.

    Represents a restaurant brand/franchise independent of specific locations.
    Examples: Starbucks, McDonald's, local restaurant groups.

    Attributes:
        name: Name of the merchant/brand
        short_name: Optional short display name used in restaurant display names
        website: Optional merchant website URL
        category: Optional physical/operational format classification
        menu_focus: Optional primary menu/product focus classification
        cuisine: Optional cuisine classification aligned with restaurants
        format_category: Deprecated duplicate format field retained for compatibility
        service_level: Optional service style classification (e.g., quick_service, casual_dining)
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
    description: Mapped[str | None] = mapped_column(
        db.Text,
        nullable=True,
        comment="Optional merchant description or summary",
    )
    favicon_url: Mapped[str | None] = mapped_column(
        db.String(500),
        nullable=True,
        comment="Optional explicit favicon URL; takes precedence over website-derived favicon",
    )
    category: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Optional physical or operational format classification for the merchant",
    )
    menu_focus: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Optional menu or product focus classification for the merchant",
    )
    cuisine: Mapped[str | None] = mapped_column(
        db.String(100),
        nullable=True,
        index=True,
        comment="Optional cuisine classification aligned with restaurant cuisine values",
    )
    format_category: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Optional physical or operational format classification for the merchant",
    )
    service_level: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Optional service style classification for the merchant",
    )
    is_chain: Mapped[bool] = mapped_column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether this merchant represents a chain brand with multiple locations",
    )

    # Relationships
    restaurants: Mapped[list[Restaurant]] = relationship(
        "Restaurant",
        back_populates="merchant",
        lazy="dynamic",
    )
    merchant_rewards_links: Mapped[list[MerchantRewardsLink]] = relationship(
        "MerchantRewardsLink",
        back_populates="merchant",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )

    @property
    def category_display(self) -> str | None:
        if not self.category:
            return None
        return _MERCHANT_FORMAT_CATEGORY_LABELS.get(
            self.category,
            self.category.replace("_", " ").title(),
        )

    @property
    def menu_focus_display(self) -> str | None:
        if not self.menu_focus:
            return None
        return self.menu_focus

    @property
    def format_category_display(self) -> str | None:
        format_value = self.category or self.format_category
        if not format_value:
            return None
        return _MERCHANT_FORMAT_CATEGORY_LABELS.get(
            format_value,
            format_value.replace("_", " ").title(),
        )

    @property
    def service_level_display(self) -> str | None:
        if not self.service_level:
            return None
        return _MERCHANT_SERVICE_LEVEL_LABELS.get(
            self.service_level,
            self.service_level.replace("_", " ").title(),
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
            "description": self.description,
            "favicon_url": self.favicon_url,
            "category": self.category,
            "category_display": self.category_display,
            "menu_focus": self.menu_focus,
            "menu_focus_display": self.menu_focus_display,
            "cuisine": self.cuisine,
            "format_category": self.format_category,
            "format_category_display": self.format_category_display,
            "service_level": self.service_level,
            "service_level_display": self.service_level_display,
            "is_chain": self.is_chain,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Merchant(id={self.id}, name='{self.name}')>"
