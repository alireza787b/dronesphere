# src/core/ports/output/nlp_service.py
"""Natural Language Processing port definitions.

This module defines the interfaces (ports) for NLP services in the system.
Following hexagonal architecture, these are pure interfaces with no implementation details.
Supports multiple providers: spaCy, OpenAI, Deepseek, Ollama, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.domain.value_objects.command import DroneCommand


class ConfidenceLevel(str, Enum):
    """Confidence levels for NLP parsing results."""
    
    HIGH = "HIGH"        # > 0.8 - Execute without confirmation
    MEDIUM = "MEDIUM"    # 0.5-0.8 - Suggest confirmation
    LOW = "LOW"          # < 0.5 - Require confirmation or reject


class NLPProvider(str, Enum):
    """Available NLP providers."""
    
    SPACY = "spacy"          # Local, fast, rule-based
    OPENAI = "openai"        # GPT-4 API
    DEEPSEEK = "deepseek"    # Deepseek API
    ANTHROPIC = "anthropic"  # Claude API
    OLLAMA = "ollama"        # Local LLMs
    HYBRID = "hybrid"        # Combination of providers


@dataclass
class EntityExtraction:
    """Represents an extracted entity from text."""
    
    entity_type: str     # e.g., "altitude", "distance", "direction"
    value: Any           # The extracted value
    raw_text: str        # Original text that was extracted
    confidence: float    # Confidence score for this extraction
    unit: Optional[str] = None  # Unit if applicable (meters, feet, etc.)
    
    def __post_init__(self):
        """Validate confidence score."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


@dataclass
class IntentClassification:
    """Result of intent classification."""
    
    intent: str                    # e.g., "TAKEOFF", "LAND", "MOVE"
    confidence: float              # Confidence score
    alternatives: List[Tuple[str, float]] = None  # Alternative intents with scores
    
    def __post_init__(self):
        """Initialize alternatives if not provided."""
        if self.alternatives is None:
            self.alternatives = []
            
    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        if self.confidence > 0.8:
            return ConfidenceLevel.HIGH
        elif self.confidence > 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


@dataclass
class ParseResult:
    """Complete result of NLP parsing."""
    
    # Original input
    original_text: str
    normalized_text: str
    
    # Classification results
    intent: IntentClassification
    entities: List[EntityExtraction]
    
    # Parsed command (if successful)
    command: Optional[DroneCommand] = None
    
    # Error information
    error: Optional[str] = None
    suggestions: List[str] = None
    
    # Metadata
    parse_time_ms: float = 0.0
    provider_used: str = "unknown"
    model_used: str = "unknown"
    
    # LLM-specific fields
    raw_llm_response: Optional[str] = None  # For debugging LLM outputs
    tokens_used: Optional[int] = None       # For cost tracking
    
    def __post_init__(self):
        """Initialize suggestions if not provided."""
        if self.suggestions is None:
            self.suggestions = []
    
    @property
    def success(self) -> bool:
        """Check if parsing was successful."""
        return self.command is not None and self.error is None
    
    @property
    def needs_confirmation(self) -> bool:
        """Check if result needs user confirmation."""
        return (
            self.intent.confidence_level == ConfidenceLevel.MEDIUM or
            any(e.confidence < 0.7 for e in self.entities)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "intent": {
                "type": self.intent.intent,
                "confidence": self.intent.confidence,
                "level": self.intent.confidence_level.value,
                "alternatives": self.intent.alternatives
            },
            "entities": [
                {
                    "type": e.entity_type,
                    "value": e.value,
                    "unit": e.unit,
                    "confidence": e.confidence,
                    "raw_text": e.raw_text
                }
                for e in self.entities
            ],
            "command": self.command.describe() if self.command else None,
            "success": self.success,
            "needs_confirmation": self.needs_confirmation,
            "error": self.error,
            "suggestions": self.suggestions,
            "metadata": {
                "parse_time_ms": self.parse_time_ms,
                "provider_used": self.provider_used,
                "model_used": self.model_used,
                "tokens_used": self.tokens_used
            }
        }


class NLPServicePort(ABC):
    """Port for Natural Language Processing services.
    
    This interface defines how the core domain interacts with NLP capabilities.
    Implementations can use spaCy, OpenAI, Deepseek, or any other NLP provider.
    """
    
    @abstractmethod
    async def parse_command(
        self, 
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        """Parse natural language text into a drone command.
        
        Args:
            text: The input text to parse
            context: Optional context (drone state, previous commands, etc.)
            
        Returns:
            ParseResult with the parsed command or error information
        """
        pass
    
    @abstractmethod
    async def get_suggestions(
        self,
        partial_text: str,
        limit: int = 5
    ) -> List[str]:
        """Get command suggestions for partial input (autocomplete).
        
        Args:
            partial_text: The partial text typed by user
            limit: Maximum number of suggestions to return
            
        Returns:
            List of suggested complete commands
        """
        pass
    
    @abstractmethod
    async def explain_command(
        self,
        command: DroneCommand
    ) -> str:
        """Explain what a command will do in natural language.
        
        Args:
            command: The drone command to explain
            
        Returns:
            Human-readable explanation of the command
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages.
        
        Returns:
            List of ISO 639-1 language codes (e.g., ['en', 'fa'])
        """
        pass
    
    @abstractmethod
    async def validate_feasibility(
        self,
        command: DroneCommand,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Check if a command is feasible given the current context.
        
        Args:
            command: The command to validate
            context: Current context (drone state, position, battery, etc.)
            
        Returns:
            Tuple of (is_feasible, reason_if_not_feasible)
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the name of the NLP provider."""
        pass
    
    @property
    @abstractmethod
    def requires_internet(self) -> bool:
        """Check if this provider requires internet connection."""
        pass