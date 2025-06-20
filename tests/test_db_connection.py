"""Test database connection in Lambda environment."""

import os
import unittest
from unittest.mock import patch, MagicMock
from app import create_app, db


class TestDatabaseConnection(unittest.TestCase):
    """Test database connection in Lambda environment."""

    def setUp(self):
        """Set up test environment."""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch("boto3.client")
    def test_db_connection_in_lambda(self, mock_boto):
        """Test database connection in Lambda environment."""
        # Mock the Secrets Manager response
        mock_secret = {"SecretString": '{"db_password": "testpassword"}'}
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = mock_secret
        mock_boto.return_value = mock_client

        # Set up Lambda environment
        os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-function"
        os.environ["DB_HOST"] = "test-host"
        os.environ["DB_PORT"] = "5432"
        os.environ["DB_NAME"] = "testdb"
        os.environ["DB_USERNAME"] = "testuser"
        os.environ["DB_SECRET_ARN"] = (
            "arn:aws:secretsmanager:us-west-2:123456789012:secret:test-secret"
        )
        os.environ["AWS_REGION"] = "us-west-2"

        # Create app with test config
        app = create_app("testing")
        with app.app_context():
            # Test database connection using SQLAlchemy 2.0's execution API
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("SELECT 1"))
                    result.scalar()  # Execute the query
                connection_ok = True
            except Exception as e:
                connection_ok = False
                print(f"Database connection failed: {e}")

            self.assertTrue(connection_ok, "Database connection should be successful")


if __name__ == "__main__":
    unittest.main()
