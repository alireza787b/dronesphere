# server/src/server/services/command/validator.py
"""
Command validation with configurable safety rules.
"""

from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class CommandValidator:
    """Validates commands with basic safety checks."""
    
    # Basic safety limits (configurable later)
    SAFETY_LIMITS = {
        "takeoff": {
            "altitude": {"min": 1.0, "max": 100.0}  # meters
        },
        "move_local": {
            "north": {"min": -50.0, "max": 50.0},  # meters
            "east": {"min": -50.0, "max": 50.0},   # meters
            "down": {"min": -50.0, "max": 50.0}    # meters (negative is up)
        }
    }
    
    async def validate(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        drone_id: str
    ) -> Dict[str, Any]:
        """Validate a command with its parameters."""
        
        # Check if command exists
        if command_name not in self.SAFETY_LIMITS:
            logger.warning(f"Unknown command: {command_name}")
            # For now, allow unknown commands (will be checked by drone)
            return {"valid": True, "warnings": ["Unknown command"]}
        
        # Validate parameters
        limits = self.SAFETY_LIMITS.get(command_name, {})
        errors = []
        warnings = []
        
        for param_name, param_value in parameters.items():
            if param_name in limits:
                param_limits = limits[param_name]
                
                # Check numeric limits
                if isinstance(param_value, (int, float)):
                    if param_value < param_limits.get("min", float('-inf')):
                        errors.append(
                            f"{param_name} value {param_value} is below minimum {param_limits['min']}"
                        )
                    elif param_value > param_limits.get("max", float('inf')):
                        errors.append(
                            f"{param_name} value {param_value} exceeds maximum {param_limits['max']}"
                        )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "command": command_name,
            "parameters": parameters
        }