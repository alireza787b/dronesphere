"""Dynamic command registry for DroneSphere - Final Working Version.

Path: agent/command_registry.py
Handles relative imports correctly.
"""
import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)


class CommandRegistry:
    """Dynamic command discovery and registration system."""

    def __init__(self, schemas_dir: str = None, commands_dir: str = None):
        """Initialize command registry.

        Args:
            schemas_dir: Directory containing YAML command schemas
            commands_dir: Directory containing Python command implementations
        """
        # Get absolute paths based on this file's location
        current_file = Path(__file__).resolve()
        agent_dir = current_file.parent
        project_root = agent_dir.parent

        # Set directories with absolute paths
        self.schemas_dir = (
            Path(schemas_dir) if schemas_dir else project_root / "shared" / "command_schemas"
        )
        self.commands_dir = Path(commands_dir) if commands_dir else agent_dir / "commands"

        self.commands: Dict[str, Type] = {}
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.validators: Dict[str, Draft7Validator] = {}

        # Ensure paths are in sys.path for imports to work
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        if str(agent_dir) not in sys.path:
            sys.path.insert(0, str(agent_dir))

        logger.info(f"CommandRegistry initialized:")
        logger.info(f"  Commands dir: {self.commands_dir}")
        logger.info(f"  Schemas dir: {self.schemas_dir}")

    def discover_and_register(self) -> None:
        """Auto-discover and register all commands."""
        logger.info(f"🔍 Starting command discovery...")

        # Discover Python command files using module imports (not file loading)
        if self.commands_dir.exists():
            command_files = [
                f for f in self.commands_dir.glob("*.py") if f.stem not in ["__init__", "base"]
            ]
            logger.info(f"📁 Found {len(command_files)} command files")

            for command_file in command_files:
                command_name = command_file.stem
                if self._load_command_module(command_name):
                    logger.info(f"✅ Loaded command: {command_name}")
                else:
                    logger.warning(f"⚠️  Failed to load: {command_name}")
        else:
            logger.error(f"Commands directory not found: {self.commands_dir}")

        # Discover YAML schemas
        if self.schemas_dir.exists():
            schema_files = [
                f for f in self.schemas_dir.glob("*.yaml") if f.stem != "fleet_discovery"
            ]
            logger.info(f"📁 Found {len(schema_files)} schema files")

            for schema_file in schema_files:
                try:
                    with open(schema_file, 'r') as f:
                        schema_data = yaml.safe_load(f)

                    if command_name := schema_data.get('name'):
                        self.schemas[command_name] = schema_data

                        if 'validation_schema' in schema_data:
                            self.validators[command_name] = Draft7Validator(
                                schema_data['validation_schema']
                            )
                        logger.info(f"📋 Loaded schema: {command_name}")

                except Exception as e:
                    logger.error(f"Failed to load schema {schema_file}: {e}")
        else:
            logger.warning(f"Schemas directory not found: {self.schemas_dir}")

        logger.info(f"🚀 Registry ready: {len(self.commands)} commands, {len(self.schemas)} schemas")

    def _load_command_module(self, command_name: str) -> bool:
        """Load command class using proper module import.

        Args:
            command_name: Name of the command

        Returns:
            True if class was loaded successfully
        """
        try:
            # Use standard module import which handles relative imports correctly
            module_path = f"commands.{command_name}"

            # Import the module (this will handle relative imports properly)
            module = importlib.import_module(module_path)

            # Find the command class
            class_name = self._find_command_class(module, command_name)
            if class_name:
                command_class = getattr(module, class_name)
                self.commands[command_name] = command_class
                return True
            else:
                logger.warning(f"No command class found in {module_path}")
                return False

        except ImportError as e:
            # Try with agent prefix
            try:
                module_path = f"agent.commands.{command_name}"
                module = importlib.import_module(module_path)

                class_name = self._find_command_class(module, command_name)
                if class_name:
                    command_class = getattr(module, class_name)
                    self.commands[command_name] = command_class
                    return True

            except ImportError as e2:
                logger.error(f"Cannot import {command_name}: {e} / {e2}")
                return False

        except Exception as e:
            logger.error(f"Error loading {command_name}: {e}")
            return False

    def _find_command_class(self, module, command_name: str) -> Optional[str]:
        """Find command class in module using various naming conventions.

        Args:
            module: The imported module
            command_name: Name of the command

        Returns:
            Name of the found class or None
        """
        # Special cases mapping
        special_cases = {
            "rtl": "RTLCommand",
            "goto": "GotoCommand",
        }

        # Try different naming conventions
        possible_names = [
            # Special cases first
            special_cases.get(command_name.lower()),
            # Standard convention: capitalize first letter
            f"{command_name.capitalize()}Command",
            # All caps
            f"{command_name.upper()}Command",
            # Title case for underscored names
            ''.join(p.capitalize() for p in command_name.split('_')) + 'Command',
            # Exact match
            f"{command_name}Command",
        ]

        # Check each possible name
        for name in possible_names:
            if name and hasattr(module, name):
                # Verify it's a class
                obj = getattr(module, name)
                if inspect.isclass(obj):
                    return name

        # If no convention works, find any class ending with "Command" that's not BaseCommand
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                name.endswith("Command")
                and name != "BaseCommand"
                and obj.__module__ == module.__name__
            ):
                logger.info(f"Found command class by suffix: {name}")
                return name

        return None

    def validate_params(self, command_name: str, params: Dict[str, Any]) -> List[str]:
        """Validate command parameters against schema.

        Args:
            command_name: Name of the command
            params: Parameters to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        if command_name not in self.validators:
            return []  # No validation schema defined

        errors = []
        try:
            validator = self.validators[command_name]
            for error in validator.iter_errors(params):
                path = '.'.join(str(p) for p in error.path) if error.path else 'root'
                errors.append(f"{path}: {error.message}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def get_command_class(self, command_name: str) -> Optional[Type]:
        """Get command class by name."""
        return self.commands.get(command_name)

    def get_schema(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get command schema by name."""
        return self.schemas.get(command_name)

    def list_commands(self) -> List[str]:
        """Get list of all registered command names."""
        return list(self.commands.keys())

    def get_command_info(self) -> List[Dict[str, Any]]:
        """Get information about all registered commands."""
        info = []
        all_names = set(self.commands.keys()) | set(self.schemas.keys())

        for name in all_names:
            schema = self.schemas.get(name, {})
            info.append(
                {
                    "name": name,
                    "description": schema.get("description", f"Execute {name}"),
                    "category": schema.get("category", "uncategorized"),
                    "has_implementation": name in self.commands,
                    "has_schema": name in self.schemas,
                    "has_validation": name in self.validators,
                    "parameters": self._extract_parameters(schema) if schema else [],
                }
            )

        return info

    def _extract_parameters(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameter information from schema."""
        params = []
        validation_schema = schema.get("validation_schema", {})
        properties = validation_schema.get("properties", {})
        required = validation_schema.get("required", [])

        for param_name, param_schema in properties.items():
            params.append(
                {
                    "name": param_name,
                    "type": param_schema.get("type", "any"),
                    "required": param_name in required,
                    "description": param_schema.get("description", ""),
                    "default": param_schema.get("default"),
                    "minimum": param_schema.get("minimum"),
                    "maximum": param_schema.get("maximum"),
                }
            )

        return params
