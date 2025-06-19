"""
Main application module for Meal Expense Tracker.

This module initializes the Flask application and sets up logging.
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize routes and other application components
# This file is kept as an entry point for the application package
