# server/src/server/services/command_extraction.py
"""
Command Extraction Service

Main service for extracting drone commands from natural language input.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

import structlog

from server.services.llm.factory import LLMServiceFactory
from server.services.llm.pipeline import PromptPipeline
from server.core.drone_manager import DroneManager

logger = structlog.get_logger()


class CommandExtractionService:
    """
    Service for extracting and processing drone commands from natural language.
    
    This service:
    - Loads available commands from YAML definitions
    - Uses LLM pipeline to extract commands
    - Validates extracted commands
    - Prepares commands for execution
    """
    
    def __init__(self):
        """Initialize command extraction service."""
        self.llm_service = LLMServiceFactory.create()
        self.pipeline = PromptPipeline(self.llm_service)
        self.drone_manager = DroneManager()
        self.commands_cache: Dict[str, Dict[str, Any]] = {}
        
        # Load commands on initialization
        self._load_commands()
        
    def _load_commands(self):
        """Load command definitions from YAML files."""
        commands_path = Path(__file__).parent.parent.parent.parent.parent / "shared" / "commands"
        
        if not commands_path.exists():
            logger.warning("Commands directory not found", path=str(commands_path))
            return
            
        # Load all YAML files recursively
        for yaml_file in commands_path.rglob("*.yaml"):
            if yaml_file.name.startswith("_"):
                continue  # Skip metadata files
                
            try:
                with open(yaml_file, "r") as f:
                    command_data = yaml.safe_load(f)
                    
                if command_data and command_data.get("kind") == "DroneCommand":
                    metadata = command_data.get("metadata", {})
                    command_name = metadata.get("name")
                    
                    if command_name:
                        self.commands_cache[command_name] = command_data
                        logger.info(
                            "Loaded command definition",
                            command=command_name,
                            version=metadata.get("version", "1.0.0")
                        )
                        
            except Exception as e:
                logger.error(
                    "Failed to load command definition",
                    file=str(yaml_file),
                    error=str(e)
                )
                
    def get_available_commands(self) -> List[Dict[str, Any]]:
        """
        Get list of available commands.
        
        Returns:
            List of command metadata
        """
        commands = []
        
        for name, data in self.commands_cache.items():
            metadata = data.get("metadata", {})
            spec = data.get("spec", {})
            
            commands.append({
                "name": name,
                "category": metadata.get("category", "uncategorized"),
                "description": spec.get("description", {}).get("brief", ""),
                "tags": metadata.get("tags", []),
                "version": metadata.get("version", "1.0.0"),
                "deprecated": metadata.get("deprecated", False)
            })
            
        return commands
        
    def get_command_specification(self, command_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full command specification.
        
        Args:
            command_name: Name of the command
            
        Returns:
            Command specification or None if not found
        """
        command_data = self.commands_cache.get(command_name)
        if command_data:
            return command_data.get("spec", {})
        return None
        
    async def extract_command(
        self,
        user_input: str,
        drone_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extract command from natural language input.
        
        Args:
            user_input: Natural language input from user
            drone_id: Target drone ID (optional)
            context: Additional context
            
        Returns:
            Extraction result with command, parameters, and metadata
        """
        # Get available commands
        available_commands = self.get_available_commands()
        
        # Filter out deprecated commands
        available_commands = [
            cmd for cmd in available_commands
            if not cmd.get("deprecated", False)
        ]
        
        # Get drone state if drone_id provided
        drone_state = {}
        if drone_id and drone_id in self.drone_manager.drones:
            drone_session = self.drone_manager.drones[drone_id]
            if drone_session.last_telemetry:
                drone_state = {
                    "armed": drone_session.last_telemetry.get("flight", {}).get("armed", False),
                    "is_flying": drone_session.last_telemetry.get("flight", {}).get("is_flying", False),
                    "battery_percent": drone_session.last_telemetry.get("battery", {}).get("percent", 0),
                    "gps_fix": drone_session.last_telemetry.get("gps", {}).get("fix", False),
                    "altitude": drone_session.last_telemetry.get("position", {}).get("altitude", 0),
                }
                
        # Prepare context with command specifications
        pipeline_context = {
            "drone_id": drone_id,
            **(context or {})
        }
        
        # Run pipeline
        result = await self.pipeline.process(
            user_input=user_input,
            available_commands=available_commands,
            drone_state=drone_state,
            context=pipeline_context
        )
        
        # Add command specification to result if command was extracted
        if result.get("command"):
            command_spec = self.get_command_specification(result["command"])
            if command_spec:
                pipeline_context["command_specification"] = command_spec
                
                # Re-run parameter extraction with full spec if needed
                if not result.get("parameters"):
                    # This would trigger parameter extraction stage again
                    # For now, we'll use defaults
                    default_params = {}
                    for param_name, param_spec in command_spec.get("parameters", {}).items():
                        if "default" in param_spec:
                            default_params[param_name] = param_spec["default"]
                    result["parameters"] = default_params
                    
        return result
        
    async def validate_command(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        drone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate command and parameters.
        
        Args:
            command_name: Command name
            parameters: Command parameters
            drone_id: Target drone ID
            
        Returns:
            Validation result
        """
        # Get command specification
        command_spec = self.get_command_specification(command_name)
        if not command_spec:
            return {
                "valid": False,
                "errors": [f"Unknown command: {command_name}"]
            }
            
        errors = []
        warnings = []
        
        # Check required parameters
        param_specs = command_spec.get("parameters", {})
        for param_name, param_spec in param_specs.items():
            if param_spec.get("required", False) and param_name not in parameters:
                errors.append(f"Missing required parameter: {param_name}")
                
        # Validate parameter constraints
        for param_name, value in parameters.items():
            if param_name not in param_specs:
                warnings.append(f"Unknown parameter: {param_name}")
                continue
                
            param_spec = param_specs[param_name]
            constraints = param_spec.get("constraints", {})
            
            # Type checking
            expected_type = param_spec.get("type", "string")
            if not self._check_type(value, expected_type):
                errors.append(f"Parameter '{param_name}' must be of type {expected_type}")
                
            # Range checking
            if "min" in constraints and value < constraints["min"]:
                errors.append(f"Parameter '{param_name}' must be >= {constraints['min']}")
            if "max" in constraints and value > constraints["max"]:
                errors.append(f"Parameter '{param_name}' must be <= {constraints['max']}")
                
            # Enum checking
            if "enum" in constraints and value not in constraints["enum"]:
                errors.append(f"Parameter '{param_name}' must be one of: {constraints['enum']}")
                
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
        
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "float": (int, float),
            "integer": int,
            "string": str,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected_python_type = type_map.get(expected_type, str)
        return isinstance(value, expected_python_type)