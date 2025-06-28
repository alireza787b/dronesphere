# server/src/server/api/chat.py
"""
Chat API endpoints

Handles natural language interaction with the AI system.
"""


import structlog
from fastapi import APIRouter
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message model."""

    message: str
    drone_id: str | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    command: dict | None = None
    confidence: float = 1.0


@router.post("/", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Process a chat message and return AI response.

    This is a stub implementation.
    """
    logger.info("Chat request received", message=message.message)

    # TODO: Implement LLM integration
    # For now, return a simple response
    return ChatResponse(
        response="I understand you want to control the drone. This feature is coming soon!",
        confidence=0.9,
    )
