import unittest

from app import create_app
from app.auth.models import User
from app.extensions import db
from app.restaurants.models import Restaurant


class RestaurantAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Create a user
        self.user = User(username="testuser", email="test@example.com")
        self.user.set_password("testpassword")
        db.session.add(self.user)
        db.session.commit()

        # Log in
        self.client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "testpassword"},
        )

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_create_restaurant(self):
        response = self.client.post(
            "/api/v1/restaurants",
            json={"name": "Test Restaurant", "cuisine": "Test Cuisine"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], "Test Restaurant")

    def test_create_restaurant_invalid_data(self):
        response = self.client.post(
            "/api/v1/restaurants",
            json={
                "cuisine": "Test Cuisine"
                # Missing required fields
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_get_restaurants(self):
        # Create a restaurant
        restaurant = Restaurant(name="Test Restaurant", user_id=self.user.id)
        db.session.add(restaurant)
        db.session.commit()

        response = self.client.get("/api/v1/restaurants")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)

    def test_get_restaurant(self):
        # Create a restaurant
        restaurant = Restaurant(name="Test Restaurant", user_id=self.user.id)
        db.session.add(restaurant)
        db.session.commit()

        response = self.client.get(f"/api/v1/restaurants/{restaurant.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Test Restaurant")

    def test_update_restaurant(self):
        # Create a restaurant
        restaurant = Restaurant(name="Test Restaurant", user_id=self.user.id)
        db.session.add(restaurant)
        db.session.commit()

        response = self.client.put(
            f"/api/v1/restaurants/{restaurant.id}",
            json={"name": "Updated Restaurant", "cuisine": "Updated Cuisine"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Updated Restaurant")

    def test_delete_restaurant(self):
        # Create a restaurant
        restaurant = Restaurant(name="Test Restaurant", user_id=self.user.id)
        db.session.add(restaurant)
        db.session.commit()

        response = self.client.delete(f"/api/v1/restaurants/{restaurant.id}")
        self.assertEqual(response.status_code, 204)

        # Verify the restaurant is deleted
        response = self.client.get(f"/api/v1/restaurants/{restaurant.id}")
        self.assertEqual(response.status_code, 404)

    def test_access_other_user_restaurant(self):
        # Create another user
        other_user = User(username="otheruser", email="other@example.com")
        other_user.set_password("otherpassword")
        db.session.add(other_user)
        db.session.commit()

        # Create a restaurant for the other user
        restaurant = Restaurant(name="Other Users Restaurant", user_id=other_user.id)
        db.session.add(restaurant)
        db.session.commit()

        # Try to access the restaurant as the original user
        response = self.client.get(f"/api/v1/restaurants/{restaurant.id}")
        self.assertEqual(response.status_code, 404)
