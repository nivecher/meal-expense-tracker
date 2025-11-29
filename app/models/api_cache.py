"""API cache model for storing Google Places API responses.

This model provides persistent caching using the existing PostgreSQL database,
avoiding the need for external caching infrastructure like Redis.

Following TIGER principles:
- Testing: Simple model that's easy to test
- Interfaces: Standard SQLAlchemy model interface
- Generality: Reusable caching model for any API responses
- Examples: Clear usage examples for caching operations
- Refactoring: Single responsibility for API response caching
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.base import BaseModel


class APICache(BaseModel):
    """Model for caching API responses in the database."""

    __tablename__ = "api_cache"  # type: ignore[assignment]

    # Override BaseModel's created_at/updated_at to use Float instead of DateTime
    created_at: Mapped[float] = mapped_column(  # type: ignore[assignment]
        db.Float, nullable=False, comment="Cache creation timestamp"
    )
    updated_at: Mapped[float] = mapped_column(  # type: ignore[assignment]
        db.Float, nullable=False, comment="Cache update timestamp"
    )

    key: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True, comment="Cache key")
    data: Mapped[str] = mapped_column(db.Text, nullable=False, comment="Cached API response data")

    def __repr__(self) -> str:
        return f"<APICache {self.key}>"

    @classmethod
    def create_cache_entry(cls, key: str, data: str) -> APICache:
        """Create a new cache entry."""
        import time

        current_time = time.time()
        instance = cls(key=key, data=data, created_at=current_time, updated_at=current_time)
        return instance

    @classmethod
    def get_by_key(cls, key: str) -> APICache | None:
        """Get cache entry by key."""
        stmt = select(cls).filter_by(key=key)
        result = db.session.scalar(stmt)
        if result is None:
            return None
        return result

    @classmethod
    def clear_expired(cls, ttl_seconds: int) -> int:
        """Clear expired cache entries."""
        import time

        cutoff_time = time.time() - ttl_seconds
        stmt = select(cls).where(cls.updated_at < cutoff_time)
        expired_entries = list(db.session.scalars(stmt).all())

        count = len(expired_entries)
        for entry in expired_entries:
            db.session.delete(entry)

        db.session.commit()
        return count

    @classmethod
    def clear_all(cls) -> int:
        """Clear all cache entries."""
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(cls)
        count_result = db.session.scalar(count_stmt)
        count = int(count_result) if count_result else 0

        delete_stmt = db.delete(cls)
        db.session.execute(delete_stmt)
        db.session.commit()
        return count
