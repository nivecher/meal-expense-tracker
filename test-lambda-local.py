#!/usr/bin/env python3
"""
Test script for Lambda container locally using the AWS Lambda Runtime Interface Emulator.
This script simulates API Gateway events and tests the Lambda function.
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict

import requests


def create_test_event(http_method: str = "GET", path: str = "/", headers: Dict[str, str] = None) -> Dict[str, Any]:
    """Create a test API Gateway v2.0 event."""
    if headers is None:
        headers = {"Host": "localhost:9000"}

    return {
        "version": "2.0",
        "routeKey": f"{http_method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api",
            "domainName": "localhost:9000",
            "http": {
                "method": http_method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-agent",
            },
            "requestId": "test-request-id",
            "routeKey": f"{http_method} {path}",
            "stage": "test",
            "time": "01/Jan/2025:00:00:00 +0000",
            "timeEpoch": int(time.time()),
        },
        "body": None,
        "isBase64Encoded": False,
    }


def test_lambda_container():
    """Test the Lambda container locally."""
    print("🚀 Starting Lambda container test...")

    # Start the container
    print("📦 Starting Docker container...")
    container_process = subprocess.Popen(
        ["docker", "run", "--rm", "-p", "9000:8080", "meal-expense-tracker-dev-lambda:latest"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for container to start
    print("⏳ Waiting for container to start...")
    time.sleep(10)

    # Test health endpoint
    print("🏥 Testing health endpoint...")
    health_event = create_test_event("GET", "/health")

    try:
        response = requests.post(
            "http://localhost:9000/2015-03-31/functions/function/invocations", json=health_event, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health check response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

    # Test root endpoint
    print("\n🏠 Testing root endpoint...")
    root_event = create_test_event("GET", "/")

    try:
        response = requests.post(
            "http://localhost:9000/2015-03-31/functions/function/invocations", json=root_event, timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Root endpoint response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Root endpoint failed with status {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

    # Clean up
    print("\n🧹 Stopping container...")
    container_process.terminate()
    container_process.wait()

    print("✅ Test completed!")


if __name__ == "__main__":
    test_lambda_container()
