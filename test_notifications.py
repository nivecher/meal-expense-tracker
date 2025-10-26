#!/usr/bin/env python3
"""
Test script to verify SNS notifications are working correctly.
"""

import os
import sys

import boto3


def test_sns_topic_exists():
    """Test if the SNS topic exists."""
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        account_id = os.getenv("AWS_ACCOUNT_ID", "562427544284")
        app_name = "meal-expense-tracker"
        environment = "dev"

        sns_client = boto3.client("sns", region_name=region)

        topic_name = f"{app_name}-{environment}-notifications"
        topic_arn = f"arn:aws:sns:{region}:{account_id}:{topic_name}"

        # List topics and check if ours exists
        response = sns_client.list_topics()
        topics = response.get("Topics", [])

        for topic in topics:
            if topic["TopicArn"] == topic_arn:
                print(f"✅ SNS topic exists: {topic_arn}")
                return True, topic_arn

        print(f"❌ SNS topic not found: {topic_arn}")
        return False, None

    except Exception as e:
        print(f"❌ Error checking SNS topic: {e}")
        return False, None


def test_send_notification(topic_arn):
    """Test sending a notification via SNS."""
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        sns_client = boto3.client("sns", region_name=region)

        subject = "Test Notification - Meal Expense Tracker"
        message = "This is a test notification to verify SNS configuration is working correctly."

        response = sns_client.publish(TopicArn=topic_arn, Subject=subject, Message=message)

        print(f"✅ Test notification sent successfully: {response['MessageId']}")
        print(f"   Subject: {subject}")
        print(f"   Message: {message}")
        return True

    except Exception as e:
        print(f"❌ Error sending test notification: {e}")
        return False


def test_subscribe_email(topic_arn, email):
    """Test subscribing an email address to the SNS topic."""
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        sns_client = boto3.client("sns", region_name=region)

        response = sns_client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)

        subscription_arn = response.get("SubscriptionArn")
        print(f"✅ Email subscription created: {subscription_arn}")
        print(f"   Email: {email}")
        print("   Protocol: email")
        print("   Note: You will receive a confirmation email to verify the subscription.")
        return True

    except Exception as e:
        print(f"❌ Error subscribing email: {e}")
        return False


def main():
    """Main test function."""
    print("Testing SNS Notifications Configuration")
    print("=" * 50)

    # Test 1: Check if SNS topic exists
    topic_exists, topic_arn = test_sns_topic_exists()
    if not topic_exists:
        print("\n❌ Cannot proceed with tests - SNS topic doesn't exist")
        sys.exit(1)

    # Test 2: Send test notification
    print("\nSending test notification...")
    notification_sent = test_send_notification(topic_arn)

    # Test 3: Offer to subscribe an email (optional)
    print("\nWould you like to subscribe an email address for notifications?")
    email = input("Enter email address (or press Enter to skip): ").strip()

    if email:
        print(f"Subscribing {email} to notifications...")
        subscription_created = test_subscribe_email(topic_arn, email)
        if subscription_created:
            print("✅ Email subscription setup complete!")
            print("   Check your email for a confirmation message from AWS SNS.")
    else:
        print("Skipping email subscription setup.")

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"✅ SNS Topic: {'EXISTS' if topic_exists else 'MISSING'}")
    print(f"✅ Test Notification: {'SENT' if notification_sent else 'FAILED'}")

    if notification_sent:
        print("\n🎉 SNS notifications are working correctly!")
        print("   The notification service should now work for password resets and other notifications.")
    else:
        print("\n❌ SNS notifications are NOT working properly.")
        print("   Check AWS credentials, permissions, and SNS topic configuration.")


if __name__ == "__main__":
    main()
