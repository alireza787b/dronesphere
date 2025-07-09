# server/client.py
"""Server client for agent communication."""

import asyncio
from typing import Dict, Any, Optional

import httpx

from dronesphere.core.logging import get_logger
from .config import get_server_settings

logger = get_logger(__name__)


class AgentClient:
    """HTTP client for communicating with drone agents."""
    
    def __init__(self):
        self.settings = get_server_settings()
        self.client: Optional[httpx.AsyncClient] = None
        
    async def start(self) -> None:
        """Start the client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.agent_timeout)
        )
        
    async def stop(self) -> None:
        """Stop the client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            
    async def request_with_retry(
        self, 
        method: str, 
        agent_host: str, 
        agent_port: int, 
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Make request to agent with retry logic."""
        url = f"http://{agent_host}:{agent_port}{endpoint}"
        
        for attempt in range(1, self.settings.retry_max_attempts + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                # Only log warnings for actual failures, not timeouts during busy operations
                if "timeout" not in str(e).lower() and "connection" not in str(e).lower():
                    logger.warning("agent_request_failed",
                                 agent=f"{agent_host}:{agent_port}",
                                 endpoint=endpoint,
                                 attempt=attempt,
                                 error=str(e))
                else:
                    logger.debug("agent_request_timeout",
                               agent=f"{agent_host}:{agent_port}",
                               endpoint=endpoint,
                               attempt=attempt)
                
                if attempt < self.settings.retry_max_attempts:
                    # Exponential backoff
                    delay = self.settings.retry_backoff ** attempt
                    await asyncio.sleep(delay)
                else:
                    logger.error("agent_request_exhausted",
                               agent=f"{agent_host}:{agent_port}",
                               endpoint=endpoint,
                               max_attempts=self.settings.retry_max_attempts)
                    return None
                    
    async def ping_agent(self, agent_host: str, agent_port: int) -> bool:
        """Ping agent to check connectivity."""
        result = await self.request_with_retry("GET", agent_host, agent_port, "/ping")
        return result is not None
        
    async def get_agent_health(self, agent_host: str, agent_port: int) -> Optional[Dict[str, Any]]:
        """Get agent health status."""
        return await self.request_with_retry("GET", agent_host, agent_port, "/health")
        
    async def get_agent_status(self, agent_host: str, agent_port: int) -> Optional[Dict[str, Any]]:
        """Get agent status."""
        return await self.request_with_retry("GET", agent_host, agent_port, "/status")
        
    async def get_agent_telemetry(self, agent_host: str, agent_port: int) -> Optional[Dict[str, Any]]:
        """Get agent telemetry."""
        return await self.request_with_retry("GET", agent_host, agent_port, "/telemetry")
        
    async def send_command(
        self, 
        agent_host: str, 
        agent_port: int, 
        command_sequence: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send command to agent."""
        return await self.request_with_retry(
            "POST", agent_host, agent_port, "/commands",
            json=command_sequence
        )
        
    async def emergency_stop_agent(self, agent_host: str, agent_port: int) -> Optional[Dict[str, Any]]:
        """Send emergency stop to agent."""
        return await self.request_with_retry("POST", agent_host, agent_port, "/emergency_stop")
        
    async def get_agent_history(
        self, 
        agent_host: str, 
        agent_port: int,
        limit: int = 50,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Get agent command history."""
        return await self.request_with_retry(
            "GET", agent_host, agent_port, "/history",
            params={"limit": limit, "offset": offset}
        )