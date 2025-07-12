"""Test script for Google Places sync functionality."""

import os
import unittest

from flask import url_for

from app import create_app, db
from app.auth.models import User
from app.restaurants.models import Restaurant
from tests.test_config import TestConfig

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_USERNAME = os.getenv("TEST_USERNAME", "testuser")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "testpassword123")
GOOGLE_PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"  # Google's Mountain View office


class TestGooglePlacesSync(unittest.TestCase):
    """Test Google Places sync functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client(use_cookies=True)

        # Create test user
        with self.app.app_context():
            user = User(username="testuser")
            user.set_password("testpassword123")
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_google_places_sync(self):
        """Test the Google Places sync functionality."""
        with self.app.app_context():
            # Create a test restaurant with a Google Place ID
            test_restaurant = Restaurant(
                name="Test Restaurant",
                google_place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",  # Google's Sydney office
                user_id=1,
            )
            db.session.add(test_restaurant)
            db.session.commit()

            # Get the restaurant ID after commit
            restaurant_id = test_restaurant.id

        # Log in and make the request within the test client context
        with self.client as c:
            # Log in
            c.post(
                url_for("auth.login"), data=dict(username="testuser", password="testpassword123"), follow_redirects=True
            )

            # Call the sync endpoint
            response = c.post(url_for("restaurants.sync_google_places", id=restaurant_id), follow_redirects=True)

            self.assertEqual(response.status_code, 200)

            # Verify the restaurant was updated with Google Places data
            with self.app.app_context():
                updated_restaurant = Restaurant.query.get(restaurant_id)
                self.assertIsNotNone(updated_restaurant.address)
                self.assertIsNotNone(updated_restaurant.latitude)
                self.assertIsNotNone(updated_restaurant.longitude)


if __name__ == "__main__":
    unittest.main()
