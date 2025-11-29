"""Tests for notification service functions."""

from unittest.mock import Mock, patch

from flask import current_app

from app.services.notification_service import (
    _send_via_sns,
    is_notifications_enabled,
    send_notification,
    send_password_reset_notification,
    send_test_notification,
    send_welcome_notification,
)


class TestNotificationService:
    """Test notification service functions."""

    def test_is_notifications_enabled_true(self, app) -> None:
        """Test is_notifications_enabled when notifications are enabled."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=True):
                result = is_notifications_enabled()
                assert result is True

    def test_is_notifications_enabled_false(self, app) -> None:
        """Test is_notifications_enabled when notifications are disabled."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=False):
                result = is_notifications_enabled()
                assert result is False

    def test_is_notifications_enabled_default_false(self, app) -> None:
        """Test is_notifications_enabled when NOTIFICATIONS_ENABLED is not configured."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=False):
                result = is_notifications_enabled()
                assert result is False

    @patch("boto3.client")
    def test_send_via_sns_success(self, mock_boto_client, app) -> None:
        """Test successful notification sending via SNS."""
        with app.app_context():
            # Mock SNS client
            mock_sns = Mock()
            mock_sns.publish.return_value = {"MessageId": "test-message-id"}
            mock_boto_client.return_value = mock_sns

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "AWS_REGION": "us-east-1",
                }.get(key, default)

                result = _send_via_sns(
                    topic_arn="arn:aws:sns:us-east-1:123456789012:test-topic",
                    subject="Test Subject",
                    message="Test Message",
                )

                assert result is True
                mock_sns.publish.assert_called_once()

    @patch("boto3.client")
    def test_send_via_sns_client_error(self, mock_boto_client, app) -> None:
        """Test SNS notification sending with ClientError."""
        with app.app_context():
            from botocore.exceptions import ClientError

            mock_sns = Mock()
            mock_sns.publish.side_effect = ClientError(
                error_response={"Error": {"Code": "InvalidParameter", "Message": "Invalid topic"}},
                operation_name="Publish",
            )
            mock_boto_client.return_value = mock_sns

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "AWS_REGION": "us-east-1",
                }.get(key, default)

                result = _send_via_sns(
                    topic_arn="arn:aws:sns:us-east-1:123456789012:test-topic",
                    subject="Test Subject",
                    message="Test Message",
                )

                assert result is False

    @patch("boto3.client")
    def test_send_via_sns_generic_error(self, mock_boto_client, app) -> None:
        """Test SNS notification sending with generic error."""
        with app.app_context():
            mock_boto_client.side_effect = Exception("Boto3 error")

            result = _send_via_sns(
                topic_arn="arn:aws:sns:us-east-1:123456789012:test-topic",
                subject="Test Subject",
                message="Test Message",
            )

            assert result is False

    @patch("app.services.notification_service._send_via_sns")
    def test_send_notification_enabled(self, mock_send_sns, app) -> None:
        """Test send_notification when notifications are enabled."""
        with app.app_context():
            with patch("app.services.notification_service.is_notifications_enabled", return_value=True):
                mock_send_sns.return_value = True

                with patch.object(
                    current_app.config, "get", return_value="arn:aws:sns:us-east-1:123456789012:test-topic"
                ):
                    result = send_notification(subject="Test Subject", message="Test Message")

                    assert result is True
                    mock_send_sns.assert_called_once()

    @patch("app.services.notification_service.logger")
    def test_send_notification_disabled(self, mock_logger, app) -> None:
        """Test send_notification when notifications are disabled."""
        with app.app_context():
            with patch("app.services.notification_service.is_notifications_enabled", return_value=False):
                result = send_notification(subject="Test Subject", message="Test Message")

                assert result is False
                mock_logger.warning.assert_called_once()
                mock_logger.info.assert_called_once()

    @patch("app.services.notification_service.send_notification")
    def test_send_password_reset_notification_success(self, mock_send, app) -> None:
        """Test successful password reset notification sending."""
        with app.app_context():
            mock_send.return_value = True

            result = send_password_reset_notification(
                user_email="test@example.com", username="testuser", new_password="newpass123"
            )

            assert result is True
            mock_send.assert_called_once()

    @patch("app.services.notification_service.logger")
    def test_send_password_reset_notification_error(self, mock_logger, app) -> None:
        """Test password reset notification with error."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification", side_effect=Exception("Send error")):
                result = send_password_reset_notification(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is False
                mock_logger.error.assert_called_once()

    @patch("app.services.notification_service.send_notification")
    def test_send_welcome_notification_success(self, mock_send, app) -> None:
        """Test successful welcome notification sending."""
        with app.app_context():
            mock_send.return_value = True

            result = send_welcome_notification(
                user_email="test@example.com", username="testuser", new_password="newpass123"
            )

            assert result is True
            mock_send.assert_called_once()

    @patch("app.services.notification_service.logger")
    def test_send_welcome_notification_error(self, mock_logger, app) -> None:
        """Test welcome notification with error."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification", side_effect=Exception("Send error")):
                result = send_welcome_notification(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is False
                mock_logger.error.assert_called_once()

    @patch("app.services.notification_service.send_notification")
    def test_send_test_notification_success(self, mock_send, app) -> None:
        """Test successful test notification sending."""
        with app.app_context():
            mock_send.return_value = True

            result = send_test_notification("test@example.com")

            assert result is True
            mock_send.assert_called_once()

    @patch("app.services.notification_service.logger")
    def test_send_test_notification_failure(self, mock_logger, app) -> None:
        """Test test notification sending failure."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification", side_effect=Exception("Send error")):
                result = send_test_notification("test@example.com")

                assert result is False
                mock_logger.error.assert_called_once()

    def test_password_reset_notification_content(self, app) -> None:
        """Test that password reset notification contains expected content."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification") as mock_send:
                mock_send.return_value = True

                result = send_password_reset_notification(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is True
                # Verify the call was made with correct parameters
                call_args = mock_send.call_args
                # send_notification is called with positional args: (subject, message)
                assert call_args[0][0] == "Password Reset - Meal Expense Tracker"

    def test_welcome_notification_content(self, app) -> None:
        """Test that welcome notification contains expected content."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification") as mock_send:
                mock_send.return_value = True

                result = send_welcome_notification(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is True
                # Verify the call was made with correct parameters
                call_args = mock_send.call_args
                # send_notification is called with positional args: (subject, message)
                assert call_args[0][0] == "Welcome to Meal Expense Tracker"

    def test_test_notification_content(self, app) -> None:
        """Test that test notification contains expected content."""
        with app.app_context():
            with patch("app.services.notification_service.send_notification") as mock_send:
                mock_send.return_value = True

                result = send_test_notification("test@example.com")

                assert result is True
                # Verify the call was made with correct parameters
                call_args = mock_send.call_args
                # send_notification is called with positional args: (subject, message)
                assert call_args[0][0] == "Test Notification - Meal Expense Tracker"
