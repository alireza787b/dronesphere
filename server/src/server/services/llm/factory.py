
# server/src/server/services/llm/factory.py
"""
Factory pattern for creating LLM provider instances.

This module provides a factory for creating different LLM provider instances
based on configuration, with support for fallback providers and health checks.
"""

from typing import Any, Dict, Optional, Type

import structlog

from .base import BaseLLMProvider
from .config import (
    AnthropicConfig,
    BaseLLMConfig,
    DeepSeekConfig,
    LLMConfigFactory,
    LLMProvider,
    OllamaConfig,
    OpenAIConfig,
    OpenRouterConfig,
)

logger = structlog.get_logger()


class LLMProviderFactory:
    """
    Factory for creating LLM provider instances.
    
    This factory supports:
    - Multiple LLM providers (OpenRouter, OpenAI, Ollama, etc.)
    - Lazy loading of provider implementations
    - Fallback provider support
    - Health check before returning provider
    """
    
    _providers: Dict[LLMProvider, Type[BaseLLMProvider]] = {}
    _instances: Dict[str, BaseLLMProvider] = {}
    
    @classmethod
    def register_provider(
        cls,
        provider_type: LLMProvider,
        provider_class: Type[BaseLLMProvider]
    ) -> None:
        """
        Register a provider implementation.
        
        Args:
            provider_type: Provider type enum
            provider_class: Provider implementation class
        """
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered LLM provider", provider=provider_type.value)
    
    @classmethod
    def create_provider(
        cls,
        config: BaseLLMConfig,
        fallback_config: Optional[BaseLLMConfig] = None
    ) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            config: Primary provider configuration
            fallback_config: Optional fallback provider configuration
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If provider type is not registered
            RuntimeError: If provider creation fails
        """
        # Check if we already have an instance
        instance_key = f"{config.provider}:{config.model}"
        if instance_key in cls._instances:
            logger.info("Returning cached provider instance", key=instance_key)
            return cls._instances[instance_key]
        
        # Load provider implementation lazily
        if config.provider not in cls._providers:
            cls._load_provider_implementation(config.provider)
        
        if config.provider not in cls._providers:
            raise ValueError(
                f"Provider {config.provider} not registered. "
                f"Available providers: {list(cls._providers.keys())}"
            )
        
        try:
            # Create provider instance
            provider_class = cls._providers[config.provider]
            provider = provider_class(config)
            
            # Cache the instance
            cls._instances[instance_key] = provider
            
            logger.info(
                "Created LLM provider",
                provider=config.provider,
                model=config.model,
            )
            
            return provider
            
        except Exception as e:
            logger.error(
                "Failed to create primary provider",
                provider=config.provider,
                error=str(e),
            )
            
            # Try fallback provider if available
            if fallback_config:
                logger.info("Attempting to use fallback provider")
                return cls.create_provider(fallback_config)
            
            raise RuntimeError(f"Failed to create LLM provider: {str(e)}")
    
    @classmethod
    def create_from_settings(
        cls,
        settings: Any,
        fallback_provider: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Create provider from server settings.
        
        Args:
            settings: Server settings object
            fallback_provider: Optional fallback provider name
            
        Returns:
            LLM provider instance
        """
        # Create primary config from settings
        primary_config = cls._config_from_settings(settings, settings.llm_provider)
        
        # Create fallback config if specified
        fallback_config = None
        if fallback_provider:
            fallback_config = cls._config_from_settings(settings, fallback_provider)
        
        return cls.create_provider(primary_config, fallback_config)
    
    @classmethod
    async def create_with_health_check(
        cls,
        config: BaseLLMConfig,
        fallback_config: Optional[BaseLLMConfig] = None
    ) -> BaseLLMProvider:
        """
        Create provider and verify it's healthy.
        
        Args:
            config: Primary provider configuration
            fallback_config: Optional fallback provider configuration
            
        Returns:
            Healthy LLM provider instance
            
        Raises:
            RuntimeError: If no healthy provider can be created
        """
        # Try primary provider
        try:
            provider = cls.create_provider(config)
            is_healthy, status = await provider.check_health()
            
            if is_healthy:
                logger.info("Primary provider is healthy", status=status)
                return provider
            else:
                logger.warning("Primary provider is unhealthy", status=status)
                
        except Exception as e:
            logger.error("Primary provider health check failed", error=str(e))
        
        # Try fallback if primary is unhealthy
        if fallback_config:
            logger.info("Trying fallback provider")
            try:
                provider = cls.create_provider(fallback_config)
                is_healthy, status = await provider.check_health()
                
                if is_healthy:
                    logger.info("Fallback provider is healthy", status=status)
                    return provider
                else:
                    logger.error("Fallback provider is also unhealthy", status=status)
                    
            except Exception as e:
                logger.error("Fallback provider health check failed", error=str(e))
        
        raise RuntimeError("No healthy LLM provider available")
    
    @classmethod
    def _load_provider_implementation(cls, provider_type: LLMProvider) -> None:
        """
        Lazily load provider implementation.
        
        Args:
            provider_type: Provider type to load
        """
        try:
            if provider_type == LLMProvider.OPENROUTER:
                from .providers.openrouter import OpenRouterProvider
                cls.register_provider(LLMProvider.OPENROUTER, OpenRouterProvider)

            elif provider_type == LLMProvider.OLLAMA:
                from .providers.ollama import OllamaProvider
                cls.register_provider(LLMProvider.OLLAMA, OllamaProvider)
                
            elif provider_type == LLMProvider.OPENAI:
                # TODO: Implement OpenAI provider
                logger.warning("OpenAI provider not yet implemented")
                
            elif provider_type == LLMProvider.OLLAMA:
                # TODO: Implement Ollama provider
                logger.warning("Ollama provider not yet implemented")
                
            elif provider_type == LLMProvider.ANTHROPIC:
                # TODO: Implement Anthropic provider
                logger.warning("Anthropic provider not yet implemented")
                
            elif provider_type == LLMProvider.DEEPSEEK:
                # TODO: Implement DeepSeek provider
                logger.warning("DeepSeek provider not yet implemented")
                
        except ImportError as e:
            logger.error(
                f"Failed to import provider implementation",
                provider=provider_type,
                error=str(e),
            )
    
    @classmethod
    def _config_from_settings(cls, settings: Any, provider_name: str) -> BaseLLMConfig:
        """
        Create provider config from settings.
        
        Args:
            settings: Server settings
            provider_name: Provider name
            
        Returns:
            Provider configuration
        """
        provider_lower = provider_name.lower()
        
        if provider_lower == "openrouter":
            return OpenRouterConfig(
                api_key=getattr(settings, "openrouter_api_key", None) or
                        getattr(settings, "openai_api_key", "dummy-key-for-free-model"),
                base_url=getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1"),
                model=getattr(settings, "openrouter_model", "google/gemma-2-9b-it:free"),
                temperature=getattr(settings, "openrouter_temperature", 0.3),
                max_tokens=getattr(settings, "openrouter_max_tokens", 1000),
            )
        elif provider_lower == "openai":
            return OpenAIConfig(
                api_key=getattr(settings, "openai_api_key", ""),
                model=getattr(settings, "openai_model", "gpt-4-turbo-preview"),
            )
        elif provider_lower == "ollama":
            return OllamaConfig(
                base_url=getattr(settings, "ollama_host", "http://localhost:11434"),
                model=getattr(settings, "ollama_model", "llama2"),
            )
        elif provider_lower == "anthropic":
            return AnthropicConfig(
                api_key=getattr(settings, "anthropic_api_key", ""),
                model=getattr(settings, "anthropic_model", "claude-3-opus-20240229"),
            )
        elif provider_lower == "deepseek":
            return DeepSeekConfig(
                api_key=getattr(settings, "deepseek_api_key", ""),
                base_url=getattr(settings, "deepseek_api_base", "https://api.deepseek.com/v1"),
                model=getattr(settings, "deepseek_model", "deepseek-chat"),
            )
        else:
            # Default to OpenRouter free model
            return OpenRouterConfig(
                api_key="dummy-key-for-free-model",
                model="google/gemma-2-9b-it:free",
            )
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached provider instances."""
        cls._instances.clear()
        logger.info("Cleared LLM provider cache")


# Convenience functions
async def get_llm_provider(settings: Any) -> BaseLLMProvider:
    """
    Get LLM provider instance from settings.
    
    Args:
        settings: Server settings
        
    Returns:
        LLM provider instance
    """
    return await LLMProviderFactory.create_with_health_check(
        LLMProviderFactory._config_from_settings(settings, settings.llm_provider),
        LLMProviderFactory._config_from_settings(settings, "ollama")  # Fallback to Ollama
        if hasattr(settings, "llm_fallback_provider") and settings.llm_fallback_provider
        else None
    )


def get_llm_provider_sync(settings: Any) -> BaseLLMProvider:
    """
    Get LLM provider instance synchronously (without health check).
    
    Args:
        settings: Server settings
        
    Returns:
        LLM provider instance
    """
    return LLMProviderFactory.create_from_settings(settings)

