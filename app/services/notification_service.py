"""Notification service for sending alerts and messages via AWS SNS."""

import logging
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


def is_notifications_enabled() -> bool:
    """Check if notification functionality is enabled.

    Returns:
        True if notifications are enabled and configured, False otherwise
    """
    return current_app.config.get("NOTIFICATIONS_ENABLED", False)


def _send_via_sns(topic_arn: str, subject: str, message: str) -> bool:
    """Send notification via AWS SNS.

    Args:
        topic_arn: SNS topic ARN to publish to
        subject: Notification subject
        message: Notification message

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Configure SNS client
        sns_client = boto3.client("sns", region_name=current_app.config.get("AWS_REGION", "us-east-1"))

        # Send message via SNS
        response = sns_client.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )

        logger.info(f"Notification sent via SNS: {response['MessageId']}")
        return True

    except ClientError as e:
        logger.error(f"AWS SNS error: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to send notification via SNS: {e}")
        return False


def send_notification(subject: str, message: str, topic_arn: Optional[str] = None) -> bool:
    """Send a notification via SNS.

    Args:
        subject: Notification subject
        message: Notification message
        topic_arn: SNS topic ARN (optional, uses env var if not provided)

    Returns:
        True if sent successfully, False otherwise
    """
    if not is_notifications_enabled():
        logger.warning("Notifications are disabled, logging message instead")
        logger.info(f"Notification would be sent: {subject} - {message}")
        return False

    # Get topic ARN from environment or parameter
    if not topic_arn:
        topic_arn = current_app.config.get("SNS_TOPIC_ARN")

    if not topic_arn:
        logger.error("No SNS topic ARN configured for notifications")
        return False

    # Send via SNS
    return _send_via_sns(topic_arn, subject, message)


def send_password_reset_notification(user_email: str, username: str, new_password: str) -> bool:
    """Send password reset notification to user.

    Args:
        user_email: User's email address
        username: User's username
        new_password: The new password to send

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        subject = "Password Reset - Meal Expense Tracker"

        message = f"""
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
The Meal Expense Tracker Team
        """.strip()

        # Send notification (SNS will handle email delivery)
        success = send_notification(subject, message)

        if success:
            logger.info(f"Password reset notification sent for {user_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send password reset notification for {user_email}: {e}")
        return False


def send_welcome_notification(user_email: str, username: str, new_password: str) -> bool:
    """Send welcome notification to new user.

    Args:
        user_email: User's email address
        username: User's username
        new_password: The new password to send

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        subject = "Welcome to Meal Expense Tracker"

        message = f"""
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
The Meal Expense Tracker Team
        """.strip()

        # Send notification (SNS will handle email delivery)
        success = send_notification(subject, message)

        if success:
            logger.info(f"Welcome notification sent for {user_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send welcome notification for {user_email}: {e}")
        return False


def subscribe_email_to_notifications(email_address: str) -> bool:
    """Subscribe an email address to the SNS topic for notifications.

    Args:
        email_address: Email address to subscribe

    Returns:
        True if subscription was created successfully, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Get SNS topic ARN from config
        topic_arn = current_app.config.get("SNS_TOPIC_ARN")
        if not topic_arn:
            logger.error("No SNS topic ARN configured for email subscription")
            return False

        # Configure SNS client
        region = current_app.config.get("AWS_REGION", "us-east-1")
        sns_client = boto3.client("sns", region_name=region)

        # Subscribe email to SNS topic
        response = sns_client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email_address)

        subscription_arn = response.get("SubscriptionArn")
        logger.info(f"Email subscription created: {subscription_arn} for {email_address}")

        return True

    except ClientError as e:
        logger.error(f"AWS SNS subscription error for {email_address}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to subscribe email {email_address} to notifications: {e}")
        return False


def unsubscribe_email_from_notifications(email_address: str) -> bool:
    """Unsubscribe an email address from the SNS topic for notifications.

    Args:
        email_address: Email address to unsubscribe

    Returns:
        True if unsubscription was successful, False otherwise
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        # Get SNS topic ARN from config
        topic_arn = current_app.config.get("SNS_TOPIC_ARN")
        if not topic_arn:
            logger.error("No SNS topic ARN configured for email unsubscription")
            return False

        # Configure SNS client
        region = current_app.config.get("AWS_REGION", "us-east-1")
        sns_client = boto3.client("sns", region_name=region)

        # First get all subscriptions for this topic
        response = sns_client.list_subscriptions_by_topic(TopicArn=topic_arn)

        # Find the subscription for this email
        subscription_arn = None
        for subscription in response.get("Subscriptions", []):
            if (
                subscription.get("Protocol") == "email"
                and subscription.get("Endpoint") == email_address
                and subscription.get("SubscriptionArn") != "PendingConfirmation"
            ):
                subscription_arn = subscription.get("SubscriptionArn")
                break

        if not subscription_arn:
            logger.warning(f"No active subscription found for email {email_address}")
            return False

        # Unsubscribe
        sns_client.unsubscribe(SubscriptionArn=subscription_arn)

        logger.info(f"Email subscription removed: {subscription_arn} for {email_address}")
        return True

    except ClientError as e:
        logger.error(f"AWS SNS unsubscription error for {email_address}: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to unsubscribe email {email_address} from notifications: {e}")
        return False


def send_test_notification(recipient_email: str) -> bool:
    """Send a test notification to verify configuration.

    Args:
        recipient_email: Email address to send test notification to

    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        subject = "Test Notification - Meal Expense Tracker"

        message = """
Test Notification - Meal Expense Tracker

This is a test notification to verify SNS configuration.

If you received this notification, your AWS SNS configuration is working correctly!

Sent from Meal Expense Tracker
        """.strip()

        success = send_notification(subject, message)

        if success:
            logger.info(f"Test notification sent to {recipient_email}")
        return success

    except Exception as e:
        logger.error(f"Failed to send test notification to {recipient_email}: {e}")
        return False
