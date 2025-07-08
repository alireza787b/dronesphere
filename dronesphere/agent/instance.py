"""Agent instance management.

This module provides a singleton agent instance to avoid circular imports
between main.py and api.py modules.
"""

from typing import Optional
from .config import get_agent_settings

# Global agent instance
_agent: Optional["DroneAgent"] = None

def get_agent() -> "DroneAgent":
    """Get the global agent instance."""
    global _agent
    if _agent is None:
        # Import here to avoid circular import
        from .main import DroneAgent
        _agent = DroneAgent()
    return _agent

def set_agent(agent: "DroneAgent") -> None:
    """Set the global agent instance."""
    global _agent
    _agent = agent
