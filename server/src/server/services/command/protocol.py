# server/src/server/services/command/protocol.py
"""
Command protocol for drone communication.
"""

from typing import List, Dict, Any
from datetime import datetime
import json
import uuid

import structlog

logger = structlog.get_logger()


class CommandProtocol:
    """Creates command manifests for drone execution."""
    
    def create_manifest(
        self,
        drone_id: str,
        session_id: str,
        commands: List[Any]  # List of ProcessedCommand
    ) -> Dict[str, Any]:
        """Create a command manifest in JSON format."""
        
        manifest = {
            "manifest_id": str(uuid.uuid4()),
            "drone_id": drone_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "commands": []
        }
        
        for cmd in commands:
            manifest["commands"].append({
                "id": cmd.command_id,
                "name": cmd.name,
                "parameters": cmd.parameters,
                "sequence": len(manifest["commands"]) + 1
            })
        
        logger.info(
            "Created command manifest",
            manifest_id=manifest["manifest_id"],
            command_count=len(commands)
        )
        
        return manifest