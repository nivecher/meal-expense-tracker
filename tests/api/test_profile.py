import unittest

from app import create_app
from app.auth.models import User
from app.extensions import db


class ProfileAPITestCase(unittest.TestCase):
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

    def test_get_profile(self):
        response = self.client.get("/api/v1/profile")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["username"], "testuser")

    def test_update_profile(self):
        response = self.client.put(
            "/api/v1/profile",
            json={"username": "newusername", "email": "newemail@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["username"], "newusername")

    def test_change_password(self):
        response = self.client.post(
            "/api/v1/profile/change-password",
            json={"old_password": "testpassword", "new_password": "newpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "success")

        # Verify the new password works
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "newpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "success")
