from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.merchants.models import Merchant


class RewardsProgram(BaseModel):
    """User-owned loyalty or rewards program definition."""

    __tablename__ = "rewards_program"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_rewards_program_user_name"),
        {"comment": "User-owned rewards programs"},
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(db.String(120), nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(db.String(500), nullable=True)
    portal_url: Mapped[str | None] = mapped_column(db.String(500), nullable=True)
    program_email: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    program_phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="rewards_programs")
    rewards_account: Mapped[RewardsAccount | None] = relationship(
        "RewardsAccount",
        back_populates="rewards_program",
        cascade="all, delete-orphan",
        uselist=False,
    )
    merchant_links: Mapped[list[MerchantRewardsLink]] = relationship(
        "MerchantRewardsLink",
        back_populates="rewards_program",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "website": self.website,
            "portal_url": self.portal_url,
            "program_email": self.program_email,
            "program_phone": self.program_phone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RewardsAccount(BaseModel):
    """Member-specific account details for a rewards program."""

    __tablename__ = "rewards_account"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("user_id", "rewards_program_id", name="uq_rewards_account_user_program"),
        {"comment": "User account details for a rewards program"},
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    rewards_program_id: Mapped[int] = mapped_column(
        ForeignKey("rewards_program.id", ondelete="CASCADE"), nullable=False, index=True
    )
    membership_email: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    membership_phone: Mapped[str | None] = mapped_column(db.String(30), nullable=True)
    portal_username: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    account_number: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    tier_name: Mapped[str | None] = mapped_column(db.String(120), nullable=True)
    points_balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(db.Text, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="rewards_accounts")
    rewards_program: Mapped[RewardsProgram] = relationship("RewardsProgram", back_populates="rewards_account")


class MerchantRewardsLink(BaseModel):
    """Current user's rewards program mapping for a merchant."""

    __tablename__ = "merchant_rewards_link"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("user_id", "merchant_id", name="uq_merchant_rewards_link_user_merchant"),
        {"comment": "User-scoped rewards program assignment for merchants"},
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchant.id", ondelete="CASCADE"), nullable=False, index=True)
    rewards_program_id: Mapped[int] = mapped_column(
        ForeignKey("rewards_program.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user: Mapped[User] = relationship("User", back_populates="merchant_rewards_links")
    merchant: Mapped[Merchant] = relationship("Merchant", back_populates="merchant_rewards_links")
    rewards_program: Mapped[RewardsProgram] = relationship("RewardsProgram", back_populates="merchant_links")
