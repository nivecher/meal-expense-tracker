from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from flask.typing import ResponseReturnValue
from flask_login import UserMixin
from sqlalchemy import Connection, event
from sqlalchemy.orm import Mapped, Mapper, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import LoginManager, db
from app.models.base import BaseModel

if TYPE_CHECKING:
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

    __tablename__ = "user"

    # Override the default id to match the existing schema
    id: Mapped[int] = db.Column(db.Integer, primary_key=True, comment="Primary key for the user")

    # User authentication information
    username: Mapped[str] = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username",
    )
    email: Mapped[str] = db.Column(
        db.String(120),
        unique=True,
        nullable=False,
        index=True,
        comment="User's email address",
    )
    password_hash: Mapped[Optional[str]] = db.Column(db.String(256), nullable=True, comment="Hashed password")

    # User status flags
    is_active: Mapped[bool] = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        comment="Whether the user account is active",
    )
    is_admin: Mapped[bool] = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether the user has admin privileges",
    )

    # Profile fields
    first_name: Mapped[Optional[str]] = db.Column(
        db.String(64),
        nullable=True,
        comment="User's first name",
    )
    last_name: Mapped[Optional[str]] = db.Column(
        db.String(64),
        nullable=True,
        comment="User's last name",
    )
    display_name: Mapped[Optional[str]] = db.Column(
        db.String(128),
        nullable=True,
        comment="User's preferred display name",
    )
    bio: Mapped[Optional[str]] = db.Column(
        db.Text,
        nullable=True,
        comment="User's bio or description",
    )
    avatar_url: Mapped[Optional[str]] = db.Column(
        db.String(255),
        nullable=True,
        comment="URL to user's avatar image",
    )
    phone: Mapped[Optional[str]] = db.Column(
        db.String(20),
        nullable=True,
        comment="User's phone number",
    )
    timezone: Mapped[Optional[str]] = db.Column(
        db.String(50),
        nullable=True,
        default="UTC",
        comment="User's timezone preference",
    )

    # Relationships
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    restaurants: Mapped[List["Restaurant"]] = relationship(
        "Restaurant",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    categories: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
        passive_deletes=True,
    )
    tags: Mapped[List["Tag"]] = relationship(
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
        if not password or not self.password_hash:
            return False

        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        """Return the user ID as a string for Flask-Login."""
        return str(self.id)

    def get_display_name(self) -> str:
        """Get the user's preferred display name.

        Returns:
            The display name if set, otherwise the full name, otherwise the username
        """
        if self.display_name:
            return self.display_name

        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name

        return self.username

    def get_initials(self) -> str:
        """Get user initials for avatar display.

        Returns:
            Two-character initials based on name or username
        """
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        elif self.first_name:
            return self.first_name[:2].upper()
        elif self.display_name:
            parts = self.display_name.split()
            if len(parts) >= 2:
                return f"{parts[0][0]}{parts[1][0]}".upper()
            return self.display_name[:2].upper()

        return self.username[:2].upper()

    def to_dict(self) -> Dict[str, Any]:
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

    def to_token_dict(self) -> Dict[str, Any]:
        """Return a dictionary suitable for JWT token generation.

        Returns:
            Dict containing minimal user data for token claims
        """
        return {
            "user_id": self.id,
            "username": self.username,
            "is_admin": self.is_admin,
        }

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def validate_user(mapper: Mapper, connection: Connection, target: User) -> None:
    """Validate user data before insert/update."""
    # Ensure username is lowercase
    if target.username:
        target.username = target.username.lower().strip()

    # Ensure email is lowercase
    if target.email:
        target.email = target.email.lower().strip()


def init_login_manager(login_manager: LoginManager) -> None:
    """Initialize the login manager with the user loader.

    This function sets up the user loader callback that Flask-Login uses
    to reload the user object from the user ID stored in the session.

    Args:
        login_manager: The Flask-Login LoginManager instance
    """

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """Load a user by ID.

        Args:
            user_id: The user ID as a string from the session

        Returns:
            Optional[User]: The User instance if found and active, None otherwise

        Note:
            Only returns active users. Inactive users are treated as non-existent.
        """
        if not user_id or not user_id.isdigit():
            return None

        user = db.session.get(User, int(user_id))

        # Only return the user if they exist and are active
        if user and user.is_active:
            return user

        return None

    @login_manager.unauthorized_handler
    def unauthorized() -> ResponseReturnValue:
        """Handle unauthorized access attempts.

        Returns:
            Response: A redirect to the login page for HTML requests,
                     or a JSON response for API requests
        """
        from flask import jsonify, redirect, request, url_for

        # Check if the request accepts HTML
        if "text/html" in request.accept_mimetypes:
            return redirect(url_for("auth.login", next=request.url))

        # Default to JSON response for API requests
        return jsonify({"error": "You must be logged in to access this resource"}), 401

    @login_manager.needs_refresh_handler
    def refresh_needed() -> tuple[dict[str, str], int]:
        """Handle session refresh requirements."""
        return {"error": "Session expired, please log in again"}, 401
