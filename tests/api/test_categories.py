import unittest

from app import create_app
from app.auth.models import User
from app.expenses.models import Category
from app.extensions import db


class CategoryAPITestCase(unittest.TestCase):
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

    def test_create_category(self):
        response = self.client.post(
            "/api/v1/categories",
            json={"name": "Test Category", "description": "A test category"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["name"], "Test Category")

    def test_create_category_invalid_data(self):
        response = self.client.post("/api/v1/categories", json={"description": "This should fail"})
        self.assertEqual(response.status_code, 400)

    def test_get_categories(self):
        # Create a category
        category = Category(name="Test Category", user_id=self.user.id)
        db.session.add(category)
        db.session.commit()

        response = self.client.get("/api/v1/categories")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)

    def test_get_category(self):
        # Create a category
        category = Category(name="Test Category", user_id=self.user.id)
        db.session.add(category)
        db.session.commit()

        response = self.client.get(f"/api/v1/categories/{category.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Test Category")

    def test_update_category(self):
        # Create a category
        category = Category(name="Test Category", user_id=self.user.id)
        db.session.add(category)
        db.session.commit()

        response = self.client.put(
            f"/api/v1/categories/{category.id}",
            json={"name": "Updated Category", "description": "An updated category"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["name"], "Updated Category")

    def test_delete_category(self):
        # Create a category
        category = Category(name="Test Category", user_id=self.user.id)
        db.session.add(category)
        db.session.commit()

        response = self.client.delete(f"/api/v1/categories/{category.id}")
        self.assertEqual(response.status_code, 204)

        # Verify the category is deleted
        response = self.client.get(f"/api/v1/categories/{category.id}")
        self.assertEqual(response.status_code, 404)

    def test_access_other_user_category(self):
        # Create another user
        other_user = User(username="otheruser", email="other@example.com")
        other_user.set_password("otherpassword")
        db.session.add(other_user)
        db.session.commit()

        # Create a category for the other user
        category = Category(name="Other Users Category", user_id=other_user.id)
        db.session.add(category)
        db.session.commit()

        # Try to access the category as the original user
        response = self.client.get(f"/api/v1/categories/{category.id}")
        self.assertEqual(response.status_code, 404)
