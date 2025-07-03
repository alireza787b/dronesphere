# server/src/server/services/conversation/session.py
"""
Conversation session management for drone interactions.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class Message(BaseModel):
    """Single message in conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    """Represents a conversation session with a drone."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    drone_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: List[Message] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    language: str = "en"
    active: bool = True
    
    def add_message(self, role: str, content: str, **metadata):
        """Add a message to the conversation."""
        self.messages.append(Message(
            role=role,
            content=content,
            metadata=metadata
        ))
        self.updated_at = datetime.utcnow()
    
    def get_context_window(self, window_size: int = 10) -> List[Dict[str, str]]:
        """Get recent messages for context."""
        recent_messages = self.messages[-window_size:]
        return [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]
    
    def to_langchain_messages(self):
        """Convert to LangChain message format."""
        from langchain.schema import HumanMessage, AIMessage, SystemMessage
        
        messages = []
        for msg in self.messages:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                messages.append(SystemMessage(content=msg.content))
        
        return messages