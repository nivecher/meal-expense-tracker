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

from app.extensions import db


class APICache(db.Model):
    """Model for caching API responses in the database."""

    __tablename__ = "api_cache"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<APICache {self.key}>"

    @classmethod
    def create_cache_entry(cls, key: str, data: str) -> "APICache":
        """Create a new cache entry."""
        import time

        current_time = time.time()
        return cls(key=key, data=data, created_at=current_time, updated_at=current_time)

    @classmethod
    def get_by_key(cls, key: str) -> "APICache":
        """Get cache entry by key."""
        return cls.query.filter_by(key=key).first()

    @classmethod
    def clear_expired(cls, ttl_seconds: int) -> int:
        """Clear expired cache entries."""
        import time

        cutoff_time = time.time() - ttl_seconds
        expired_entries = cls.query.filter(cls.updated_at < cutoff_time).all()

        count = len(expired_entries)
        for entry in expired_entries:
            db.session.delete(entry)

        db.session.commit()
        return count

    @classmethod
    def clear_all(cls) -> int:
        """Clear all cache entries."""
        count = cls.query.count()
        cls.query.delete()
        db.session.commit()
        return count
