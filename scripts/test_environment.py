#!/usr/bin/env python3
"""
Test script to verify all services are working.
This ensures our Python app can connect to Docker services.
"""

import asyncio
import sys

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


async def test_postgresql():
    """Test PostgreSQL connection."""
    print(f"{YELLOW}Testing PostgreSQL...{RESET}")
    try:
        import asyncpg

        # Connect to database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="dronesphere",
            password="dronesphere_pass_dev",
            database="dronesphere",
        )

        # Run test query
        version = await conn.fetchval("SELECT version()")
        print(f"{GREEN}✅ PostgreSQL connected!{RESET}")
        print(f"   Version: {version[:50]}...")

        # Check PostGIS
        postgis = await conn.fetchval("SELECT PostGIS_version()")
        print(f"   PostGIS: {postgis}")

        await conn.close()
        return True
    except ImportError:
        print(f"{RED}❌ PostgreSQL failed: asyncpg not installed{RESET}")
        print(f"   Run: poetry install")
        return False
    except Exception as e:
        print(f"{RED}❌ PostgreSQL failed: {e}{RESET}")
        return False


async def test_redis():
    """Test Redis connection."""
    print(f"\n{YELLOW}Testing Redis...{RESET}")
    try:
        import redis.asyncio as redis

        # Connect to Redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Test ping
        await r.ping()
        print(f"{GREEN}✅ Redis connected!{RESET}")

        # Test set/get
        await r.set("test:connection", "successful")
        value = await r.get("test:connection")
        print(f"   Test value: {value}")

        # Get Redis info
        info = await r.info("server")
        print(f"   Version: {info['redis_version']}")

        # Use aclose() to avoid deprecation warning
        await r.aclose()
        return True
    except ImportError:
        print(f"{RED}❌ Redis failed: redis not installed{RESET}")
        print(f"   Run: poetry install")
        return False
    except Exception as e:
        print(f"{RED}❌ Redis failed: {e}{RESET}")
        return False


async def test_rabbitmq():
    """Test RabbitMQ connection."""
    print(f"\n{YELLOW}Testing RabbitMQ...{RESET}")
    try:
        import aio_pika

        # Connect to RabbitMQ
        connection = await aio_pika.connect_robust(
            host="localhost",
            port=5672,
            login="dronesphere",
            password="dronesphere_pass_dev",
            virtualhost="dronesphere",
        )

        print(f"{GREEN}✅ RabbitMQ connected!{RESET}")

        # Create a test channel
        await connection.channel()
        print("   Channel created successfully")

        await connection.close()
        return True
    except ImportError:
        print(f"{RED}❌ RabbitMQ failed: aio-pika not installed{RESET}")
        print(f"   Run: poetry install")
        return False
    except Exception as e:
        print(f"{RED}❌ RabbitMQ failed: {e}{RESET}")
        return False


async def main():
    """Run all tests."""
    print(f"\n{YELLOW}🔍 DroneSphere Environment Test{RESET}")
    print("=" * 50)

    results = []

    # Run tests
    results.append(await test_postgresql())
    results.append(await test_redis())
    results.append(await test_rabbitmq())

    # Summary
    print("\n" + "=" * 50)
    if all(results):
        print(f"{GREEN}🎉 All services are working correctly!{RESET}")
        print("\nYou can access:")
        print("  • Database UI: http://localhost:8080")
        print("    - System: PostgreSQL")
        print("    - Server: postgres")
        print("    - Username: dronesphere")
        print("    - Password: dronesphere_pass_dev")
        print("  • RabbitMQ UI: http://localhost:15672")
        print("    - Username: dronesphere")
        print("    - Password: dronesphere_pass_dev")
        return 0
    else:
        print(f"{RED}❌ Some services failed.{RESET}")
        if any("not installed" in str(r) for r in results):
            print(f"\n{YELLOW}First, ensure all dependencies are installed:{RESET}")
            print("  poetry install")
        print(f"\n{YELLOW}If Docker services are not running:{RESET}")
        print("  make docker-logs")
        return 1


if __name__ == "__main__":
    # Make sure we're in virtual environment
    if sys.prefix == sys.base_prefix:
        print(f"{RED}⚠️  Not in virtual environment! Run:{RESET}")
        print("  source venv/bin/activate")
        sys.exit(1)

    # Run tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)