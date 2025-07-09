"""Agent heartbeat manager for server communication.

This module provides heartbeat functionality for agents to communicate their
status and availability to the coordination server.
"""

import asyncio
import time

import httpx

from dronesphere.core.logging import get_logger

logger = get_logger(__name__)


class HeartbeatManager:
    """Manages heartbeat communication with server."""

    def __init__(
        self,
        agent_port: int,
        server_host: str,
        server_port: int,
        interval: float = 30.0,
    ):
        self.agent_port = agent_port
        self.server_host = server_host
        self.server_port = server_port
        self.interval = interval
        self.client: httpx.AsyncClient | None = None
        self.task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start heartbeat."""
        if self._running:
            return

        self.client = httpx.AsyncClient(timeout=5.0)
        self._running = True
        self.task = asyncio.create_task(self._heartbeat_loop())

        logger.info(
            "heartbeat_started",
            server=f"{self.server_host}:{self.server_port}",
            interval=self.interval,
        )

    async def stop(self) -> None:
        """Stop heartbeat."""
        self._running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        if self.client:
            await self.client.aclose()
            self.client = None

        logger.info("heartbeat_stopped")

    async def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        consecutive_failures = 0

        while self._running:
            try:
                # Send heartbeat to server
                response = await self.client.post(
                    f"http://{self.server_host}:{self.server_port}/agents/heartbeat",
                    json={
                        "agent_port": self.agent_port,
                        "timestamp": time.time(),
                        "status": "alive",
                    },
                )

                if response.status_code == 200:
                    consecutive_failures = 0
                    logger.debug("heartbeat_sent")
                else:
                    consecutive_failures += 1
                    logger.warning(
                        "heartbeat_failed",
                        status_code=response.status_code,
                        consecutive_failures=consecutive_failures,
                    )

            except Exception as e:
                consecutive_failures += 1
                logger.warning(
                    "heartbeat_error",
                    error=str(e),
                    consecutive_failures=consecutive_failures,
                )

                # Log server communication issues
                if consecutive_failures >= 3:
                    logger.error(
                        "server_communication_lost",
                        consecutive_failures=consecutive_failures,
                    )

            await asyncio.sleep(self.interval)
