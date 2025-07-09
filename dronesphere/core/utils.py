# dronesphere/core/utils.py
# ================================

"""Core utilities."""

import asyncio
from collections.abc import Awaitable
from typing import Any, TypeVar

from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T], timeout: float, timeout_message: str | None = None
) -> T:
    """Run coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        msg = timeout_message or f"Operation timed out after {timeout}s"
        logger.warning("timeout_occurred", message=msg, timeout=timeout)
        raise


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """Safely convert value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    try:
        return bool(value)
    except (ValueError, TypeError):
        return default
