# server/src/server/services/command/pipeline.py
"""
Command processing pipeline.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio

import structlog
from pydantic import BaseModel

from .validator import CommandValidator
from .protocol import CommandProtocol

logger = structlog.get_logger()


class CommandStatus(str, Enum):
    """Command execution status."""
    PENDING = "pending"
    VALIDATED = "validated"
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessedCommand(BaseModel):
    """Processed command ready for execution."""
    command_id: str
    name: str
    parameters: Dict[str, Any]
    status: CommandStatus = CommandStatus.PENDING
    validation_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CommandPipeline:
    """Processes commands through validation and prepares for execution."""
    
    def __init__(self):
        self.validator = CommandValidator()
        self.protocol = CommandProtocol()
        self.command_queue: List[ProcessedCommand] = []
    
    async def process_commands(
        self,
        commands: List[Dict[str, Any]],
        drone_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Process a list of commands through the pipeline."""
        processed_commands = []
        
        for idx, cmd in enumerate(commands):
            # Create processed command
            processed_cmd = ProcessedCommand(
                command_id=f"{session_id}_{idx}",
                name=cmd.get("name"),
                parameters=cmd.get("parameters", {})
            )
            
            # Validate command
            validation_result = await self.validator.validate(
                cmd.get("name"),
                cmd.get("parameters", {}),
                drone_id
            )
            
            processed_cmd.validation_result = validation_result
            
            if validation_result["valid"]:
                processed_cmd.status = CommandStatus.VALIDATED
            else:
                processed_cmd.status = CommandStatus.FAILED
                processed_cmd.error = validation_result.get("error")
            
            processed_commands.append(processed_cmd)
        
        # Create execution manifest
        valid_commands = [
            cmd for cmd in processed_commands 
            if cmd.status == CommandStatus.VALIDATED
        ]
        
        manifest = self.protocol.create_manifest(
            drone_id=drone_id,
            session_id=session_id,
            commands=valid_commands
        )
        
        return {
            "processed_commands": [cmd.dict() for cmd in processed_commands],
            "valid_count": len(valid_commands),
            "total_count": len(commands),
            "manifest": manifest
        }