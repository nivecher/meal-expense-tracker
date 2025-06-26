"""Logging configuration and utilities for the Meal Expense Tracker application."""

import logging
import logging.config
import os
from typing import Any, Dict, Optional

from flask import has_request_context, request


def configure_logging() -> None:
    """Configure logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    use_json = os.getenv("LOG_AS_JSON", "").lower() == "true"

    # Default log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if has_request_context():
        log_format += " [%(request_id)s]"

    # Configure formatters
    formatters = {
        "default": {
            "format": log_format,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }

    # Add JSON formatter if requested and available
    formatter_name = "default"
    if use_json:
        try:
            import pythonjsonlogger.jsonlogger

            formatters["json"] = {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            }
            formatter_name = "json"
        except ImportError:
            import warnings

            warnings.warn(
                "python-json-logger not installed, falling back to default formatter. "
                "Install it with: pip install python-json-logger"
            )

    # Configure logging
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "filters": {"request_context": {"()": "app.core.utils.logging.RequestContextFilter"}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": formatter_name,
                    "filters": ["request_context"],
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": log_level, "handlers": ["console"], "propagate": False},
            "loggers": {
                "app": {"level": log_level, "propagate": False},
                "gunicorn": {"level": log_level, "propagate": False},
                "werkzeug": {"level": "WARNING", "propagate": False},
                "sqlalchemy": {"level": "WARNING", "propagate": False},
                "boto3": {"level": "WARNING", "propagate": False},
                "botocore": {"level": "WARNING", "propagate": False},
                "urllib3": {"level": "WARNING", "propagate": False},
            },
        }
    )


class RequestContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add request context to log record if available."""
        try:
            if has_request_context() and hasattr(request, "headers"):
                record.request_id = request.headers.get("X-Request-ID", "-")
            else:
                record.request_id = "-"
        except RuntimeError:
            record.request_id = "-"
        if has_request_context():
            record.path = request.path
            record.method = request.method
            record.remote_addr = request.remote_addr
        else:
            record.path = ""
            record.method = ""
            record.remote_addr = ""
        return True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name. If None, returns the root logger.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    return logger


class StructuredLogger:
    """Structured logger that adds context to log messages."""

    def __init__(self, name: str):
        """Initialize the structured logger.

        Args:
            name: Logger name
        """
        self.logger = get_logger(name)
        self.base_extra: Dict[str, Any] = {}

    def bind(self, **kwargs: Any) -> "StructuredLogger":
        """Add context to all subsequent log messages.

        Args:
            **kwargs: Key-value pairs to add to log context

        Returns:
            Self for method chaining
        """
        self.base_extra.update(kwargs)
        return self

    def _get_extra(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get extra context for log message.

        Args:
            extra: Additional context for this log message

        Returns:
            Combined context dictionary
        """
        if extra is None:
            return self.base_extra.copy()
        return {**self.base_extra, **extra}

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(msg, extra={"extra": self._get_extra(kwargs)})

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(msg, extra={"extra": self._get_extra(kwargs)})

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(msg, extra={"extra": self._get_extra(kwargs)})

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(msg, extra={"extra": self._get_extra(kwargs)})

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        self.logger.exception(msg, extra={"extra": self._get_extra(kwargs)})

    def critical(self, msg: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self.logger.critical(msg, extra={"extra": self._get_extra(kwargs)})
