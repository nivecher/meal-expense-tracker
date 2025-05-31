from typing import Optional
from fastapi import Request, HTTPException
from app.models import User


async def get_current_user(request: Optional[Request] = None) -> User:
    """Get the current user from the request."""
    if request is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # ... existing code ...


async def get_current_active_user(request: Optional[Request] = None) -> User:
    """Get the current active user from the request."""
    if request is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    # ... existing code ...
