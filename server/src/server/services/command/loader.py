# server/src/server/services/command/loader.py
"""
Load commands from YAML definitions.
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class CommandLoader:
    """Load command definitions from YAML files."""
    
    def __init__(self, commands_path: str = "shared/commands"):
        self.commands_path = Path(commands_path)
        self.commands = {}
        self.load_all_commands()
    
    def load_all_commands(self):
        """Load all command YAML files."""
        for yaml_file in self.commands_path.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    command_data = yaml.safe_load(f)
                    name = command_data.get('metadata', {}).get('name')
                    if name:
                        self.commands[name] = command_data
                        logger.info(f"Loaded command: {name}")
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """Get all loaded commands."""
        return list(self.commands.values())
    
    def get_command(self, name: str) -> Dict[str, Any]:
        """Get a specific command by name."""
        return self.commands.get(name)


# Singleton instance
command_loader = CommandLoader()