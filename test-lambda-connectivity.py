#!/usr/bin/env python3
"""
Test Lambda connectivity to RDS Proxy
This tests network connectivity from Lambda to RDS Proxy
"""
import json
import socket

import boto3
import dns.resolver

# RDS Proxy endpoint
PROXY_ENDPOINT = "meal-expense-tracker-dev-aurora-proxy.proxy-ct7mmnmqbvyr.us-east-1.rds.amazonaws.com"


def test_dns_resolution(hostname):
    """Test DNS resolution"""
    print(f"Testing DNS resolution for {hostname}...")
    try:
        result = socket.gethostbyname(hostname)
        print(f"✅ DNS resolved to: {result}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False


def test_port_connectivity(hostname, port=5432):
    """Test port connectivity"""
    print(f"Testing port connectivity to {hostname}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        if result == 0:
            print(f"✅ Port {port} is open")
            return True
        else:
            print(f"❌ Port {port} is closed or unreachable (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def test_aws_services():
    """Test AWS service connectivity"""
    print("\nTesting AWS service connectivity...")

    # Test Secrets Manager
    try:
        secrets_client = boto3.client("secretsmanager")
        secret = secrets_client.get_secret_value(SecretId="meal-expense-tracker/dev/aurora-credentials")
        data = json.loads(secret["SecretString"])
        print("✅ AWS Secrets Manager accessible")
        print(f"   Endpoint: {data.get('db_host')}")
        return True
    except Exception as e:
        print(f"❌ Secrets Manager error: {e}")
        return False


def main():
    print("=" * 60)
    print("Lambda Connectivity Test")
    print("=" * 60)

    # Test 1: DNS resolution
    dns_ok = test_dns_resolution(PROXY_ENDPOINT)

    # Test 2: Port connectivity
    port_ok = test_port_connectivity(PROXY_ENDPOINT)

    # Test 3: AWS services
    aws_ok = test_aws_services()

    print("\n" + "=" * 60)
    print("Results:")
    print(f"  DNS Resolution: {'✅ PASS' if dns_ok else '❌ FAIL'}")
    print(f"  Port Connectivity: {'✅ PASS' if port_ok else '❌ FAIL'}")
    print(f"  AWS Services: {'✅ PASS' if aws_ok else '❌ FAIL'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
