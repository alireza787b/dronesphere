"""Pytest configuration and shared fixtures."""

import asyncio

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_drone_config():
    """Mock drone configuration for testing."""
    return {
        "drones": [
            {
                "id": 1,
                "name": "Test Drone",
                "agent": "127.0.0.1:8001",
                "capabilities": ["takeoff", "land", "goto"],
            }
        ]
    }


# Future fixtures can be added here:
# @pytest.fixture
# def mock_sitl():
#     """Mock SITL connection for testing."""
#     pass

# @pytest.fixture
# def test_client():
#     """FastAPI test client."""
#     pass
