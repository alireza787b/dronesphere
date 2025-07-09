"""Command registry and YAML loader."""

import importlib
from pathlib import Path
from typing import Dict, List, Type

import yaml
from pydantic import ValidationError

from ..core.config import get_settings
from ..core.errors import CommandValidationError, ConfigurationError
from ..core.logging import get_logger
from ..core.models import CommandSpec
from .base import BaseCommand

logger = get_logger(__name__)


class CommandRegistry:
    """Registry for command specifications and implementations."""
    
    def __init__(self):
        self._commands: Dict[str, CommandSpec] = {}
        self._implementations: Dict[str, Type[BaseCommand]] = {}
        
    def register_spec(self, spec: CommandSpec) -> None:
        """Register a command specification."""
        command_name = spec.metadata.name
        
        # Validate specification
        if command_name in self._commands:
            logger.warning("command_spec_overridden", command=command_name)
            
        self._commands[command_name] = spec
        logger.info("command_spec_registered", command=command_name, version=spec.metadata.version)
        
    def register_implementation(self, name: str, implementation: Type[BaseCommand]) -> None:
        """Register a command implementation."""
        self._implementations[name] = implementation
        logger.info("command_implementation_registered", command=name, impl_class=implementation.__name__)
        
    def get_spec(self, name: str) -> CommandSpec:
        """Get command specification by name."""
        if name not in self._commands:
            raise CommandValidationError(f"Unknown command: {name}")
        return self._commands[name]
        
    def get_implementation(self, name: str) -> Type[BaseCommand]:
        """Get command implementation by name."""
        spec = self.get_spec(name)  # This validates the command exists
        
        handler_path = spec.spec["implementation"]["handler"]
        
        # Check if already loaded
        if name in self._implementations:
            return self._implementations[name]
            
        # Dynamically import the implementation
        try:
            module_path, class_name = handler_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            implementation = getattr(module, class_name)
            
            # Validate it's a BaseCommand subclass
            if not issubclass(implementation, BaseCommand):
                raise CommandValidationError(
                    f"Command implementation {handler_path} must inherit from BaseCommand"
                )
                
            self._implementations[name] = implementation
            return implementation
            
        except Exception as e:
            logger.error("command_import_failed", command=name, handler=handler_path, error=str(e))
            raise CommandValidationError(f"Failed to import command {name}: {e}")
            
    def validate_parameters(self, name: str, params: Dict) -> Dict:
        """Validate and normalize command parameters."""
        spec = self.get_spec(name)
        parameters_spec = spec.spec.get("parameters", {})
        
        validated_params = {}
        
        for param_name, param_spec in parameters_spec.items():
            param_type = param_spec.get("type", "str")
            default_value = param_spec.get("default")
            constraints = param_spec.get("constraints", {})
            
            # Get value or default
            if param_name in params:
                value = params[param_name]
            elif default_value is not None:
                value = default_value
            else:
                raise CommandValidationError(
                    f"Required parameter '{param_name}' missing for command '{name}'"
                )
                
            # Type conversion
            try:
                if param_type == "float":
                    value = float(value)
                elif param_type == "int":
                    value = int(value)
                elif param_type == "bool":
                    if isinstance(value, str):
                        value = value.lower() in ("true", "1", "yes", "on")
                    else:
                        value = bool(value)
                elif param_type == "str":
                    value = str(value)
                else:
                    raise CommandValidationError(f"Unknown parameter type: {param_type}")
                    
            except ValueError as e:
                raise CommandValidationError(
                    f"Invalid value for parameter '{param_name}': {e}"
                )
                
            # Constraint validation
            if "min" in constraints and value < constraints["min"]:
                raise CommandValidationError(
                    f"Parameter '{param_name}' value {value} below minimum {constraints['min']}"
                )
            if "max" in constraints and value > constraints["max"]:
                raise CommandValidationError(
                    f"Parameter '{param_name}' value {value} above maximum {constraints['max']}"
                )
                
            validated_params[param_name] = value
            
        return validated_params
        
    def list_commands(self) -> List[str]:
        """List all registered command names."""
        return list(self._commands.keys())
        
    def create_command(self, name: str, params: Dict) -> BaseCommand:
        """Create a command instance with validated parameters."""
        # Validate parameters
        validated_params = self.validate_parameters(name, params)
        
        # Get implementation class
        impl_class = self.get_implementation(name)
        
        # Create instance
        return impl_class(name, validated_params)


# Global registry instance
_registry = CommandRegistry()


def get_command_registry() -> CommandRegistry:
    """Get the global command registry."""
    return _registry


def load_command_library() -> None:
    """Load command library from YAML files."""
    settings = get_settings()
    command_path = settings.paths.command_library_path
    
    if not command_path.exists():
        logger.warning("command_library_not_found", path=str(command_path))
        return
        
    logger.info("loading_command_library", path=str(command_path))
    
    # Load all YAML files recursively
    yaml_files = list(command_path.rglob("*.yaml")) + list(command_path.rglob("*.yml"))
    
    for yaml_file in yaml_files:
        try:
            logger.debug("loading_command_file", file=str(yaml_file))
            
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                
            # Support single command or list of commands
            if isinstance(data, list):
                commands = data
            else:
                commands = [data]
                
            for command_data in commands:
                try:
                    spec = CommandSpec(**command_data)
                    _registry.register_spec(spec)
                    
                except ValidationError as e:
                    logger.error("command_validation_failed", 
                               file=str(yaml_file), 
                               error=str(e))
                    
        except Exception as e:
            logger.error("command_file_load_failed", 
                        file=str(yaml_file), 
                        error=str(e))
            
    logger.info("command_library_loaded", 
               count=len(_registry.list_commands()),
               commands=_registry.list_commands())
