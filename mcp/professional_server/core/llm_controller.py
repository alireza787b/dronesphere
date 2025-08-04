"""
Multi-LLM Controller for DroneSphere Professional MCP Server
Supports OpenRouter, OpenAI, and Ollama with automatic fallback
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import httpx
import yaml
from dotenv import load_dotenv
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """Configuration for an LLM provider."""
    provider: LLMProvider
    base_url: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 1200
    timeout: int = 30
    api_key: Optional[str] = None


class LLMResponse(BaseModel):
    """Standardized LLM response."""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    response_time: float
    success: bool
    error: Optional[str] = None


class MultiLLMController:
    """Multi-LLM controller with automatic fallback support."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize multi-LLM controller."""
        self.config = self._load_config(config_path)
        self.providers = self._setup_providers()
        self.fallback_chain = [LLMProvider.OPENROUTER, LLMProvider.OPENAI, LLMProvider.OLLAMA]
        self.retry_attempts = self.config.get("llm", {}).get("retry_attempts", 2)
        
        logger.info(f"Multi-LLM Controller initialized with {len(self.providers)} providers")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "llm": {
                "primary": {
                    "provider": "openrouter",
                    "base_url": "https://openrouter.ai/api/v1",
                    "model": "anthropic/claude-3-sonnet",
                    "temperature": 0.1,
                    "max_tokens": 1200,
                    "timeout": 30
                },
                "secondary": {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                    "temperature": 0.1,
                    "max_tokens": 1200,
                    "timeout": 30
                },
                "local": {
                    "provider": "ollama",
                    "base_url": "http://localhost:11434",
                    "model": "llama3.1:8b",
                    "temperature": 0.1,
                    "max_tokens": 1200,
                    "timeout": 60
                },
                "fallback_enabled": True,
                "retry_attempts": 2
            }
        }

    def _setup_providers(self) -> Dict[LLMProvider, LLMConfig]:
        """Setup LLM providers with API keys."""
        providers = {}
        llm_config = self.config.get("llm", {})

        # OpenRouter (Primary)
        if "primary" in llm_config:
            openrouter_config = llm_config["primary"].copy()
            openrouter_config["api_key"] = os.getenv("OPENROUTER_API_KEY")
            providers[LLMProvider.OPENROUTER] = LLMConfig(
                **openrouter_config
            )

        # OpenAI (Secondary)
        if "secondary" in llm_config:
            openai_config = llm_config["secondary"].copy()
            openai_config["api_key"] = os.getenv("OPENAI_API_KEY")
            providers[LLMProvider.OPENAI] = LLMConfig(
                **openai_config
            )

        # Ollama (Local) - Only if enabled
        if "local" in llm_config:
            ollama_config = llm_config["local"].copy()
            if ollama_config.get("enabled", True):  # Check if enabled
                providers[LLMProvider.OLLAMA] = LLMConfig(
                    **ollama_config
                )

        return providers

    async def process_with_fallback(
        self, 
        messages: List[Dict[str, str]], 
        preferred_provider: Optional[LLMProvider] = None
    ) -> LLMResponse:
        """Process request with automatic fallback through providers."""
        
        # Determine provider order
        if preferred_provider and preferred_provider in self.providers:
            provider_order = [preferred_provider] + [p for p in self.fallback_chain if p != preferred_provider]
        else:
            provider_order = self.fallback_chain

        last_error = None
        
        for provider in provider_order:
            if provider not in self.providers:
                continue
                
            config = self.providers[provider]
            
            # Check if provider is available
            if not self._is_provider_available(config):
                logger.warning(f"Provider {provider} not available, skipping")
                continue

            # Try to process with this provider
            for attempt in range(self.retry_attempts + 1):
                try:
                    logger.info(f"Attempting with {provider} (attempt {attempt + 1})")
                    response = await self._process_with_provider(config, messages)
                    
                    if response.success:
                        logger.info(f"Success with {provider} in {response.response_time:.2f}s")
                        return response
                        
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Provider {provider} failed (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.retry_attempts:
                        await asyncio.sleep(1)  # Brief delay before retry
                    continue

        # All providers failed
        logger.error(f"All providers failed. Last error: {last_error}")
        return LLMResponse(
            content="",
            provider=LLMProvider.OPENROUTER,  # Default
            model="unknown",
            response_time=0.0,
            success=False,
            error=f"All LLM providers failed: {last_error}"
        )

    def _is_provider_available(self, config: LLMConfig) -> bool:
        """Check if provider is available and configured."""
        if config.provider in [LLMProvider.OPENROUTER, LLMProvider.OPENAI]:
            return bool(config.api_key)
        elif config.provider == LLMProvider.OLLAMA:
            # For Ollama, we'll check availability during request
            return True
        return False

    async def _process_with_provider(self, config: LLMConfig, messages: List[Dict[str, str]]) -> LLMResponse:
        """Process request with specific provider."""
        import time
        start_time = time.time()

        try:
            if config.provider in [LLMProvider.OPENROUTER, LLMProvider.OPENAI]:
                return await self._process_openai_compatible(config, messages)
            elif config.provider == LLMProvider.OLLAMA:
                return await self._process_ollama(config, messages)
            else:
                raise ValueError(f"Unsupported provider: {config.provider}")

        except Exception as e:
            response_time = time.time() - start_time
            return LLMResponse(
                content="",
                provider=config.provider,
                model=config.model,
                response_time=response_time,
                success=False,
                error=str(e)
            )

    async def _process_openai_compatible(self, config: LLMConfig, messages: List[Dict[str, str]]) -> LLMResponse:
        """Process with OpenAI-compatible API (OpenRouter, OpenAI)."""
        import time
        start_time = time.time()

        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url
        )

        response = await client.chat.completions.create(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout=config.timeout
        )

        response_time = time.time() - start_time
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=config.provider,
            model=config.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
            response_time=response_time,
            success=True
        )

    async def _process_ollama(self, config: LLMConfig, messages: List[Dict[str, str]]) -> LLMResponse:
        """Process with Ollama local API."""
        import time
        start_time = time.time()

        # Convert messages to Ollama format
        prompt = self._convert_messages_to_prompt(messages)
        
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            response = await client.post(
                f"{config.base_url}/api/generate",
                json={
                    "model": config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": config.temperature,
                        "num_predict": config.max_tokens
                    }
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code}")

            result = response.json()
            response_time = time.time() - start_time
            
            return LLMResponse(
                content=result.get("response", ""),
                provider=config.provider,
                model=config.model,
                response_time=response_time,
                success=True
            )

    def _convert_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI format messages to Ollama prompt format."""
        prompt_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n".join(prompt_parts) + "\nAssistant:"

    async def test_providers(self) -> Dict[str, Any]:
        """Test all available providers."""
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from DroneSphere MCP'"}
        ]
        
        results = {}
        
        for provider in self.providers:
            config = self.providers[provider]
            if self._is_provider_available(config):
                try:
                    response = await self._process_with_provider(config, test_messages)
                    results[provider.value] = {
                        "available": True,
                        "response_time": response.response_time,
                        "success": response.success,
                        "error": response.error
                    }
                except Exception as e:
                    results[provider.value] = {
                        "available": False,
                        "error": str(e)
                    }
            else:
                results[provider.value] = {
                    "available": False,
                    "error": "Not configured"
                }
        
        return results

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        status = {}
        
        for provider, config in self.providers.items():
            status[provider.value] = {
                "configured": self._is_provider_available(config),
                "model": config.model,
                "base_url": config.base_url,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens
            }
        
        return status 