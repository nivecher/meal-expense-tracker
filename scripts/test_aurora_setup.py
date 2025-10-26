#!/usr/bin/env python3
"""
Test Aurora Serverless Setup

This script validates that Aurora Serverless is properly configured and accessible.
It performs connectivity tests, schema validation, and basic functionality checks.

Usage:
    python scripts/test_aurora_setup.py
"""

import logging
import os
import sys
from typing import Dict

import boto3
import psycopg2
from psycopg2 import sql

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AuroraTester:
    """Tests Aurora Serverless setup and connectivity"""

    def __init__(self):
        self.rds_client = boto3.client("rds")
        self.secrets_client = boto3.client("secretsmanager")

    def get_aurora_config_from_env(self) -> Dict:
        """Get Aurora configuration from environment variables"""
        return {
            "host": os.getenv("AURORA_HOST"),
            "port": int(os.getenv("AURORA_PORT", 5432)),
            "database": os.getenv("AURORA_NAME"),
            "user": os.getenv("AURORA_USER"),
            "password": os.getenv("AURORA_PASSWORD"),
        }

    def test_aurora_cluster_status(self) -> bool:
        """Test that Aurora cluster is available and healthy"""
        try:
            logger.info("🔍 Testing Aurora cluster status...")

            # Get Aurora cluster status
            response = self.rds_client.describe_db_clusters(DBClusterIdentifier=os.getenv("AURORA_CLUSTER_ID"))

            cluster = response["DBClusters"][0]
            status = cluster["Status"]

            if status == "available":
                logger.info(f"✅ Aurora cluster is available: {cluster['DBClusterIdentifier']}")
                logger.info(f"   Engine: {cluster['Engine']} {cluster['EngineVersion']}")
                logger.info(f"   Endpoint: {cluster['Endpoint']}")
                logger.info(f"   Serverless v2: {cluster.get('ServerlessV2Config', 'Not configured')}")
                return True
            else:
                logger.error(f"❌ Aurora cluster status: {status}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to check Aurora cluster status: {e}")
            return False

    def test_database_connectivity(self) -> bool:
        """Test database connectivity to Aurora"""
        config = self.get_aurora_config_from_env()

        # Validate configuration
        missing = [k for k, v in config.items() if v is None]
        if missing:
            logger.error(f"❌ Missing Aurora configuration: {', '.join(missing)}")
            logger.error("Set environment variables: AURORA_HOST, AURORA_PORT, etc.")
            return False

        try:
            logger.info("🔌 Testing Aurora database connectivity...")

            conn = psycopg2.connect(**config)
            cursor = conn.cursor()

            # Test basic query
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            logger.info(f"✅ Connected to Aurora PostgreSQL: {version[:50]}...")

            # Test Aurora-specific features
            cursor.execute("SHOW serverless")
            serverless_status = cursor.fetchone()
            logger.info(f"   Serverless status: {serverless_status}")

            cursor.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"❌ Database connectivity test failed: {e}")
            return False

    def test_schema_creation(self) -> bool:
        """Test that we can create the application schema"""
        config = self.get_aurora_config_from_env()

        try:
            logger.info("🏗️ Testing schema creation...")

            conn = psycopg2.connect(**config)
            conn.autocommit = True
            cursor = conn.cursor()

            # Create test tables (matching our application schema)
            test_tables = [
                """
                CREATE TABLE IF NOT EXISTS test_user (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(64) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS test_restaurant (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    user_id INTEGER REFERENCES test_user(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS test_expense (
                    id SERIAL PRIMARY KEY,
                    amount DECIMAL(10,2) NOT NULL,
                    user_id INTEGER REFERENCES test_user(id),
                    restaurant_id INTEGER REFERENCES test_restaurant(id),
                    date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
            ]

            for table_sql in test_tables:
                cursor.execute(table_sql)

            logger.info("✅ Test schema created successfully")

            # Test data insertion
            cursor.execute(
                """
                INSERT INTO test_user (username, email)
                VALUES (%s, %s) RETURNING id
            """,
                ("test_user", "test@example.com"),
            )

            user_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO test_restaurant (name, user_id)
                VALUES (%s, %s) RETURNING id
            """,
                ("Test Restaurant", user_id),
            )

            restaurant_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO test_expense (amount, user_id, restaurant_id, date)
                VALUES (%s, %s, %s, %s)
            """,
                (25.50, user_id, restaurant_id, "2024-01-15 12:00:00"),
            )

            logger.info("✅ Test data inserted successfully")

            # Test queries
            cursor.execute("SELECT COUNT(*) FROM test_expense")
            expense_count = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT e.amount, r.name, u.username
                FROM test_expense e
                JOIN test_restaurant r ON e.restaurant_id = r.id
                JOIN test_user u ON e.user_id = u.id
            """
            )
            results = cursor.fetchall()

            logger.info(f"✅ Query test passed: {expense_count} expenses found")
            logger.info(f"   Sample result: {results[0] if results else 'No results'}")

            # Clean up test data
            cursor.execute("DROP TABLE IF EXISTS test_expense CASCADE")
            cursor.execute("DROP TABLE IF EXISTS test_restaurant CASCADE")
            cursor.execute("DROP TABLE IF EXISTS test_user CASCADE")

            logger.info("✅ Test cleanup completed")

            cursor.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"❌ Schema creation test failed: {e}")
            return False

    def test_rds_proxy_connectivity(self) -> bool:
        """Test RDS Proxy connectivity"""
        proxy_config = {
            "host": os.getenv("AURORA_PROXY_HOST"),
            "port": int(os.getenv("AURORA_PROXY_PORT", 5432)),
            "database": os.getenv("AURORA_NAME"),
            "user": os.getenv("AURORA_USER"),
            "password": os.getenv("AURORA_PASSWORD"),
        }

        if not proxy_config["host"]:
            logger.info("⏭️ RDS Proxy host not configured, skipping proxy test")
            return True

        try:
            logger.info("🔌 Testing RDS Proxy connectivity...")

            conn = psycopg2.connect(**proxy_config)
            cursor = conn.cursor()

            # Test basic query through proxy
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            logger.info(f"✅ Connected through RDS Proxy: {version[:50]}...")

            cursor.close()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"❌ RDS Proxy connectivity test failed: {e}")
            return False

    def test_performance_baseline(self) -> bool:
        """Establish performance baseline for Aurora"""
        config = self.get_aurora_config_from_env()

        try:
            logger.info("⚡ Testing Aurora performance baseline...")

            conn = psycopg2.connect(**config)
            cursor = conn.cursor()

            # Test query performance
            import time

            start_time = time.time()
            cursor.execute(
                """
                SELECT COUNT(*) FROM pg_stat_user_tables
                UNION ALL
                SELECT COUNT(*) FROM pg_stat_user_indexes
                UNION ALL
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_schema = 'public'
            """
            )
            results = cursor.fetchall()
            query_time = time.time() - start_time

            logger.info(f"✅ Performance test completed in {query_time:.3f} seconds")
            logger.info(f"   Query results: {results}")

            cursor.close()
            conn.close()

            # Performance should be under 1 second for basic queries
            if query_time < 1.0:
                logger.info("✅ Performance meets expectations")
                return True
            else:
                logger.warning(f"⚠️ Performance slower than expected: {query_time:.3f}s")
                return True  # Still pass, just warn

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all Aurora setup tests"""
        logger.info("🚀 Starting Aurora Serverless setup validation")
        logger.info("=" * 60)

        tests = [
            ("Aurora Cluster Status", self.test_aurora_cluster_status),
            ("Database Connectivity", self.test_database_connectivity),
            ("Schema Creation", self.test_schema_creation),
            ("RDS Proxy Connectivity", self.test_rds_proxy_connectivity),
            ("Performance Baseline", self.test_performance_baseline),
        ]

        passed = 0
        total = len(tests)

        for test_name, test_func in tests:
            logger.info(f"\n{'=' * 20} {test_name} {'=' * 20}")
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")

        logger.info("\n" + "=" * 60)
        logger.info(f"📊 Test Results: {passed}/{total} tests passed")

        if passed == total:
            logger.info("🎉 All Aurora setup tests passed! Ready for migration.")
            return True
        else:
            logger.error(f"❌ {total - passed} tests failed. Please fix issues before proceeding.")
            return False


def main():
    """Main test execution"""
    # Validate environment variables
    required_env_vars = ["AURORA_CLUSTER_ID", "AURORA_HOST", "AURORA_USER", "AURORA_PASSWORD", "AURORA_NAME"]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before running the test.")
        sys.exit(1)

    # Run tests
    tester = AuroraTester()
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
