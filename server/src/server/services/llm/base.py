# server/src/server/services/llm/base.py
"""
Base LLM Service Interface

Defines the abstract interface for all LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import structlog

logger = structlog.get_logger()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


@dataclass
class LLMMessage:
    """Standard message format for LLM interactions."""
    
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standard response from LLM providers."""
    
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMService(ABC):
    """
    Abstract base class for LLM service implementations.
    
    All LLM providers must implement this interface to ensure
    compatibility with the DroneSphere system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize LLM service.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.provider = self._get_provider_name()
        
    @abstractmethod
    def _get_provider_name(self) -> str:
        """Get the provider name."""
        pass
        
    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Get completion from LLM.
        
        Args:
            messages: List of messages in conversation
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with generated content
        """
        pass
        
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the LLM service is available.
        
        Returns:
            True if service is reachable and configured
        """
        pass
        
    async def extract_json(
        self,
        messages: List[LLMMessage],
        schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Extract structured JSON from LLM response.
        
        Args:
            messages: Conversation messages
            schema: Expected JSON schema (for validation)
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON object
        """
        import json
        
        # Add JSON instruction to last user message
        if messages and messages[-1].role == "user":
            messages[-1].content += "\n\nRespond with valid JSON only."
            
        response = await self.complete(
            messages=messages,
            temperature=0.1,  # Low temperature for consistent JSON
            **kwargs
        )
        
        try:
            # Extract JSON from response
            content = response.content.strip()
            
            # Try to find JSON in the response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            result = json.loads(content)
            
            # TODO: Validate against schema if provided
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from LLM",
                provider=self.provider,
                error=str(e),
                response=response.content[:200]
            )
            raise ValueError(f"LLM returned invalid JSON: {str(e)}")
            
    def create_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        assistant_prompt: Optional[str] = None
    ) -> List[LLMMessage]:
        """
        Helper to create message list.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            assistant_prompt: Optional assistant message
            
        Returns:
            List of LLMMessage objects
        """
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        if assistant_prompt:
            messages.append(LLMMessage(role="assistant", content=assistant_prompt))
            
        return messages