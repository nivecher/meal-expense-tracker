"""Security-related functionality for the application.

This package contains modules for handling security-related functionality
such as secret management, password generation, and other security utilities.
"""

from .secret_rotation import generate_password, get_secret_dict  # noqa: F401

__all__ = ["generate_password", "get_secret_dict"]
