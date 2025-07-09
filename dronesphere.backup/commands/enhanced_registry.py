"""Enhanced command registry with auto-discovery."""

import importlib
import pkgutil
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


class EnhancedCommandRegistry:
    """Enhanced registry with auto-discovery and categorization."""
    
    def __init__(self):
        self._commands: Dict[str, CommandSpec] = {}
        self._implementations: Dict[str, Type[BaseCommand]] = {}
        self._categories: Dict[str, List[str]] = {}
        
    def auto_discover_and_load(self) -> None:
        """Auto-discover commands from both YAML specs and Python implementations."""
        # Load YAML specifications
        self._load_yaml_specs()
        
        # Auto-discover Python implementations
        self._discover_implementations()
        
        # Validate and register matching pairs
        self._validate_and_register()
        
    def _load_yaml_specs(self) -> None:
        """Load command specifications from YAML files."""
        settings = get_settings()
        command_path = settings.paths.command_library_path
        
        if not command_path.exists():
            logger.warning("command_library_not_found", path=str(command_path))
            return
            
        logger.info("loading_yaml_specs", path=str(command_path))
        
        yaml_files = list(command_path.rglob("*.yaml")) + list(command_path.rglob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    
                spec = CommandSpec(**data)
                self._commands[spec.metadata.name] = spec
                
                # Track category
                category = yaml_file.parent.name
                if category not in self._categories:
                    self._categories[category] = []
                self._categories[category].append(spec.metadata.name)
                
                logger.info("yaml_spec_loaded", 
                           command=spec.metadata.name,
                           category=category,
                           file=str(yaml_file))
                    
            except Exception as e:
                logger.error("yaml_spec_load_failed", 
                            file=str(yaml_file), 
                            error=str(e))
                
    def _discover_implementations(self) -> None:
        """Auto-discover command implementations from categorized Python files."""
        base_package = "dronesphere.commands"
        
        # Discover in each category directory
        for category in ["basic", "navigation", "utility", "advanced"]:
            try:
                category_package = f"{base_package}.{category}"
                logger.info("discovering_category", category=category, package=category_package)
                
                # Import the category package
                category_module = importlib.import_module(category_package)
                
                # Get all command classes from __all__ if available
                if hasattr(category_module, "__all__"):
                    for class_name in category_module.__all__:
                        try:
                            command_class = getattr(category_module, class_name)
                            if issubclass(command_class, BaseCommand):
                                # Extract command name from class name
                                # TakeoffCommand -> takeoff
                                command_name = class_name.replace("Command", "").lower()
                                
                                self._implementations[command_name] = command_class
                                logger.info("implementation_discovered",
                                           command=command_name,
                                           category=category,
                                           class_name=class_name)
                                           
                        except Exception as e:
                            logger.error("implementation_load_failed",
                                       class_name=class_name,
                                       category=category,
                                       error=str(e))
                            
            except ImportError as e:
                logger.warning("category_import_failed", 
                              category=category, 
                              error=str(e))
                              
    def _validate_and_register(self) -> None:
        """Validate that specs and implementations match."""
        for command_name in self._commands:
            if command_name not in self._implementations:
                logger.warning("missing_implementation", command=command_name)
                
        for command_name in self._implementations:
            if command_name not in self._commands:
                logger.warning("missing_specification", command=command_name)
                
        # Log successful registrations
        valid_commands = set(self._commands.keys()) & set(self._implementations.keys())
        logger.info("commands_registered",
                   count=len(valid_commands),
                   commands=sorted(valid_commands),
                   categories=dict(self._categories))
    
    # Rest of the registry methods remain the same...
    def get_spec(self, name: str) -> CommandSpec:
        """Get command specification by name."""
        if name not in self._commands:
            raise CommandValidationError(f"Unknown command: {name}")
        return self._commands[name]
        
    def get_implementation(self, name: str) -> Type[BaseCommand]:
        """Get command implementation by name."""
        if name not in self._implementations:
            raise CommandValidationError(f"No implementation for command: {name}")
        return self._implementations[name]
        
    def list_commands(self) -> List[str]:
        """List all registered command names."""
        return sorted(list(set(self._commands.keys()) & set(self._implementations.keys())))
        
    def list_categories(self) -> Dict[str, List[str]]:
        """List commands by category."""
        return dict(self._categories)
        
    def create_command(self, name: str, params: Dict) -> BaseCommand:
        """Create a command instance with validated parameters."""
        # Validate parameters using spec
        spec = self.get_spec(name)
        validated_params = self.validate_parameters(name, params)
        
        # Create instance using implementation
        impl_class = self.get_implementation(name)
        return impl_class(name, validated_params)


# Global enhanced registry
_enhanced_registry = EnhancedCommandRegistry()


def get_enhanced_command_registry() -> EnhancedCommandRegistry:
    """Get the enhanced command registry."""
    return _enhanced_registry
