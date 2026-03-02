from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.expenses.models import Expense
    from app.restaurants.models import Restaurant
    from app.visits.models import Visit


class Receipt(BaseModel):
    """Receipt model for structured receipt management.

    Replaces the attachment-only model with a structured receipt entity.
    Supports OCR data and flexible linking to expenses, restaurants, or visits.

    Attributes:
        expense_id: Optional link to an expense
        restaurant_id: Optional link to a restaurant
        visit_id: Optional link to a visit
        user_id: Required link to the user who owns this receipt
        file_uri: S3 path to the receipt file
        receipt_type: Type of receipt (paper, email, app, pdf, unknown)
        ocr_total: Total amount extracted via OCR
        ocr_tax: Tax amount extracted via OCR
        ocr_tip: Tip amount extracted via OCR
        ocr_confidence: Confidence score for OCR extraction
    """

    __tablename__ = "receipt"  # type: ignore[assignment]
    __table_args__ = {"comment": "Structured receipt data with OCR information"}

    # Receipt details
    expense_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("expense.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to an expense",
    )
    restaurant_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("restaurant.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to a restaurant",
    )
    visit_id: Mapped[int | None] = mapped_column(
        db.Integer,
        ForeignKey("visit.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to a visit",
    )
    user_id: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who owns this receipt",
    )
    file_uri: Mapped[str] = mapped_column(
        db.String(255),
        nullable=False,
        comment="S3 path to the receipt file",
    )
    receipt_type: Mapped[str | None] = mapped_column(
        db.String(20),
        nullable=True,
        index=True,
        comment="Type of receipt (paper, email, app, pdf, unknown)",
    )
    ocr_total: Mapped[Decimal | None] = mapped_column(
        db.Numeric(10, 2),
        nullable=True,
        comment="Total amount extracted via OCR",
    )
    ocr_tax: Mapped[Decimal | None] = mapped_column(
        db.Numeric(10, 2),
        nullable=True,
        comment="Tax amount extracted via OCR",
    )
    ocr_tip: Mapped[Decimal | None] = mapped_column(
        db.Numeric(10, 2),
        nullable=True,
        comment="Tip amount extracted via OCR",
    )
    ocr_confidence: Mapped[Decimal | None] = mapped_column(
        db.Numeric(5, 4),
        nullable=True,
        comment="Confidence score for OCR extraction",
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="receipts", lazy="select")
    expense: Mapped[Expense | None] = relationship("Expense", back_populates="receipt", lazy="select")
    restaurant: Mapped[Restaurant | None] = relationship("Restaurant", lazy="select")
    visit: Mapped[Visit | None] = relationship("Visit", lazy="select")

    @property
    def has_ocr_data(self) -> bool:
        """Check if receipt has any OCR data.

        Returns:
            True if any OCR field is populated, False otherwise
        """
        return self.ocr_total is not None or self.ocr_tax is not None or self.ocr_tip is not None

    @property
    def ocr_summary(self) -> dict[str, Any]:
        """Get a summary of OCR data.

        Returns:
            Dict containing OCR data summary
        """
        return {
            "has_ocr_data": self.has_ocr_data,
            "total": float(self.ocr_total) if self.ocr_total is not None else None,
            "tax": float(self.ocr_tax) if self.ocr_tax is not None else None,
            "tip": float(self.ocr_tip) if self.ocr_tip is not None else None,
            "confidence": float(self.ocr_confidence) if self.ocr_confidence is not None else None,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the receipt.

        Returns:
            Dict containing receipt data with OCR summary
        """
        result: dict[str, Any] = {
            "id": self.id,
            "expense_id": self.expense_id,
            "restaurant_id": self.restaurant_id,
            "visit_id": self.visit_id,
            "user_id": self.user_id,
            "file_uri": self.file_uri,
            "receipt_type": self.receipt_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        # Include OCR fields
        result.update(
            {
                "ocr_total": float(self.ocr_total) if self.ocr_total is not None else None,
                "ocr_tax": float(self.ocr_tax) if self.ocr_tax is not None else None,
                "ocr_tip": float(self.ocr_tip) if self.ocr_tip is not None else None,
                "ocr_confidence": float(self.ocr_confidence) if self.ocr_confidence is not None else None,
            }
        )

        # Include OCR summary
        result["ocr_summary"] = self.ocr_summary

        return result

    def __repr__(self) -> str:
        return f"<Receipt(id={self.id}, file_uri='{self.file_uri}', user_id={self.user_id})>"
