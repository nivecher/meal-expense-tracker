from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from flask import Response
from flask_login import UserMixin

# Type alias for Flask route return values
ResponseReturnValue = Union[str, Response, tuple]
from sqlalchemy import event
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

    from app.expenses.models import Category, Expense, Tag
    from app.restaurants.models import Restaurant


class User(BaseModel, UserMixin):
    """User model for authentication and authorization.

    Attributes:
        username: Unique username for the user
        email: Unique email address for the user
        password_hash: Hashed password (never store plaintext passwords!)
        is_active: Whether the user account is active
        is_admin: Whether the user has admin privileges
    """

    __tablename__ = "user"  # type: ignore[assignment]

    # Override the default id to match the existing schema
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, comment="Primary key for the user")

    # User authentication information
    username: Mapped[str] = mapped_column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username",
    )
    email: Mapped[str] = mapped_column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address",
    )
    password_hash: Mapped[str | None] = mapped_column(db.String(256), nullable=True, comment="Hashed password")

    # User status flags
    is_active: Mapped[bool] = mapped_column(
        db.Boolean,
        default=True,
        nullable=False,
        comment="Whether the user account is active",
    )
    is_admin: Mapped[bool] = mapped_column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether the user has admin privileges",
    )

    # Profile fields
    first_name: Mapped[str | None] = mapped_column(
        db.String(64),
        nullable=True,
        comment="User's first name",
    )
    last_name: Mapped[str | None] = mapped_column(
        db.String(64),
        nullable=True,
        comment="User's last name",
    )
    display_name: Mapped[str | None] = mapped_column(
        db.String(128),
        nullable=True,
        comment="User's preferred display name",
    )
    bio: Mapped[str | None] = mapped_column(
        db.Text,
        nullable=True,
        comment="User's bio or description",
    )
    avatar_url: Mapped[str | None] = mapped_column(
        db.String(255),
        nullable=True,
        comment="URL to user's avatar image",
    )
    phone: Mapped[str | None] = mapped_column(
        db.String(20),
        nullable=True,
        comment="User's phone number",
    )
    timezone: Mapped[str | None] = mapped_column(
        db.String(50),
        nullable=True,
        default="UTC",
        comment="User's timezone preference",
    )

    # Relationships
    expenses: Mapped[list[Expense]] = relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    restaurants: Mapped[list[Restaurant]] = relationship(
        "Restaurant",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    categories: Mapped[list[Category]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    tags: Mapped[list[Tag]] = relationship(
        "Tag",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )

    def set_password(self, password: str) -> None:
        """Set the user's password.

        Args:
            password: The plaintext password to hash and store

        Raises:
            ValueError: If password is empty or None
        """
        if not password:
            raise ValueError("Password cannot be empty")

        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the stored hash.

        Args:
            password: The plaintext password to verify

        Returns:
            bool: True if the password matches, False otherwise

        Note:
            Returns False if the user has no password set
        """
        if not password:
            return False
        password_hash = self.password_hash
        if password_hash is None:
            return False
        # After None check, password_hash is guaranteed to be str
        return bool(check_password_hash(password_hash, password))

    def get_id(self) -> str:
        """Return the user ID as a string for Flask-Login."""
        return str(self.id)

    def get_display_name(self) -> str:
        """Get the user's preferred display name.

        Returns:
            The display name if set, otherwise the full name, otherwise the username
        """
        # Check display_name first (explicit None check for type narrowing)
        if self.display_name:
            return self.display_name

        # Check for full name
        first_name = self.first_name
        last_name = self.last_name
        if first_name is not None:
            if last_name is not None:
                return f"{first_name} {last_name}"

        # Check for first name only
        if first_name is not None:
            return first_name

        # Fallback to username (always available, non-optional)
        return self.username

    def get_initials(self) -> str:
        """Get user initials for avatar display.

        Returns:
            Two-character initials based on name or username
        """
        first_name = self.first_name
        last_name = self.last_name
        if first_name is not None:
            if last_name is not None:
                return f"{first_name[0]}{last_name[0]}".upper()
            return first_name[:2].upper()
        elif self.display_name:
            parts = self.display_name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return self.display_name[:2].upper()

        return self.username[:2].upper()

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation of the user.

        Returns:
            Dict containing the user data with sensitive fields removed
        """
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "phone": self.phone,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def validate_user(mapper: Mapper, connection: Connection, target: User) -> None:
    """Validate user data before insert/update."""
    # Ensure username is lowercase (required field, always present)
    target.username = target.username.lower().strip()

    # Ensure email is lowercase (required field, always present)
    target.email = target.email.lower().strip()
