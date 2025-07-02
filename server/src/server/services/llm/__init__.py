# server/src/server/services/llm/__init__.py
"""
LLM service package.

This package provides LLM integration for natural language command extraction
and conversation management.
"""

from .base import (
    BaseLLMProvider,
    ClarificationRequest,
    ClarificationResponse,
    CommandExtractionResult,
    ConversationContext,
)
from .config import (
    AnthropicConfig,
    BaseLLMConfig,
    DeepSeekConfig,
    LLMConfigFactory,
    LLMProvider,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
    load_llm_config_from_env,
)
from .factory import (
    LLMProviderFactory,
    get_llm_provider,
    get_llm_provider_sync,
)



__all__ = [
    # Base classes
    "BaseLLMProvider",
    "ClarificationRequest",
    "ClarificationResponse",
    "CommandExtractionResult",
    "ConversationContext",
    # Config classes
    "BaseLLMConfig",
    "LLMProvider",
    "OpenRouterConfig",
    "OpenAIConfig",
    "OllamaConfig",
    "AnthropicConfig",
    "DeepSeekConfig",
    "LLMConfigFactory",
    "load_llm_config_from_env",
    # Factory
    "LLMProviderFactory",
    "get_llm_provider",
    "get_llm_provider_sync",
]