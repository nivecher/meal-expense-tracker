"""Remote administration module for Lambda-based management."""

from .lambda_admin import LambdaAdminHandler
from .operations import AdminOperation, AdminOperationRegistry

__all__ = ["LambdaAdminHandler", "AdminOperation", "AdminOperationRegistry"]
