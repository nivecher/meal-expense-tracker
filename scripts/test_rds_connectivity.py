#!/usr/bin/env python3
"""
RDS Connectivity Test Script
Tests various aspects of RDS connectivity including network, security groups, and authentication.
"""

import argparse
import json
import socket
import sys
from typing import Any, Dict, Optional

import boto3


def test_network_connectivity(host: str, port: int) -> bool:
    """Test basic network connectivity to RDS endpoint."""
    print(f"Testing network connectivity to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print("✅ Network connectivity: SUCCESS")
            return True
        else:
            print(f"❌ Network connectivity: FAILED (Error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Network connectivity: FAILED ({e})")
        return False


def get_rds_instance_info(instance_id: str, region: str) -> Optional[Dict[str, Any]]:
    """Get RDS instance information."""
    try:
        rds = boto3.client("rds", region_name=region)
        response = rds.describe_db_instances(DBInstanceIdentifier=instance_id)

        if response["DBInstances"]:
            return response["DBInstances"][0]
        return None
    except Exception as e:
        print(f"❌ Failed to get RDS instance info: {e}")
        return None


def check_security_groups(instance_info: Dict[str, Any], region: str) -> None:
    """Check security group rules for RDS instance."""
    print("\n🔍 Checking security groups...")

    try:
        ec2 = boto3.client("ec2", region_name=region)

        for sg in instance_info.get("VpcSecurityGroups", []):
            sg_id = sg["VpcSecurityGroupId"]
            print(f"\nSecurity Group: {sg_id}")

            response = ec2.describe_security_groups(GroupIds=[sg_id])

            for group in response["SecurityGroups"]:
                print(f"  Description: {group['Description']}")

                for rule in group.get("IpPermissions", []):
                    port_range = f"{rule.get('FromPort', 'N/A')}-{rule.get('ToPort', 'N/A')}"
                    protocol = rule.get("IpProtocol", "N/A")

                    print(f"  Inbound Rule: Protocol={protocol}, Ports={port_range}")

                    # Check CIDR blocks
                    for ip_range in rule.get("IpRanges", []):
                        cidr = ip_range.get("CidrIp", "N/A")
                        desc = ip_range.get("Description", "No description")
                        print(f"    CIDR: {cidr} ({desc})")

                    # Check security group references
                    for sg_ref in rule.get("UserIdGroupPairs", []):
                        ref_sg_id = sg_ref.get("GroupId", "N/A")
                        print(f"    Security Group: {ref_sg_id}")

    except Exception as e:
        print(f"❌ Failed to check security groups: {e}")


def check_subnet_configuration(instance_info: Dict[str, Any], region: str) -> None:
    """Check subnet configuration for RDS instance."""
    print("\n🔍 Checking subnet configuration...")

    try:
        ec2 = boto3.client("ec2", region_name=region)

        subnet_group = instance_info.get("DBSubnetGroup", {})
        print(f"DB Subnet Group: {subnet_group.get('DBSubnetGroupName', 'N/A')}")
        print(f"VPC ID: {subnet_group.get('VpcId', 'N/A')}")

        for subnet in subnet_group.get("Subnets", []):
            subnet_id = subnet.get("SubnetIdentifier")
            az = subnet.get("SubnetAvailabilityZone", {}).get("Name", "N/A")

            # Get subnet details
            response = ec2.describe_subnets(SubnetIds=[subnet_id])
            subnet_details = response["Subnets"][0]

            is_public = subnet_details.get("MapPublicIpOnLaunch", False)
            cidr = subnet_details.get("CidrBlock", "N/A")

            print(f"  Subnet: {subnet_id} (AZ: {az})")
            print(f"    CIDR: {cidr}")
            print(f"    Public: {'Yes' if is_public else 'No'}")

            # Check route table
            route_tables = ec2.describe_route_tables(Filters=[{"Name": "association.subnet-id", "Values": [subnet_id]}])

            for rt in route_tables["RouteTables"]:
                print(f"    Route Table: {rt['RouteTableId']}")
                for route in rt.get("Routes", []):
                    dest = route.get("DestinationCidrBlock", route.get("DestinationPrefixListId", "N/A"))
                    target = route.get("GatewayId", route.get("NatGatewayId", route.get("InstanceId", "local")))
                    print(f"      Route: {dest} -> {target}")

    except Exception as e:
        print(f"❌ Failed to check subnet configuration: {e}")


def main():
    parser = argparse.ArgumentParser(description="Test RDS connectivity")
    parser.add_argument("--instance-id", required=True, help="RDS instance identifier")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--port", type=int, default=5432, help="Database port")

    args = parser.parse_args()

    print(f"🔍 Testing RDS connectivity for instance: {args.instance_id}")
    print(f"Region: {args.region}")
    print("=" * 60)

    # Get RDS instance information
    instance_info = get_rds_instance_info(args.instance_id, args.region)
    if not instance_info:
        print("❌ Failed to get RDS instance information")
        sys.exit(1)

    # Display basic instance info
    print("\n📋 Instance Information:")
    print(f"  Endpoint: {instance_info.get('Endpoint', {}).get('Address', 'N/A')}")
    print(f"  Port: {instance_info.get('Endpoint', {}).get('Port', 'N/A')}")
    print(f"  Engine: {instance_info.get('Engine', 'N/A')}")
    print(f"  Status: {instance_info.get('DBInstanceStatus', 'N/A')}")
    print(f"  Publicly Accessible: {instance_info.get('PubliclyAccessible', False)}")
    print(f"  Multi-AZ: {instance_info.get('MultiAZ', False)}")

    host = instance_info.get("Endpoint", {}).get("Address")
    port = instance_info.get("Endpoint", {}).get("Port", args.port)

    if not host:
        print("❌ No endpoint address found")
        sys.exit(1)

    # Test network connectivity
    network_ok = test_network_connectivity(host, port)

    # Check security groups
    check_security_groups(instance_info, args.region)

    # Check subnet configuration
    check_subnet_configuration(instance_info, args.region)

    print("\n" + "=" * 60)
    if network_ok:
        print("✅ RDS instance is reachable from this location")
    else:
        print("❌ RDS instance is NOT reachable from this location")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Check if RDS is in public subnets (not private)")
        print("2. Verify security group allows your IP address")
        print("3. Ensure route tables have internet gateway routes")
        print("4. Check if RDS is marked as publicly accessible")


if __name__ == "__main__":
    main()
