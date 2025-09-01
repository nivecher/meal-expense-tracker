"""Email service for sending notifications and password resets via AWS SES."""

import logging
from typing import Optional

from flask import current_app, render_template

logger = logging.getLogger(__name__)


def is_email_enabled() -> bool:
    """Check if email functionality is enabled.

    Returns:
        True if email is enabled and configured, False otherwise
    """
    return current_app.config.get("MAIL_ENABLED", False)


def _send_via_ses(to_addresses: list[str], subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send email via AWS SES using IAM roles.

    Args:
        to_addresses: List of recipient email addresses
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Configure SES client using IAM role (default and recommended)
        ses_client = boto3.client("ses", region_name=current_app.config.get("AWS_SES_REGION", "us-east-1"))

        # Prepare message body
        body = {"Html": {"Data": html_body, "Charset": "UTF-8"}}
        if text_body:
            body["Text"] = {"Data": text_body, "Charset": "UTF-8"}

        # Send email via SES
        response = ses_client.send_email(
            Source=current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@nivecher.com"),
            Destination={"ToAddresses": to_addresses},
            Message={"Subject": {"Data": subject, "Charset": "UTF-8"}, "Body": body},
        )

        logger.info(f"Email sent via SES: {response['MessageId']}")
        return True

    except ClientError as e:
        logger.error(f"AWS SES error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send email via SES: {e}")
        return False


def _send_email(to_addresses: list[str], subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
    """Send email using AWS SES.

    Args:
        to_addresses: List of recipient email addresses
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text email body (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    if not is_email_enabled():
        logger.warning("Email is disabled, logging message instead")
        logger.info(f"Email would be sent to {to_addresses}: {subject}")
        return False

    # Send via AWS SES
    return _send_via_ses(to_addresses, subject, html_body, text_body)


def send_password_reset_email(user_email: str, username: str, new_password: str) -> bool:
    """Send password reset email to user.

    Args:
        user_email: User's email address
        username: User's username
        new_password: The new password to send

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Render email template
        html_body = render_template(
            "emails/password_reset.html",
            username=username,
            new_password=new_password,
            app_name=current_app.config.get("APP_NAME", "Meal Expense Tracker"),
        )

        # Create plain text version
        text_body = f"""
Password Reset - {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}

Hello {username},

Your password has been reset by an administrator.

Your new temporary password is: {new_password}

IMPORTANT SECURITY NOTICE:
- Please change this password immediately after logging in
- This is a temporary password and should not be shared
- If you did not request this password reset, please contact support immediately

To change your password:
1. Log in with the temporary password above
2. Go to your profile settings
3. Click "Change Password"
4. Enter a new secure password

Best regards,
The {current_app.config.get('APP_NAME', 'Meal Expense Tracker')} Team
        """.strip()

        # Send email
        success = _send_email(
            to_addresses=[user_email],
            subject="Password Reset - Meal Expense Tracker",
            html_body=html_body,
            text_body=text_body,
        )

        if success:
            logger.info(f"Password reset email sent to {user_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {e}")
        return False


def send_welcome_email(user_email: str, username: str, new_password: str) -> bool:
    """Send welcome email to new user.

    Args:
        user_email: User's email address
        username: User's username
        new_password: The new password to send

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        # Render email template
        html_body = render_template(
            "emails/welcome.html",
            username=username,
            new_password=new_password,
            app_name=current_app.config.get("APP_NAME", "Meal Expense Tracker"),
        )

        # Create plain text version
        text_body = f"""
Welcome to {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}!

Hello {username},

Welcome to the Meal Expense Tracker! Your account has been created by an administrator.

Your login credentials:
Username: {username}
Password: {new_password}

IMPORTANT SECURITY NOTICE:
- Please change this password immediately after your first login
- This is a temporary password and should not be shared
- Keep your login credentials secure

Getting Started:
1. Log in with the credentials above
2. Change your password in profile settings
3. Start tracking your meal expenses
4. Explore the analytics and reporting features

Features:
- Track meal expenses with detailed categorization
- Manage restaurant information and preferences
- Generate expense reports and analytics
- Google Maps integration for location services

If you have any questions, please don't hesitate to contact support.

Best regards,
The {current_app.config.get('APP_NAME', 'Meal Expense Tracker')} Team
        """.strip()

        # Send email
        success = _send_email(
            to_addresses=[user_email],
            subject="Welcome to Meal Expense Tracker",
            html_body=html_body,
            text_body=text_body,
        )

        if success:
            logger.info(f"Welcome email sent to {user_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send welcome email to {user_email}: {e}")
        return False


def send_test_email(recipient_email: str) -> bool:
    """Send a test email to verify email configuration.

    Args:
        recipient_email: Email address to send test email to

    Returns:
        True if email was sent successfully, False otherwise
    """
    try:
        html_body = f"""
        <html>
        <body>
            <h2>Test Email - {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}</h2>
            <p>This is a test email to verify email configuration.</p>
            <p>If you received this email, your AWS SES configuration is working correctly!</p>
            <hr>
            <p><small>Sent from {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}</small></p>
        </body>
        </html>
        """

        text_body = f"""
Test Email - {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}

This is a test email to verify email configuration.

If you received this email, your AWS SES configuration is working correctly!

Sent from {current_app.config.get('APP_NAME', 'Meal Expense Tracker')}
        """.strip()

        success = _send_email(
            to_addresses=[recipient_email],
            subject="Test Email - Meal Expense Tracker",
            html_body=html_body,
            text_body=text_body,
        )

        if success:
            logger.info(f"Test email sent to {recipient_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send test email to {recipient_email}: {e}")
        return False
