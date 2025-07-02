# server/src/server/services/llm/config.py
"""
Configuration models for LLM providers.

This module contains Pydantic models for configuring different LLM providers
with proper validation and defaults.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


class BaseLLMConfig(BaseModel):
    """Base configuration for all LLM providers."""

    provider: LLMProvider
    model: str
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)
    timeout: int = Field(default=30, ge=1)
    retry_attempts: int = Field(default=3, ge=0)
    retry_delay: float = Field(default=1.0, ge=0.0)

    # Command extraction specific settings
    command_extraction_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    command_extraction_max_tokens: int = Field(default=500, ge=1)

    # Conversation settings
    conversation_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    conversation_max_tokens: int = Field(default=1000, ge=1)

    class Config:
        """Pydantic config."""

        use_enum_values = True


class OpenRouterConfig(BaseLLMConfig):
    """Configuration for OpenRouter provider."""

    provider: LLMProvider = LLMProvider.OPENROUTER
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemma-2-9b-it:free"

    # OpenRouter specific settings
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    repetition_penalty: float = Field(default=1.0, ge=0.0, le=2.0)

    # Optional OpenRouter features
    transforms: Optional[list] = None
    route: Optional[str] = None

    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or not v.startswith("sk-"):
            raise ValueError(
                "Valid OpenRouter API key required (should start with 'sk-')"
            )
        return v


class OpenAIConfig(BaseLLMConfig):
    """Configuration for OpenAI provider."""

    provider: LLMProvider = LLMProvider.OPENAI
    api_key: str
    base_url: Optional[str] = None
    model: str = "gpt-4-turbo-preview"
    organization: Optional[str] = None

    # OpenAI specific settings
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = None

    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or not v.startswith("sk-"):
            raise ValueError("Valid OpenAI API key required (should start with 'sk-')")
        return v


class OllamaConfig(BaseLLMConfig):
    """Configuration for Ollama provider."""

    provider: LLMProvider = LLMProvider.OLLAMA
    base_url: str = "http://localhost:11434"
    model: str = "llama2"

    # Ollama specific settings
    num_predict: Optional[int] = None
    top_k: Optional[int] = None
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    repeat_last_n: Optional[int] = None
    repeat_penalty: float = Field(default=1.0, ge=0.0)

    # Ollama options
    num_ctx: int = Field(default=2048, ge=128)
    num_batch: int = Field(default=512, ge=1)
    num_gpu: int = Field(default=1, ge=0)
    main_gpu: int = Field(default=0, ge=0)
    low_vram: bool = False
    vocab_only: bool = False
    use_mmap: bool = True
    use_mlock: bool = False

    @validator("base_url")
    def validate_base_url(cls, v):
        """Ensure base URL doesn't end with slash."""
        return v.rstrip("/")

    @validator("model")
    def validate_model(cls, v):
        """Validate model name format."""
        if not v:
            raise ValueError("Model name cannot be empty")
        # Common Ollama model format validation
        if ":" not in v and v not in [
            "llama2",
            "mistral",
            "phi",
            "neural-chat",
            "codellama",
        ]:
            # Add :latest tag if no tag specified for consistency
            return f"{v}:latest"
        return v


class AnthropicConfig(BaseLLMConfig):
    """Configuration for Anthropic provider."""

    provider: LLMProvider = LLMProvider.ANTHROPIC
    api_key: str
    base_url: Optional[str] = None
    model: str = "claude-3-opus-20240229"

    # Anthropic specific settings
    top_k: Optional[int] = None
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)

    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or not v.startswith("sk-ant-"):
            raise ValueError(
                "Valid Anthropic API key required (should start with 'sk-ant-')"
            )
        return v


class DeepSeekConfig(BaseLLMConfig):
    """Configuration for DeepSeek provider."""

    provider: LLMProvider = LLMProvider.DEEPSEEK
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"

    # DeepSeek specific settings
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)

    @validator("api_key")
    def validate_api_key(cls, v):
        """Validate API key is not empty."""
        if not v or v == "your-key-here":
            raise ValueError("Valid DeepSeek API key required")
        return v


class LLMConfigFactory:
    """Factory for creating LLM configurations."""

    _config_map = {
        LLMProvider.OPENROUTER: OpenRouterConfig,
        LLMProvider.OPENAI: OpenAIConfig,
        LLMProvider.OLLAMA: OllamaConfig,
        LLMProvider.ANTHROPIC: AnthropicConfig,
        LLMProvider.DEEPSEEK: DeepSeekConfig,
    }

    @classmethod
    def create_config(cls, provider: str, **kwargs) -> BaseLLMConfig:
        """
        Create configuration for specified provider.

        Args:
            provider: Provider name
            **kwargs: Provider-specific configuration

        Returns:
            Provider configuration instance

        Raises:
            ValueError: If provider is not supported
        """
        try:
            provider_enum = LLMProvider(provider.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported providers: {', '.join([p.value for p in LLMProvider])}"
            )

        config_class = cls._config_map[provider_enum]
        return config_class(provider=provider_enum, **kwargs)


def load_llm_config_from_env(settings: Any) -> BaseLLMConfig:
    """
    Load LLM configuration from environment settings.

    Args:
        settings: Server settings instance

    Returns:
        LLM configuration instance
    """
    provider = settings.llm_provider.lower()

    if provider == LLMProvider.OPENROUTER:
        return OpenRouterConfig(
            api_key=settings.openrouter_api_key
            or settings.openai_api_key
            or "dummy-key-for-free-model",
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            temperature=settings.openrouter_temperature,
            max_tokens=settings.openrouter_max_tokens,
        )
    elif provider == LLMProvider.OPENAI:
        return OpenAIConfig(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model or "gpt-4-turbo-preview",
        )
    elif provider == LLMProvider.OLLAMA:
        return OllamaConfig(
            base_url=settings.ollama_host,
            model=settings.ollama_model or "llama2",
            temperature=getattr(settings, "ollama_temperature", 0.3),
            max_tokens=getattr(settings, "ollama_max_tokens", 1000),
            timeout=getattr(settings, "ollama_timeout", 60),
            num_ctx=getattr(settings, "ollama_num_ctx", 4096),
            num_gpu=getattr(settings, "ollama_num_gpu", 1),
        )
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicConfig(
            api_key=settings.anthropic_api_key or "",
            model=settings.anthropic_model or "claude-3-opus-20240229",
        )
    elif provider == LLMProvider.DEEPSEEK:
        return DeepSeekConfig(
            api_key=settings.deepseek_api_key or "",
            base_url=settings.deepseek_api_base,
            model=settings.deepseek_model or "deepseek-chat",
        )
    else:
        # Default to OpenRouter with free model
        return OpenRouterConfig(
            api_key="dummy-key-for-free-model",
            model="google/gemma-2-9b-it:free",
        )
