# src/adapters/output/nlp/providers/deepseek_adapter.py
"""Deepseek-based NLP adapter implementation stub.

This module will implement the NLP port using Deepseek's API.
Deepseek is particularly good at understanding technical/code-like commands.
"""

from typing import Any, Dict, List, Optional

from src.adapters.output.nlp.base_adapter import BaseNLPAdapter
from src.core.ports.output.nlp_service import (
    NLPProvider,
    ParseResult,
)


class DeepseekNLPAdapter(BaseNLPAdapter):
    """Deepseek-based implementation of the NLP service port.
    
    This adapter will use Deepseek's API for command parsing,
    particularly effective for technical or code-like command syntax.
    """
    
    def __init__(self, api_key: str, model: str = "deepseek-coder"):
        """Initialize the Deepseek NLP adapter.
        
        Args:
            api_key: Deepseek API key
            model: Model to use (deepseek-coder, deepseek-chat)
        """
        super().__init__()
        self.api_key = api_key
        self.model = model
        # TODO: Initialize Deepseek client
    
    @property
    def provider_name(self) -> str:
        """Get the name of the NLP provider."""
        return NLPProvider.DEEPSEEK
    
    @property
    def requires_internet(self) -> bool:
        """Check if this provider requires internet connection."""
        return True  # Deepseek requires API calls
    
    async def parse_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ParseResult:
        """Parse natural language text into a drone command using Deepseek.
        
        Deepseek advantages:
        - Good at understanding structured/technical commands
        - Can handle code-like syntax
        - Efficient for command parsing tasks
        """
        # TODO: Implement Deepseek-based parsing
        raise NotImplementedError("Deepseek adapter is not yet implemented")
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["en", "zh"]  # Deepseek primarily supports English and Chinese