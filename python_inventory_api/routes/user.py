from app.security import HashedPassword
from app.models import User
from app.schemas import UserCreate


def create_user(user: UserCreate) -> User:
    """Create a new user."""
    hashed_password = HashedPassword(user.password)
    db_user = User(username=user.username, password=hashed_password, email=user.email)
    # ... existing code ...
