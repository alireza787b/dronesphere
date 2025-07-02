# server/src/server/services/llm/parsing.py
"""
Generic LLM output parsing utilities using LangChain tools.

This module provides robust parsing capabilities for any LLM provider,
using LangChain's built-in parsing tools for better reliability.
"""

import json
import re
from typing import Any

import structlog
from langchain.output_parsers import (
    OutputFixingParser,
    ResponseSchema,
    RetryOutputParser,
    StructuredOutputParser,
)
from langchain.output_parsers.json import parse_json_markdown
from langchain.schema.output_parser import OutputParserException
from pydantic import BaseModel, ValidationError

logger = structlog.get_logger()


class RobustCommandParser:
    """
    Generic parser for LLM outputs using LangChain's robust parsing tools.

    This parser handles:
    - JSON extraction from markdown blocks
    - Key normalization (capitalization issues)
    - Malformed JSON fixing
    - Retry with error feedback
    - Fallback mechanisms
    """

    def __init__(self, llm=None, max_retries: int = 2):
        """
        Initialize the robust parser.

        Args:
            llm: Optional LLM instance for retry parsing
            max_retries: Maximum number of retry attempts
        """
        self.llm = llm
        self.max_retries = max_retries

        # Define response schemas for structured output
        self.response_schemas = [
            ResponseSchema(
                name="commands",
                description="List of extracted commands with parameters",
                type="array",
            ),
            ResponseSchema(
                name="response_text",
                description="Natural language response to the user",
                type="string",
            ),
            ResponseSchema(
                name="requires_clarification",
                description="Whether user input needs clarification",
                type="boolean",
            ),
            ResponseSchema(
                name="clarification_questions",
                description="Questions to ask user for clarification",
                type="array",
            ),
            ResponseSchema(
                name="detected_language",
                description="Detected language code (e.g., 'en', 'fa')",
                type="string",
            ),
            ResponseSchema(
                name="overall_confidence",
                description="Overall confidence in the extraction (0.0-1.0)",
                type="number",
            ),
        ]

        # Create base parser
        self.structured_parser = StructuredOutputParser.from_response_schemas(
            self.response_schemas
        )

        # Create fixing parser if LLM is provided
        if self.llm:
            self.fixing_parser = OutputFixingParser.from_llm(
                parser=self.structured_parser, llm=self.llm
            )
            self.retry_parser = RetryOutputParser.from_llm(
                parser=self.structured_parser, llm=self.llm
            )
        else:
            self.fixing_parser = None
            self.retry_parser = None

    def parse(
        self,
        text: str,
        pydantic_model: type[BaseModel] | None = None,
        original_prompt: str | None = None,
    ) -> dict[str, Any] | BaseModel:
        """
        Parse LLM output with multiple fallback strategies.

        Args:
            text: Raw LLM output text
            pydantic_model: Optional Pydantic model to validate against
            original_prompt: Optional original prompt for retry parsing

        Returns:
            Parsed output as dict or Pydantic model instance

        Raises:
            OutputParserException: If all parsing strategies fail
        """
        logger.debug("Starting robust parsing", text_length=len(text))

        # Strategy 1: Try to extract and parse clean JSON
        try:
            cleaned_json = self._extract_json(text)
            parsed_data = json.loads(cleaned_json)
            normalized_data = self._normalize_keys(parsed_data)

            if pydantic_model:
                return self._validate_with_pydantic(normalized_data, pydantic_model)
            return normalized_data

        except (json.JSONDecodeError, ValidationError) as e:
            logger.debug(f"Initial parsing failed: {e}")

        # Strategy 2: Try LangChain's markdown JSON parser
        try:
            parsed_data = parse_json_markdown(text)
            normalized_data = self._normalize_keys(parsed_data)

            if pydantic_model:
                return self._validate_with_pydantic(normalized_data, pydantic_model)
            return normalized_data

        except Exception as e:
            logger.debug(f"Markdown parsing failed: {e}")

        # Strategy 3: Try structured parser
        try:
            parsed_data = self.structured_parser.parse(text)
            normalized_data = self._normalize_keys(parsed_data)

            if pydantic_model:
                return self._validate_with_pydantic(normalized_data, pydantic_model)
            return normalized_data

        except OutputParserException as e:
            logger.debug(f"Structured parsing failed: {e}")

        # Strategy 4: Try fixing parser if available
        if self.fixing_parser:
            try:
                parsed_data = self.fixing_parser.parse(text)
                normalized_data = self._normalize_keys(parsed_data)
                if pydantic_model:
                    return self._validate_with_pydantic(normalized_data, pydantic_model)
                return normalized_data

            except Exception as e:
                logger.debug(f"Fixing parser failed: {e}")

        # Strategy 5: Try retry parser with original prompt if available
        if self.retry_parser and original_prompt:
            try:
                parsed_data = self.retry_parser.parse_with_prompt(text, original_prompt)
                normalized_data = self._normalize_keys(parsed_data)

                if pydantic_model:
                    return self._validate_with_pydantic(normalized_data, pydantic_model)
                return normalized_data

            except Exception as e:
                logger.debug(f"Retry parser failed: {e}")

        # Strategy 6: Last resort - extract what we can
        try:
            fallback_data = self._extract_fallback_data(text)
            if pydantic_model:
                return self._validate_with_pydantic(fallback_data, pydantic_model)
            return fallback_data

        except Exception as e:
            logger.error("All parsing strategies failed", error=str(e))
            raise OutputParserException(f"Failed to parse LLM output: {str(e)}")

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown blocks and other formats.

        Args:
            text: Raw text containing JSON

        Returns:
            Cleaned JSON string
        """
        # Remove markdown code blocks
        code_block_pattern = r"```(?:json)?\s*([\s\S]+?)\s*```"
        code_match = re.search(code_block_pattern, text, re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()

        # Try to find JSON object directly
        json_pattern = r"\{[\s\S]*\}"
        json_match = re.search(json_pattern, text)
        if json_match:
            return json_match.group(0).strip()

        # Return original text as last resort
        return text.strip()

    def _normalize_keys(self, obj: Any) -> Any:
        """
        Recursively normalize dictionary keys to handle capitalization variations.

        Args:
            obj: Object to normalize (dict, list, or other)

        Returns:
            Normalized object
        """
        if isinstance(obj, dict):
            # Key normalization mapping
            key_map = {
                "Commands": "commands",
                "COMMANDS": "commands",
                "Response_text": "response_text",
                "ResponseText": "response_text",
                "response text": "response_text",
                "Requires_clarification": "requires_clarification",
                "RequiresClarification": "requires_clarification",
                "Clarification_questions": "clarification_questions",
                "ClarificationQuestions": "clarification_questions",
                "Detected_language": "detected_language",
                "DetectedLanguage": "detected_language",
                "Overall_confidence": "overall_confidence",
                "OverallConfidence": "overall_confidence",
                "confidence": "overall_confidence",
                "Confidence": "overall_confidence",
                "Original_phrase": "original_phrase",
                "OriginalPhrase": "original_phrase",
            }

            normalized = {}
            for k, v in obj.items():
                # Check if key needs normalization
                normalized_key = key_map.get(k, k)

                # Also try lowercase version
                if normalized_key == k and k != k.lower():
                    lowercase_key = k.lower()
                    if lowercase_key in [
                        "commands",
                        "response_text",
                        "requires_clarification",
                        "clarification_questions",
                        "detected_language",
                        "overall_confidence",
                        "original_phrase",
                    ]:
                        normalized_key = lowercase_key

                normalized[normalized_key] = self._normalize_keys(v)

            return normalized

        elif isinstance(obj, list):
            return [self._normalize_keys(item) for item in obj]

        return obj

    def _validate_with_pydantic(
        self, data: dict[str, Any], model_class: type[BaseModel]
    ) -> BaseModel:
        """
        Validate data with Pydantic model, handling common issues.

        Args:
            data: Data to validate
            model_class: Pydantic model class

        Returns:
            Validated model instance

        Raises:
            ValidationError: If validation fails
        """
        # Handle case where data might be wrapped
        if len(data) == 1 and isinstance(list(data.values())[0], dict):
            inner_data = list(data.values())[0]
            if all(key in inner_data for key in ["commands", "response_text"]):
                data = inner_data

        # Ensure required fields have defaults
        if "commands" not in data:
            data["commands"] = []
        if "response_text" not in data:
            data["response_text"] = ""
        if "requires_clarification" not in data:
            data["requires_clarification"] = False
        if "clarification_questions" not in data:
            data["clarification_questions"] = []
        if "detected_language" not in data:
            data["detected_language"] = "en"
        if "overall_confidence" not in data:
            data["overall_confidence"] = 0.5

        # Ensure commands have required fields
        if isinstance(data.get("commands"), list):
            for cmd in data["commands"]:
                if isinstance(cmd, dict):
                    if "confidence" not in cmd:
                        cmd["confidence"] = 0.7
                    if "original_phrase" not in cmd:
                        cmd["original_phrase"] = ""

        return model_class(**data)

    def _extract_fallback_data(self, text: str) -> dict[str, Any]:
        """
        Extract basic data as a last resort fallback.

        Args:
            text: Raw text to extract from

        Returns:
            Basic extracted data
        """
        logger.warning("Using fallback extraction")

        # Try to detect commands from common patterns
        commands = []
        text_lower = text.lower()

        # Common command patterns
        if "takeoff" in text_lower or "take off" in text_lower:
            altitude_match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:meter|metre|m)", text_lower
            )
            altitude = float(altitude_match.group(1)) if altitude_match else 10.0
            commands.append(
                {
                    "name": "takeoff",
                    "category": "flight",
                    "parameters": {"altitude": altitude},
                    "confidence": 0.5,
                    "original_phrase": text[:50],
                }
            )
        elif "land" in text_lower:
            commands.append(
                {
                    "name": "land",
                    "category": "flight",
                    "parameters": {},
                    "confidence": 0.5,
                    "original_phrase": text[:50],
                }
            )

        # Detect language
        detected_language = (
            "fa" if any(ord(c) > 0x0600 and ord(c) < 0x06FF for c in text) else "en"
        )

        return {
            "commands": commands,
            "response_text": "I processed your request, but had some trouble understanding the full context.",
            "requires_clarification": len(commands) == 0,
            "clarification_questions": (
                ["Could you please rephrase your command?"]
                if len(commands) == 0
                else []
            ),
            "detected_language": detected_language,
            "overall_confidence": 0.5 if commands else 0.0,
        }

    def get_format_instructions(self) -> str:
        """
        Get formatting instructions for the LLM.

        Returns:
            Formatting instructions string
        """
        base_instructions = self.structured_parser.get_format_instructions()

        additional_instructions = """
IMPORTANT: Your response must be ONLY valid JSON. Do not wrap it in markdown code blocks.
Do not include any text before or after the JSON.

The JSON must include these exact keys (all lowercase):
- commands: array of command objects
- response_text: string
- requires_clarification: boolean
- clarification_questions: array of strings
- detected_language: string ("en" or "fa")
- overall_confidence: number between 0 and 1

Each command in the commands array must have:
- name: string (command name like "takeoff", "land")
- category: string (command category like "flight", "navigation")
- parameters: object (command-specific parameters)
- confidence: number between 0 and 1
- original_phrase: string (the user's words that triggered this command)
"""

        return base_instructions + "\n\n" + additional_instructions


def create_command_parser(llm=None) -> RobustCommandParser:
    """
    Factory function to create a command parser.

    Args:
        llm: Optional LLM instance for advanced parsing features

    Returns:
        RobustCommandParser instance
    """
    return RobustCommandParser(llm=llm)
