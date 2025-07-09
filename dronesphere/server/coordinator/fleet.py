# server/coordinator/fleet.py
"""Fleet management for multi-drone coordination."""

import asyncio
import time
from typing import Any

import yaml

from dronesphere.core.config import get_settings
from dronesphere.core.logging import get_logger

from ..client import AgentClient

logger = get_logger(__name__)


class DroneInfo:
    """Information about a drone and its agent."""

    def __init__(self, config: dict[str, Any]):
        self.id = config["id"]
        self.name = config["name"]
        self.type = config["type"]
        self.agent_host = config["agent"]["host"]
        self.agent_port = config["agent"]["port"]
        self.agent_timeout = config["agent"].get("timeout", 10.0)
        self.capabilities = config.get("capabilities", [])
        self.limits = config.get("limits", {})
        self.safety = config.get("safety", {})

        # Status tracking
        self.last_seen = time.time()
        self.connected = False
        self.health_status = "unknown"


class FleetManager:
    """Manages fleet of drones and their agents."""

    def __init__(self):
        self.settings = get_settings()
        self.client = AgentClient()
        self.drones: dict[int, DroneInfo] = {}
        self._running = False
        self._monitor_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start fleet manager."""
        if self._running:
            return

        logger.info("fleet_manager_starting")

        # Start agent client
        await self.client.start()

        # Load drone configuration
        await self._load_drone_config()

        # Start monitoring
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info("fleet_manager_started", drone_count=len(self.drones))

    async def stop(self) -> None:
        """Stop fleet manager."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        await self.client.stop()
        logger.info("fleet_manager_stopped")

    async def _load_drone_config(self) -> None:
        """Load drone configuration from YAML."""
        try:
            config_path = self.settings.paths.shared_config_path / "drones.yaml"

            with open(config_path) as f:
                config = yaml.safe_load(f)

            for drone_config in config.get("drones", []):
                drone = DroneInfo(drone_config)
                self.drones[drone.id] = drone

                logger.info(
                    "drone_registered",
                    drone_id=drone.id,
                    name=drone.name,
                    agent=f"{drone.agent_host}:{drone.agent_port}",
                )

        except Exception as e:
            logger.error("drone_config_load_failed", error=str(e))
            raise

    async def _monitor_loop(self) -> None:
        """Monitor all agents."""
        while self._running:
            try:
                # Check all drones
                for drone in self.drones.values():
                    await self._check_drone(drone)

            except Exception as e:
                logger.error("monitor_loop_error", error=str(e))

            await asyncio.sleep(10)  # Check every 10 seconds

    async def _check_drone(self, drone: DroneInfo) -> None:
        """Check individual drone status."""
        try:
            # Ping agent
            connected = await self.client.ping_agent(drone.agent_host, drone.agent_port)

            if connected:
                drone.connected = True
                drone.last_seen = time.time()

                # Get health status
                health = await self.client.get_agent_health(
                    drone.agent_host, drone.agent_port
                )
                if health:
                    drone.health_status = health.get("status", "unknown")

            else:
                drone.connected = False
                drone.health_status = "disconnected"

        except Exception as e:
            logger.warning("drone_check_failed", drone_id=drone.id, error=str(e))
            drone.connected = False
            drone.health_status = "error"

    def get_drone(self, drone_id: int) -> DroneInfo | None:
        """Get drone by ID."""
        return self.drones.get(drone_id)

    def list_drones(self) -> list[DroneInfo]:
        """List all drones."""
        return list(self.drones.values())

    def get_connected_drones(self) -> list[DroneInfo]:
        """Get list of connected drones."""
        return [drone for drone in self.drones.values() if drone.connected]

    async def send_command_to_drone(
        self, drone_id: int, command_sequence: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Send command to specific drone."""
        drone = self.get_drone(drone_id)
        if not drone:
            logger.error("drone_not_found", drone_id=drone_id)
            return None

        if not drone.connected:
            logger.error("drone_not_connected", drone_id=drone_id)
            return None

        return await self.client.send_command(
            drone.agent_host, drone.agent_port, command_sequence
        )
