# server/src/server/services/llm/openrouter.py
"""
OpenRouter LLM Service Implementation

Provides access to multiple LLM models through OpenRouter's unified API.
"""

from typing import List, Dict, Any, Optional
import httpx
from openai import AsyncOpenAI

import structlog

from .base import BaseLLMService, LLMMessage, LLMResponse

logger = structlog.get_logger()


class OpenRouterService(BaseLLMService):
    """
    OpenRouter LLM service implementation.
    
    Uses OpenRouter's unified API to access multiple LLM providers
    including free models like Google Gemma.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenRouter service.
        
        Args:
            config: Configuration with api_key, base_url, model, etc.
        """
        super().__init__(config)
        
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://openrouter.ai/api/v1")
        self.model = config.get("model", "google/gemma-2-9b-it:free")
        self.site_url = config.get("site_url", "https://dronesphere.ai")
        self.app_name = config.get("app_name", "DroneSphere Control System")
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
            
        # Initialize OpenAI-compatible client
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )
        
        logger.info(
            "OpenRouter service initialized",
            model=self.model,
            base_url=self.base_url
        )
        
    def _get_provider_name(self) -> str:
        """Get the provider name."""
        return "openrouter"
        
    async def complete(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Get completion from OpenRouter.
        
        Args:
            messages: List of messages in conversation
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with generated content
        """
        try:
            # Convert to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": openai_messages,
                "temperature": temperature or self.config.get("temperature", 0.7),
                "max_tokens": max_tokens or self.config.get("max_tokens", 2000),
            }
            
            # Add any additional parameters
            request_params.update(kwargs)
            
            logger.debug(
                "Sending request to OpenRouter",
                model=self.model,
                num_messages=len(messages),
                temperature=request_params["temperature"]
            )
            
            # Make request with custom headers
            response = await self.client.chat.completions.create(
                **request_params,
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                }
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Build response
            llm_response = LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "openrouter_id": getattr(response, 'id', None),
                }
            )
            
            logger.info(
                "OpenRouter completion successful",
                model=response.model,
                tokens=llm_response.usage.get("total_tokens", 0)
            )
            
            return llm_response
            
        except Exception as e:
            logger.error(
                "OpenRouter completion failed",
                error=str(e),
                model=self.model
            )
            raise
            
    async def is_available(self) -> bool:
        """
        Check if OpenRouter service is available.
        
        Returns:
            True if service is reachable and configured
        """
        try:
            # Try a simple completion
            test_messages = [
                LLMMessage(role="user", content="Say 'ok' if you can hear me.")
            ]
            
            response = await self.complete(
                messages=test_messages,
                max_tokens=10,
                temperature=0
            )
            
            return bool(response.content)
            
        except Exception as e:
            logger.warning(
                "OpenRouter availability check failed",
                error=str(e)
            )
            return False
            
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from OpenRouter.
        
        Returns:
            List of available models with metadata
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": self.site_url,
                        "X-Title": self.app_name,
                    }
                )
                response.raise_for_status()
                
                models = response.json().get("data", [])
                
                # Filter and format model information
                formatted_models = []
                for model in models:
                    formatted_models.append({
                        "id": model.get("id"),
                        "name": model.get("name", model.get("id")),
                        "context_length": model.get("context_length"),
                        "pricing": model.get("pricing"),
                        "is_free": "free" in model.get("id", "").lower(),
                    })
                    
                return formatted_models
                
        except Exception as e:
            logger.error("Failed to list OpenRouter models", error=str(e))
            return []