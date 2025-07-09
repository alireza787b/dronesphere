# tests/performance/test_load.py
# ===================================

"""Load testing."""

import asyncio
import time

import pytest

from dronesphere.server.client import DroneSphereClient


@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """Performance tests."""

    @pytest.mark.asyncio
    async def test_telemetry_throughput(self):
        """Test telemetry request throughput."""
        client = DroneSphereClient("http://localhost:8000")

        try:
            # Warm up
            await client.get_telemetry(1)

            # Measure throughput
            start_time = time.time()
            request_count = 100

            tasks = []
            for _ in range(request_count):
                tasks.append(client.get_telemetry(1))

            await asyncio.gather(*tasks)

            duration = time.time() - start_time
            rps = request_count / duration

            print(f"Telemetry throughput: {rps:.1f} requests/second")

            # Should achieve at least 50 RPS for telemetry
            assert rps >= 50.0

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_commands(self):
        """Test concurrent command handling."""
        clients = [DroneSphereClient("http://localhost:8000") for _ in range(5)]

        try:
            # Execute concurrent wait commands
            start_time = time.time()

            tasks = []
            for i, client in enumerate(clients):
                # Stagger commands slightly to avoid conflicts
                await asyncio.sleep(0.1)
                tasks.append(client.wait(1, 1.0))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            duration = time.time() - start_time

            # Check responses
            successful = sum(1 for r in responses if not isinstance(r, Exception))
            print(
                f"Concurrent commands: {successful}/{len(clients)} successful in {duration:.2f}s"
            )

            # At least one should succeed (others might be overridden)
            assert successful >= 1

        finally:
            for client in clients:
                await client.close()
