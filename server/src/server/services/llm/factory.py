# server/src/server/services/llm/factory.py
"""
LLM Service Factory

Creates appropriate LLM service based on configuration.
"""

from typing import Dict, Any, Optional

import structlog

from server.core.config import get_settings
from .base import BaseLLMService, LLMProvider
from .openrouter import OpenRouterService

logger = structlog.get_logger()


class LLMServiceFactory:
    """
    Factory for creating LLM service instances.
    
    Supports multiple providers and handles configuration.
    """
    
    # Registry of available providers
    _providers = {
        LLMProvider.OPENROUTER: OpenRouterService,
        # Future providers will be added here:
        # LLMProvider.OLLAMA: OllamaService,
        # LLMProvider.OPENAI: OpenAIService,
        # LLMProvider.ANTHROPIC: AnthropicService,
        # LLMProvider.DEEPSEEK: DeepSeekService,
    }
    
    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> BaseLLMService:
        """
        Create LLM service instance.
        
        Args:
            provider: Provider name (defaults to config)
            config_override: Override default configuration
            
        Returns:
            Configured LLM service instance
            
        Raises:
            ValueError: If provider not supported
        """
        settings = get_settings()
        
        # Determine provider
        provider_name = provider or settings.llm_provider
        
        try:
            provider_enum = LLMProvider(provider_name.lower())
        except ValueError:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
            
        # Get provider class
        provider_class = cls._providers.get(provider_enum)
        if not provider_class:
            raise ValueError(f"Provider {provider_name} not implemented yet")
            
        # Build configuration
        config = cls._build_config(provider_enum, settings, config_override)
        
        # Create instance
        logger.info(f"Creating LLM service", provider=provider_name)
        return provider_class(config)
        
    @classmethod
    def _build_config(
        cls,
        provider: LLMProvider,
        settings,
        override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build provider-specific configuration.
        
        Args:
            provider: Provider enum
            settings: Application settings
            override: Configuration override
            
        Returns:
            Provider configuration dict
        """
        base_config = {
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
            "timeout": settings.llm_timeout,
        }
        
        # Provider-specific configuration
        if provider == LLMProvider.OPENROUTER:
            base_config.update({
                "api_key": settings.openrouter_api_key,
                "base_url": settings.openrouter_base_url,
                "model": settings.openrouter_model,
                "site_url": settings.openrouter_site_url,
                "app_name": settings.openrouter_app_name,
            })
        elif provider == LLMProvider.OLLAMA:
            base_config.update({
                "host": settings.ollama_host,
                "model": settings.ollama_model,
            })
        elif provider == LLMProvider.OPENAI:
            base_config.update({
                "api_key": settings.openai_api_key,
                "model": settings.openai_model,
            })
        elif provider == LLMProvider.ANTHROPIC:
            base_config.update({
                "api_key": settings.anthropic_api_key,
                "model": settings.anthropic_model,
            })
        elif provider == LLMProvider.DEEPSEEK:
            base_config.update({
                "api_key": settings.deepseek_api_key,
                "base_url": settings.deepseek_api_base,
                "model": settings.deepseek_model,
            })
            
        # Apply overrides
        if override:
            base_config.update(override)
            
        return base_config
        
    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List available providers.
        
        Returns:
            List of provider names
        """
        return [p.value for p in cls._providers.keys()]