# server/src/server/services/llm/base.py
"""
Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement
to ensure consistency across different LLM backends (OpenRouter, OpenAI, Ollama, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class ConversationContext(BaseModel):
    """Context for maintaining conversation state."""

    session_id: str
    history: list[dict[str, str]] = []
    language: str | None = None
    drone_id: str | None = "default"
    drone_state: dict[str, Any] | None = None
    user_preferences: dict[str, Any] = {}


class CommandExtractionResult(BaseModel):
    """Result of command extraction from user input."""

    commands: list[dict[str, Any]] = []
    confidence: float = 0.0
    response_text: str = ""
    requires_clarification: bool = False
    clarification_questions: list[str] = []
    detected_language: str | None = None
    error: str | None = None


class ClarificationRequest(BaseModel):
    """Request for clarification from user."""

    original_input: str
    ambiguous_parts: list[str]
    suggestions: list[str]
    context: ConversationContext


class ClarificationResponse(BaseModel):
    """Response to clarification request."""

    clarified_input: str
    confidence: float
    response_text: str


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (OpenRouter, OpenAI, Ollama, etc.) must implement this interface
    to ensure they can be used interchangeably in the system.
    """

    def __init__(self, config: dict[str, Any], parser=None):
        """
        Initialize the LLM provider.

        Args:
            config: Provider-specific configuration
            parser: Optional parser instance for output parsing
        """
        self.config = config
        self.name = self.__class__.__name__
        self.parser = parser  # Generic parser can be injected
        logger.info("Initializing LLM provider", provider=self.name)

    @abstractmethod
    async def extract_commands(
        self,
        user_input: str,
        context: ConversationContext,
        available_commands: list[dict[str, Any]],
    ) -> CommandExtractionResult:
        """
        Extract drone commands from natural language input.

        Args:
            user_input: The user's natural language input
            context: Current conversation context
            available_commands: List of available command schemas

        Returns:
            CommandExtractionResult containing extracted commands and metadata
        """
        pass

    @abstractmethod
    async def generate_response(
        self, prompt: str, context: ConversationContext | None = None, **kwargs
    ) -> str:
        """
        Generate a general response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            context: Optional conversation context
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated response text
        """
        pass

    @abstractmethod
    async def handle_clarification(
        self, clarification_request: ClarificationRequest
    ) -> ClarificationResponse:
        """
        Handle ambiguous commands by requesting clarification.

        Args:
            clarification_request: Details about what needs clarification

        Returns:
            ClarificationResponse with clarified interpretation
        """
        pass

    @abstractmethod
    async def format_error_response(
        self, error: Exception, context: ConversationContext, user_input: str
    ) -> str:
        """
        Format an error into a user-friendly response.

        Args:
            error: The exception that occurred
            context: Current conversation context
            user_input: The original user input that caused the error

        Returns:
            User-friendly error message in the appropriate language
        """
        pass

    @abstractmethod
    async def check_health(self) -> tuple[bool, str]:
        """
        Check if the LLM provider is healthy and accessible.

        Returns:
            Tuple of (is_healthy, status_message)
        """
        pass

    def get_conversation_prompt(
        self, context: ConversationContext, system_prompt: str | None = None
    ) -> list[dict[str, str]]:
        """
        Build conversation prompt with history.

        Args:
            context: Current conversation context
            system_prompt: Optional system prompt override

        Returns:
            List of messages for the conversation
        """
        messages = []

        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add conversation history
        for msg in context.history[-10:]:  # Last 10 messages for context window
            messages.append(msg)

        return messages

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
