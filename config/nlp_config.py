# config/nlp_config.py
"""Configuration for NLP services.

This module defines configuration settings for different NLP providers
and their specific parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from src.core.ports.output.nlp_service import NLPProvider


@dataclass
class NLPConfig:
    """Configuration for NLP services."""
    
    # Provider selection
    provider: NLPProvider = NLPProvider.SPACY
    
    # General settings
    confidence_threshold: float = 0.7
    require_confirmation: bool = True
    default_language: str = "en"
    
    # spaCy settings
    spacy_model: str = "en_core_web_sm"
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_temperature: float = 0.3
    openai_max_tokens: int = 500
    
    # Deepseek settings
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-coder"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    
    # Ollama settings (for local LLMs)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # Hybrid settings
    hybrid_primary_provider: NLPProvider = NLPProvider.SPACY
    hybrid_fallback_provider: NLPProvider = NLPProvider.OPENAI
    hybrid_confidence_threshold: float = 0.5
    
    @classmethod
    def from_env(cls, env_dict: Dict[str, Any]) -> "NLPConfig":
        """Create config from environment variables."""
        return cls(
            provider=NLPProvider(env_dict.get("NLP_PROVIDER", "spacy")),
            confidence_threshold=float(env_dict.get("NLP_CONFIDENCE_THRESHOLD", "0.7")),
            require_confirmation=env_dict.get("NLP_REQUIRE_CONFIRMATION", "true").lower() == "true",
            default_language=env_dict.get("NLP_DEFAULT_LANGUAGE", "en"),
            
            # spaCy
            spacy_model=env_dict.get("SPACY_MODEL", "en_core_web_sm"),
            
            # OpenAI
            openai_api_key=env_dict.get("OPENAI_API_KEY"),
            openai_model=env_dict.get("OPENAI_MODEL", "gpt-4"),
            openai_temperature=float(env_dict.get("OPENAI_TEMPERATURE", "0.3")),
            openai_max_tokens=int(env_dict.get("OPENAI_MAX_TOKENS", "500")),
            
            # Deepseek
            deepseek_api_key=env_dict.get("DEEPSEEK_API_KEY"),
            deepseek_model=env_dict.get("DEEPSEEK_MODEL", "deepseek-coder"),
            deepseek_base_url=env_dict.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            
            # Ollama
            ollama_base_url=env_dict.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=env_dict.get("OLLAMA_MODEL", "llama2"),
            
            # Hybrid
            hybrid_primary_provider=NLPProvider(env_dict.get("NLP_PRIMARY_PROVIDER", "spacy")),
            hybrid_fallback_provider=NLPProvider(env_dict.get("NLP_FALLBACK_PROVIDER", "openai")),
            hybrid_confidence_threshold=float(env_dict.get("NLP_HYBRID_THRESHOLD", "0.5")),
        )
    
    def to_factory_config(self) -> Dict[str, Any]:
        """Convert to factory configuration format."""
        if self.provider == NLPProvider.SPACY:
            return {"model_name": self.spacy_model}
        
        elif self.provider == NLPProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "temperature": self.openai_temperature,
                "max_tokens": self.openai_max_tokens,
            }
        
        elif self.provider == NLPProvider.DEEPSEEK:
            return {
                "api_key": self.deepseek_api_key,
                "model": self.deepseek_model,
                "base_url": self.deepseek_base_url,
            }
        
        elif self.provider == NLPProvider.OLLAMA:
            return {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
            }
        
        elif self.provider == NLPProvider.HYBRID:
            return {
                "primary_provider": self.hybrid_primary_provider,
                "fallback_provider": self.hybrid_fallback_provider,
                "confidence_threshold": self.hybrid_confidence_threshold,
                "primary_config": NLPConfig(provider=self.hybrid_primary_provider).to_factory_config(),
                "fallback_config": NLPConfig(provider=self.hybrid_fallback_provider).to_factory_config(),
            }
        
        return {}