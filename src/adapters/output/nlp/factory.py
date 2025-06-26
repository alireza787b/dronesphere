# src/adapters/output/nlp/factory.py
"""Factory for creating NLP service instances.

This module provides a factory pattern for creating different NLP adapters
based on configuration. It supports spaCy, OpenAI, Deepseek, and other providers.
"""

from typing import Dict, Any, Optional

from src.core.ports.output.nlp_service import NLPServicePort, NLPProvider
from src.adapters.output.nlp.providers.spacy_adapter import SpacyNLPAdapter
# Future imports:
# from src.adapters.output.nlp.providers.openai_adapter import OpenAINLPAdapter
# from src.adapters.output.nlp.providers.deepseek_adapter import DeepseekNLPAdapter
# from src.adapters.output.nlp.providers.ollama_adapter import OllamaNLPAdapter
# from src.adapters.output.nlp.providers.hybrid_adapter import HybridNLPAdapter


class NLPServiceFactory:
    """Factory for creating NLP service instances based on configuration."""
    
    @staticmethod
    def create(
        provider: str,
        config: Optional[Dict[str, Any]] = None
    ) -> NLPServicePort:
        """Create an NLP service instance.
        
        Args:
            provider: The provider to use (spacy, openai, deepseek, etc.)
            config: Provider-specific configuration
            
        Returns:
            NLPServicePort implementation
            
        Raises:
            ValueError: If provider is not supported
        """
        config = config or {}
        
        if provider == NLPProvider.SPACY:
            model_name = config.get("model_name", "en_core_web_sm")
            return SpacyNLPAdapter(model_name=model_name)
        
        # elif provider == NLPProvider.OPENAI:
        #     api_key = config.get("api_key")
        #     if not api_key:
        #         raise ValueError("OpenAI provider requires 'api_key' in config")
        #     model = config.get("model", "gpt-4")
        #     return OpenAINLPAdapter(api_key=api_key, model=model)
        
        # elif provider == NLPProvider.DEEPSEEK:
        #     api_key = config.get("api_key")
        #     if not api_key:
        #         raise ValueError("Deepseek provider requires 'api_key' in config")
        #     model = config.get("model", "deepseek-coder")
        #     return DeepseekNLPAdapter(api_key=api_key, model=model)
        
        # elif provider == NLPProvider.OLLAMA:
        #     base_url = config.get("base_url", "http://localhost:11434")
        #     model = config.get("model", "llama2")
        #     return OllamaNLPAdapter(base_url=base_url, model=model)
        
        # elif provider == NLPProvider.HYBRID:
        #     # Hybrid uses spaCy first, then falls back to LLM
        #     primary_provider = config.get("primary_provider", NLPProvider.SPACY)
        #     fallback_provider = config.get("fallback_provider", NLPProvider.OPENAI)
        #     
        #     primary = NLPServiceFactory.create(primary_provider, config.get("primary_config", {}))
        #     fallback = NLPServiceFactory.create(fallback_provider, config.get("fallback_config", {}))
        #     
        #     confidence_threshold = config.get("confidence_threshold", 0.5)
        #     return HybridNLPAdapter(
        #         primary=primary,
        #         fallback=fallback,
        #         confidence_threshold=confidence_threshold
        #     )
        
        else:
            raise ValueError(
                f"Unsupported NLP provider: {provider}. "
                f"Supported providers: {', '.join([p.value for p in NLPProvider])}"
            )
    
    @staticmethod
    def create_from_env(env_config: Dict[str, Any]) -> NLPServicePort:
        """Create NLP service from environment configuration.
        
        Args:
            env_config: Environment configuration dictionary
            
        Returns:
            NLPServicePort implementation
        """
        provider = env_config.get("NLP_PROVIDER", NLPProvider.SPACY)
        
        # Build provider-specific config from environment
        config = {}
        
        if provider == NLPProvider.SPACY:
            config["model_name"] = env_config.get("SPACY_MODEL", "en_core_web_sm")
        
        elif provider == NLPProvider.OPENAI:
            config["api_key"] = env_config.get("OPENAI_API_KEY")
            config["model"] = env_config.get("OPENAI_MODEL", "gpt-4")
        
        elif provider == NLPProvider.DEEPSEEK:
            config["api_key"] = env_config.get("DEEPSEEK_API_KEY")
            config["model"] = env_config.get("DEEPSEEK_MODEL", "deepseek-coder")
        
        elif provider == NLPProvider.OLLAMA:
            config["base_url"] = env_config.get("OLLAMA_BASE_URL", "http://localhost:11434")
            config["model"] = env_config.get("OLLAMA_MODEL", "llama2")
        
        elif provider == NLPProvider.HYBRID:
            config["primary_provider"] = env_config.get("NLP_PRIMARY_PROVIDER", NLPProvider.SPACY)
            config["fallback_provider"] = env_config.get("NLP_FALLBACK_PROVIDER", NLPProvider.OPENAI)
            config["confidence_threshold"] = float(env_config.get("NLP_CONFIDENCE_THRESHOLD", "0.5"))
            
            # Primary provider config
            if config["primary_provider"] == NLPProvider.SPACY:
                config["primary_config"] = {
                    "model_name": env_config.get("SPACY_MODEL", "en_core_web_sm")
                }
            
            # Fallback provider config
            if config["fallback_provider"] == NLPProvider.OPENAI:
                config["fallback_config"] = {
                    "api_key": env_config.get("OPENAI_API_KEY"),
                    "model": env_config.get("OPENAI_MODEL", "gpt-4")
                }
        
        return NLPServiceFactory.create(provider, config)