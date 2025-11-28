"""Base model class with SQLAlchemy type hints."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Type, TypeAlias, TypeVar, cast

from flask_sqlalchemy.model import DefaultMeta
from sqlalchemy.orm import Mapped, Session as _Session, mapped_column
from sqlalchemy.sql import func

from ..extensions import db as _db

# Type variable for model classes
ModelType = TypeVar("ModelType", bound="BaseModel")

# Type alias for SQLAlchemy session
SessionType: TypeAlias = _Session

# Re-export commonly used types for convenience
Column = _db.Column
relationship = _db.relationship
backref = _db.backref

# Type for SQLAlchemy model base
if TYPE_CHECKING:
    Model = _db.Model
else:
    # At runtime, use the actual model
    Model = cast(DefaultMeta, _db.Model)


class BaseModel(Model):  # type: ignore
    """Base model class with common functionality for all models.

    This class extends Flask-SQLAlchemy's Model class and adds common fields and methods.
    """

    __abstract__ = True

    # Common columns for all models
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        _db.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when the record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        _db.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when the record was last updated",
    )

    @_db.declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically.

        Converts CamelCase class names to snake_case table names.

        Returns:
            str: The table name in snake_case based on the class name
        """
        import re

        # Convert CamelCase to snake_case
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        result: dict[str, Any] = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Handle datetime serialization
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            result[column.name] = value
        return result

    @classmethod
    def from_dict(cls: type[ModelType], data: dict[str, Any], **kwargs: Any) -> ModelType:
        """Create model instance from dictionary.

        Args:
            data: Dictionary containing model data
            **kwargs: Additional keyword arguments to pass to the model constructor

        Returns:
            ModelType: An instance of the model
        """
        # Get the table columns
        columns = {c.name for c in cls.__table__.columns}

        # Filter data to only include valid columns
        filtered_data = {k: v for k, v in data.items() if k in columns}

        # Create and return the model instance
        return cls(**filtered_data, **kwargs)

    def save(self, commit: bool = True) -> None:
        """Save the current model instance to the database.

        Args:
            commit: If True, commit the transaction. Set to False if you want to
                   add multiple objects in a single transaction.
        """
        _db.session.add(self)
        if commit:
            try:
                _db.session.commit()
            except Exception as e:
                _db.session.rollback()
                raise e

    def delete(self, commit: bool = True) -> None:
        """Delete the current model instance from the database.

        Args:
            commit: If True, commit the transaction. Set to False if you want to
                   delete multiple objects in a single transaction.
        """
        _db.session.delete(self)
        if commit:
            try:
                _db.session.commit()
            except Exception as e:
                _db.session.rollback()
                raise e
