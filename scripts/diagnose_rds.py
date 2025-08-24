#!/usr/bin/env python3
import socket
import sys

import boto3


def check_rds_connectivity():
    # Get RDS instance info
    rds = boto3.client("rds")
    try:
        response = rds.describe_db_instances(DBInstanceIdentifier="meal-expense-tracker-dev")
        instance = response["DBInstances"][0]

        print(f"RDS Status: {instance['DBInstanceStatus']}")
        print(f"Publicly Accessible: {instance['PubliclyAccessible']}")
        print(f"Endpoint: {instance['Endpoint']['Address']}")
        print(f"Port: {instance['Endpoint']['Port']}")

        # Test network connectivity
        host = instance["Endpoint"]["Address"]
        port = instance["Endpoint"]["Port"]

        print(f"\nTesting connection to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print("✅ Network connectivity: SUCCESS")
        else:
            print(f"❌ Network connectivity: FAILED (Error: {result})")

        # Check security groups
        print("\nSecurity Groups:")
        for sg in instance["VpcSecurityGroups"]:
            print(f"  {sg['VpcSecurityGroupId']}: {sg['Status']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_rds_connectivity()
