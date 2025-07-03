# server/src/server/api/v1/chat.py
"""
Chat API for conversational drone control.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

import structlog

from ...services.conversation.manager import conversation_manager
from ...services.command.pipeline import CommandPipeline
from ...core.drone_manager import drone_manager

logger = structlog.get_logger()

router = APIRouter()

# Command pipeline instance
command_pipeline = CommandPipeline()


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    session_id: Optional[str] = None
    drone_id: str


class ChatResponse(BaseModel):
    """Chat response model."""
    session_id: str
    response: str
    commands: List[Dict[str, Any]]
    requires_clarification: bool = False
    clarification_questions: List[str] = []


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message to the drone assistant."""
    
    # Get or create session
    if request.session_id:
        session = await conversation_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = await conversation_manager.create_session(
            drone_id=request.drone_id
        )
    
    # Get available commands (from shared/commands or config)
    available_commands = get_available_commands()
    
    # Process message
    result = await conversation_manager.process_message(
        session.session_id,
        request.message,
        available_commands
    )
    
    # If commands were extracted, process through pipeline
    if result.get("commands"):
        pipeline_result = await command_pipeline.process_commands(
            result["commands"],
            request.drone_id,
            session.session_id
        )
        
        # Send manifest to drone if connected
        drone_session = drone_manager.get_drone_session(request.drone_id)
        if drone_session and pipeline_result.get("manifest"):
            await drone_manager.send_command_manifest(
                request.drone_id,
                pipeline_result["manifest"]
            )
    
    return ChatResponse(
        session_id=session.session_id,
        response=result["response"],
        commands=result.get("commands", []),
        requires_clarification=result.get("requires_clarification", False),
        clarification_questions=result.get("clarification_questions", [])
    )


@router.get("/sessions/{drone_id}")
async def get_drone_sessions(drone_id: str):
    """Get all chat sessions for a drone."""
    sessions = await conversation_manager.get_drone_sessions(drone_id)
    return {
        "drone_id": drone_id,
        "sessions": [
            {
                "session_id": s.session_id,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "message_count": len(s.messages),
                "active": s.active
            }
            for s in sessions
        ]
    }


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    session = await conversation_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in session.messages
        ]
    }


def get_available_commands() -> List[Dict[str, Any]]:
    """Get available commands (placeholder - implement based on your structure)."""
    # For now, return basic commands
    return [
        {
            "metadata": {"name": "takeoff", "category": "flight"},
            "spec": {
                "description": {"brief": "Take off to altitude"},
                "parameters": {
                    "altitude": {"type": "float", "required": True, "default": 10.0}
                }
            }
        },
        {
            "metadata": {"name": "land", "category": "flight"},
            "spec": {
                "description": {"brief": "Land at current position"},
                "parameters": {}
            }
        },
        {
            "metadata": {"name": "move_local", "category": "navigation"},
            "spec": {
                "description": {"brief": "Move in local coordinates"},
                "parameters": {
                    "north": {"type": "float", "required": False, "default": 0},
                    "east": {"type": "float", "required": False, "default": 0},
                    "down": {"type": "float", "required": False, "default": 0}
                }
            }
        }
    ]