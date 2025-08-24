"""Base service classes and utilities for the application."""

from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Query

from app.extensions import db

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType")


class BaseService(Generic[ModelType]):
    """Base service class providing common CRUD operations.

    This class reduces duplication across service modules and provides
    consistent error handling and data validation.
    """

    def __init__(self, model_class: Type[ModelType]):
        """Initialize the service with a model class.

        Args:
            model_class: The SQLAlchemy model class to operate on
        """
        self.model_class = model_class

    def get_by_id(self, item_id: int, user_id: int) -> Optional[ModelType]:
        """Get an item by ID, ensuring it belongs to the user.

        Args:
            item_id: The ID of the item to retrieve
            user_id: The ID of the user who owns the item

        Returns:
            The item if found and belongs to the user, None otherwise
        """
        return self.model_class.query.filter_by(id=item_id, user_id=user_id).first()

    def get_all_for_user(self, user_id: int, **filters) -> List[ModelType]:
        """Get all items for a specific user with optional filters.

        Args:
            user_id: The ID of the user
            **filters: Additional filter criteria

        Returns:
            List of items matching the criteria
        """
        query = self.model_class.query.filter_by(user_id=user_id, **filters)
        return query.all()

    def create(self, user_id: int, data: Dict[str, Any], **kwargs) -> ModelType:
        """Create a new item for a user.

        Args:
            user_id: The ID of the user
            data: The data to create the item with
            **kwargs: Additional keyword arguments

        Returns:
            The created item

        Raises:
            Exception: If creation fails
        """
        try:
            item = self.model_class(user_id=user_id, **data, **kwargs)
            db.session.add(item)
            db.session.commit()
            return item
        except Exception as e:
            db.session.rollback()
            raise e

    def update(self, item: ModelType, data: Dict[str, Any]) -> ModelType:
        """Update an existing item.

        Args:
            item: The item to update
            data: The data to update the item with

        Returns:
            The updated item

        Raises:
            Exception: If update fails
        """
        try:
            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)

            db.session.commit()
            return item
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self, item: ModelType) -> None:
        """Delete an item.

        Args:
            item: The item to delete

        Raises:
            Exception: If deletion fails
        """
        try:
            db.session.delete(item)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def exists(self, user_id: int, **criteria) -> bool:
        """Check if an item exists for a user.

        Args:
            user_id: The ID of the user
            **criteria: Additional criteria to check

        Returns:
            True if item exists, False otherwise
        """
        return self.model_class.query.filter_by(user_id=user_id, **criteria).first() is not None

    def count_for_user(self, user_id: int, **filters) -> int:
        """Count items for a user with optional filters.

        Args:
            user_id: The ID of the user
            **filters: Additional filter criteria

        Returns:
            The count of items
        """
        return self.model_class.query.filter_by(user_id=user_id, **filters).count()

    def get_query(self, user_id: int) -> Query:
        """Get a base query for a user.

        Args:
            user_id: The ID of the user

        Returns:
            A SQLAlchemy query object
        """
        return self.model_class.query.filter_by(user_id=user_id)
