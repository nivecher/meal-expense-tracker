"""Tests for email service functions."""

from unittest.mock import Mock, patch

from flask import current_app

from app.services.email_service import (
    _send_email,
    _send_via_ses,
    is_email_enabled,
    send_password_reset_email,
    send_test_email,
    send_welcome_email,
)


class TestEmailService:
    """Test email service functions."""

    def test_is_email_enabled_true(self, app):
        """Test is_email_enabled when email is enabled."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=True):
                result = is_email_enabled()
                assert result is True

    def test_is_email_enabled_false(self, app):
        """Test is_email_enabled when email is disabled."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=False):
                result = is_email_enabled()
                assert result is False

    def test_is_email_enabled_default_false(self, app):
        """Test is_email_enabled when MAIL_ENABLED is not configured."""
        with app.app_context():
            with patch.object(current_app.config, "get", return_value=False):
                result = is_email_enabled()
                assert result is False

    @patch("boto3.client")
    def test_send_via_ses_success(self, mock_boto_client, app):
        """Test successful email sending via SES."""
        with app.app_context():
            # Mock SES client
            mock_ses = Mock()
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
            mock_boto_client.return_value = mock_ses

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "AWS_SES_REGION": "us-east-1",
                    "MAIL_DEFAULT_SENDER": "noreply@example.com",
                }.get(key, default)

                result = _send_via_ses(
                    to_addresses=["test@example.com"],
                    subject="Test Subject",
                    html_body="<h1>Test</h1>",
                    text_body="Test",
                )

                assert result is True
                mock_ses.send_email.assert_called_once()

    @patch("boto3.client")
    def test_send_via_ses_without_text_body(self, mock_boto_client, app):
        """Test SES email sending without text body."""
        with app.app_context():
            mock_ses = Mock()
            mock_ses.send_email.return_value = {"MessageId": "test-message-id"}
            mock_boto_client.return_value = mock_ses

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "AWS_SES_REGION": "us-east-1",
                    "MAIL_DEFAULT_SENDER": "noreply@example.com",
                }.get(key, default)

                result = _send_via_ses(
                    to_addresses=["test@example.com"], subject="Test Subject", html_body="<h1>Test</h1>"
                )

                assert result is True
                call_args = mock_ses.send_email.call_args
                # Should not have Text body
                body = call_args[1]["Message"]["Body"]
                assert "Html" in body
                assert "Text" not in body

    @patch("boto3.client")
    def test_send_via_ses_client_error(self, mock_boto_client, app):
        """Test SES email sending with ClientError."""
        with app.app_context():
            from botocore.exceptions import ClientError

            mock_ses = Mock()
            mock_ses.send_email.side_effect = ClientError(
                error_response={"Error": {"Code": "MessageRejected", "Message": "Email rejected"}},
                operation_name="SendEmail",
            )
            mock_boto_client.return_value = mock_ses

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {
                    "AWS_SES_REGION": "us-east-1",
                    "MAIL_DEFAULT_SENDER": "noreply@example.com",
                }.get(key, default)

                result = _send_via_ses(
                    to_addresses=["test@example.com"], subject="Test Subject", html_body="<h1>Test</h1>"
                )

                assert result is False

    @patch("boto3.client")
    def test_send_via_ses_generic_error(self, mock_boto_client, app):
        """Test SES email sending with generic error."""
        with app.app_context():
            mock_boto_client.side_effect = Exception("Boto3 error")

            result = _send_via_ses(to_addresses=["test@example.com"], subject="Test Subject", html_body="<h1>Test</h1>")

            assert result is False

    @patch("app.services.email_service._send_via_ses")
    def test_send_email_enabled(self, mock_send_ses, app):
        """Test _send_email when email is enabled."""
        with app.app_context():
            with patch("app.services.email_service.is_email_enabled", return_value=True):
                mock_send_ses.return_value = True

                result = _send_email(
                    to_addresses=["test@example.com"], subject="Test Subject", html_body="<h1>Test</h1>"
                )

                assert result is True
                mock_send_ses.assert_called_once()

    @patch("app.services.email_service.logger")
    def test_send_email_disabled(self, mock_logger, app):
        """Test _send_email when email is disabled."""
        with app.app_context():
            with patch("app.services.email_service.is_email_enabled", return_value=False):
                result = _send_email(
                    to_addresses=["test@example.com"], subject="Test Subject", html_body="<h1>Test</h1>"
                )

                assert result is False
                mock_logger.warning.assert_called_once()
                mock_logger.info.assert_called_once()

    @patch("app.services.email_service._send_email")
    @patch("app.services.email_service.render_template")
    def test_send_password_reset_email_success(self, mock_render, mock_send, app):
        """Test successful password reset email sending."""
        with app.app_context():
            mock_render.return_value = "<h1>Password Reset</h1>"
            mock_send.return_value = True

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                result = send_password_reset_email(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is True
                mock_render.assert_called_once()
                mock_send.assert_called_once()

    @patch("app.services.email_service._send_email")
    @patch("app.services.email_service.render_template")
    def test_send_password_reset_email_template_error(self, mock_render, mock_send, app):
        """Test password reset email with template rendering error."""
        with app.app_context():
            mock_render.side_effect = Exception("Template error")

            with patch("app.services.email_service.logger") as mock_logger:
                result = send_password_reset_email(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is False
                mock_logger.error.assert_called_once()

    @patch("app.services.email_service._send_email")
    @patch("app.services.email_service.render_template")
    def test_send_welcome_email_success(self, mock_render, mock_send, app):
        """Test successful welcome email sending."""
        with app.app_context():
            mock_render.return_value = "<h1>Welcome</h1>"
            mock_send.return_value = True

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                result = send_welcome_email(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is True
                mock_render.assert_called_once()
                mock_send.assert_called_once()

    @patch("app.services.email_service._send_email")
    @patch("app.services.email_service.render_template")
    def test_send_welcome_email_template_error(self, mock_render, mock_send, app):
        """Test welcome email with template rendering error."""
        with app.app_context():
            mock_render.side_effect = Exception("Template error")

            with patch("app.services.email_service.logger") as mock_logger:
                result = send_welcome_email(
                    user_email="test@example.com", username="testuser", new_password="newpass123"
                )

                assert result is False
                mock_logger.error.assert_called_once()

    @patch("app.services.email_service._send_email")
    def test_send_test_email_success(self, mock_send, app):
        """Test successful test email sending."""
        with app.app_context():
            mock_send.return_value = True

            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                result = send_test_email("test@example.com")

                assert result is True
                mock_send.assert_called_once()

    @patch("app.services.email_service._send_email")
    def test_send_test_email_failure(self, mock_send, app):
        """Test test email sending failure."""
        with app.app_context():
            mock_send.side_effect = Exception("Send error")

            with patch("app.services.email_service.logger") as mock_logger:
                result = send_test_email("test@example.com")

                assert result is False
                mock_logger.error.assert_called_once()

    def test_password_reset_email_content(self, app):
        """Test that password reset email contains expected content."""
        with app.app_context():
            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                # We can't easily test the full content without mocking render_template,
                # but we can test the function structure
                with patch("app.services.email_service._send_email") as mock_send:
                    mock_send.return_value = True

                    result = send_password_reset_email(
                        user_email="test@example.com", username="testuser", new_password="newpass123"
                    )

                    assert result is True
                    # Verify the call was made with correct parameters
                    call_args = mock_send.call_args
                    assert call_args[1]["to_addresses"] == ["test@example.com"]
                    assert call_args[1]["subject"] == "Password Reset - Meal Expense Tracker"

    def test_welcome_email_content(self, app):
        """Test that welcome email contains expected content."""
        with app.app_context():
            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                with patch("app.services.email_service._send_email") as mock_send:
                    mock_send.return_value = True

                    result = send_welcome_email(
                        user_email="test@example.com", username="testuser", new_password="newpass123"
                    )

                    assert result is True
                    # Verify the call was made with correct parameters
                    call_args = mock_send.call_args
                    assert call_args[1]["to_addresses"] == ["test@example.com"]
                    assert call_args[1]["subject"] == "Welcome to Meal Expense Tracker"

    def test_test_email_content(self, app):
        """Test that test email contains expected content."""
        with app.app_context():
            with patch.object(current_app.config, "get") as mock_config:
                mock_config.side_effect = lambda key, default=None: {"APP_NAME": "Test App"}.get(key, default)

                with patch("app.services.email_service._send_email") as mock_send:
                    mock_send.return_value = True

                    result = send_test_email("test@example.com")

                    assert result is True
                    # Verify the call was made with correct parameters
                    call_args = mock_send.call_args
                    assert call_args[1]["to_addresses"] == ["test@example.com"]
                    assert call_args[1]["subject"] == "Test Email - Meal Expense Tracker"
                    assert "Test App" in call_args[1]["html_body"]
