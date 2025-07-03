# server/src/server/services/conversation/manager.py
"""
Main conversation manager handling all drone conversations.
"""

from typing import Dict, Optional, List
import asyncio
from datetime import datetime, timedelta

import structlog
from langchain.memory import ConversationBufferWindowMemory

from .session import ConversationSession
from server.services.llm import get_llm_provider_sync  # Fixed path
from server.services.llm.base import ConversationContext, CommandExtractionResult  # Fixed path
from server.core.config import get_settings  # Fixed path

logger = structlog.get_logger()


class ConversationManager:
    """Manages all conversation sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self.llm_provider = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM provider."""
        try:
            from ...core.config import get_settings
            settings = get_settings()
            self.llm_provider = get_llm_provider_sync(settings)
            logger.info("LLM provider initialized for conversation manager")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
    
    async def create_session(
        self, 
        drone_id: str, 
        user_id: Optional[str] = None
    ) -> ConversationSession:
        """Create a new conversation session."""
        async with self._lock:
            session = ConversationSession(
                drone_id=drone_id,
                user_id=user_id
            )
            self.sessions[session.session_id] = session
            
            logger.info(
                "Created conversation session",
                session_id=session.session_id,
                drone_id=drone_id
            )
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    async def get_drone_sessions(
        self, 
        drone_id: str, 
        active_only: bool = True
    ) -> List[ConversationSession]:
        """Get all sessions for a drone."""
        sessions = []
        for session in self.sessions.values():
            if session.drone_id == drone_id:
                if not active_only or session.active:
                    sessions.append(session)
        
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    async def process_message(
        self,
        session_id: str,
        message: str,
        available_commands: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """Process a user message and extract commands."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Add user message
        session.add_message("user", message)
        
        # Create context for LLM
        context = ConversationContext(
            session_id=session_id,
            drone_id=session.drone_id,
            history=session.get_context_window(),
            language=session.language,
            drone_state=session.context.get("drone_state"),
            user_preferences=session.context.get("user_preferences", {})
        )
        
        # Extract commands using LLM
        try:
            result = await self.llm_provider.extract_commands(
                message,
                context,
                available_commands
            )
            
            # Add assistant response
            session.add_message(
                "assistant",
                result.response_text,
                commands=result.commands,
                confidence=result.confidence
            )
            
            # Update session language if detected
            if result.detected_language:
                session.language = result.detected_language
            
            return {
                "session_id": session_id,
                "commands": result.commands,
                "response": result.response_text,
                "requires_clarification": result.requires_clarification,
                "clarification_questions": result.clarification_questions,
                "confidence": result.confidence,
                "language": result.detected_language
            }
            
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            error_response = "I'm sorry, I encountered an error processing your request."
            session.add_message("assistant", error_response, error=str(e))
            
            return {
                "session_id": session_id,
                "commands": [],
                "response": error_response,
                "error": str(e)
            }
    
    async def end_session(self, session_id: str):
        """End a conversation session."""
        async with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].active = False
                logger.info(f"Ended session {session_id}")
    
    async def cleanup_old_sessions(self, hours: int = 24):
        """Clean up inactive sessions older than specified hours."""
        async with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            to_remove = []
            
            for session_id, session in self.sessions.items():
                if not session.active and session.updated_at < cutoff_time:
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                del self.sessions[session_id]
                
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old sessions")


# Singleton instance
conversation_manager = ConversationManager()