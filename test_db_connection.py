#!/usr/bin/env python3
"""
Test script to check database connectivity without SQLAlchemy.
This will help identify if the issue is with the database connection or SQLAlchemy.
"""

import json
import os
import sys

import boto3
from botocore.exceptions import ClientError


def test_pg8000_connection():
    """Test direct connection using pg8000."""
    try:
        import pg8000

        print("✅ pg8000 imported successfully")

        # Get database credentials from environment or secrets
        db_url = os.getenv("DATABASE_URL", "")
        print(f"Database URL: {db_url}")

        if "placeholder" in db_url:
            print("🔍 Using placeholder credentials, getting real ones from Secrets Manager...")
            # Get Aurora credentials from Secrets Manager
            secrets_client = boto3.client("secretsmanager")
            secret_value = secrets_client.get_secret_value(SecretId="meal-expense-tracker/dev/aurora-credentials")
            secret_data = json.loads(secret_value["SecretString"])

            db_host = secret_data["db_host"]
            db_port = secret_data["db_port"]
            db_name = secret_data["db_name"]
            db_username = secret_data["db_username"]
            db_password = secret_data["db_password"]

            print(f"Connecting to: {db_host}:{db_port}/{db_name}")

            # Test connection
            conn = pg8000.connect(
                host=db_host, port=int(db_port), database=db_name, user=db_username, password=db_password
            )

            print("✅ Database connection successful!")

            # Test a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            print(f"✅ Database version: {version[0]}")

            cursor.close()
            conn.close()
            print("✅ Connection closed successfully")

        else:
            print("❌ No placeholder credentials found")

    except ImportError as e:
        print(f"❌ Failed to import pg8000: {e}")
        return False
    except ClientError as e:
        print(f"❌ Failed to get secrets: {e}")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    return True


def test_sqlalchemy_connection():
    """Test connection using SQLAlchemy with pg8000."""
    try:
        from sqlalchemy import create_engine, text

        print("✅ SQLAlchemy imported successfully")

        # Get database credentials
        db_url = os.getenv("DATABASE_URL", "")
        print(f"Database URL: {db_url}")

        if "placeholder" in db_url:
            print("🔍 Using placeholder credentials, getting real ones from Secrets Manager...")
            # Get Aurora credentials from Secrets Manager
            secrets_client = boto3.client("secretsmanager")
            secret_value = secrets_client.get_secret_value(SecretId="meal-expense-tracker/dev/aurora-credentials")
            secret_data = json.loads(secret_value["SecretString"])

            db_host = secret_data["db_host"]
            db_port = secret_data["db_port"]
            db_name = secret_data["db_name"]
            db_username = secret_data["db_username"]
            db_password = secret_data["db_password"]

            # Create SQLAlchemy URL with pg8000
            db_url = f"postgresql+pg8000://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
            print(f"SQLAlchemy URL: {db_url}")

            # Test connection
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()
                print(f"✅ SQLAlchemy connection successful! Version: {version[0]}")

        else:
            print("❌ No placeholder credentials found")

    except ImportError as e:
        print(f"❌ Failed to import SQLAlchemy: {e}")
        return False
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🧪 Testing database connectivity...")
    print("=" * 50)

    print("\n1. Testing pg8000 direct connection:")
    pg8000_success = test_pg8000_connection()

    print("\n2. Testing SQLAlchemy with pg8000:")
    sqlalchemy_success = test_sqlalchemy_connection()

    print("\n" + "=" * 50)
    print("📊 Results:")
    print(f"pg8000 direct connection: {'✅ SUCCESS' if pg8000_success else '❌ FAILED'}")
    print(f"SQLAlchemy with pg8000: {'✅ SUCCESS' if sqlalchemy_success else '❌ FAILED'}")

    if pg8000_success and sqlalchemy_success:
        print("\n🎉 All tests passed! Database connectivity is working.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. Check the errors above.")
        sys.exit(1)
