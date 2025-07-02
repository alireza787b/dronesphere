# server/src/server/services/llm/providers/openrouter.py
"""
OpenRouter LLM provider implementation.

This module implements the LLM provider interface for OpenRouter,
which provides access to multiple LLM models through a unified API.
"""

from typing import Any

import structlog
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..base import (
    BaseLLMProvider,
    ClarificationRequest,
    ClarificationResponse,
    CommandExtractionResult,
    ConversationContext,
)
from ..config import OpenRouterConfig
from ..parsing import create_command_parser

logger = structlog.get_logger()


class ExtractedCommand(BaseModel):
    """Model for a single extracted command."""

    name: str = Field(description="Command name (e.g., 'takeoff', 'land')")
    category: str = Field(description="Command category (e.g., 'flight', 'navigation')")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Command parameters extracted from user input"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this command extraction",
    )
    original_phrase: str = Field(
        default="", description="The part of user input that triggered this command"
    )


class CommandExtractionOutput(BaseModel):
    """Structured output for command extraction."""

    commands: list[ExtractedCommand] = Field(
        default_factory=list, description="List of extracted commands in order"
    )
    response_text: str = Field(
        default="", description="Natural language response to the user"
    )
    requires_clarification: bool = Field(
        default=False, description="Whether user input needs clarification"
    )
    clarification_questions: list[str] = Field(
        default_factory=list, description="Questions to ask user for clarification"
    )
    detected_language: str = Field(
        default="en", description="Detected language code (e.g., 'en', 'fa')"
    )
    overall_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Overall confidence in the extraction"
    )


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM provider implementation using generic parsing."""

    def __init__(self, config: OpenRouterConfig):
        """
        Initialize OpenRouter provider with generic parser.

        Args:
            config: OpenRouter configuration
        """
        # Extract OpenAI-compatible parameters only
        model_kwargs = {
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
        }

        # Set up default headers for OpenRouter
        default_headers = {
            "HTTP-Referer": "https://dronesphere.com",
            "X-Title": "DroneSphere",
        }

        # Initialize LangChain ChatOpenAI with OpenRouter endpoint
        self.llm = ChatOpenAI(
            openai_api_key=config.api_key,
            openai_api_base=config.base_url,
            model_name=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            model_kwargs=model_kwargs,
            request_timeout=config.timeout,
            max_retries=config.retry_attempts,
            default_headers=default_headers,
        )

        # Create generic parser with our LLM
        parser = create_command_parser(llm=self.llm)

        # Initialize parent with config and parser
        super().__init__(config.dict(), parser=parser)

        self.config = config

        logger.info(
            "OpenRouter provider initialized",
            model=config.model,
            base_url=config.base_url,
        )

    async def extract_commands(
        self,
        user_input: str,
        context: ConversationContext,
        available_commands: list[dict[str, Any]],
    ) -> CommandExtractionResult:
        """
        Extract drone commands from natural language input using generic parser.

        Args:
            user_input: The user's natural language input
            context: Current conversation context
            available_commands: List of available command schemas

        Returns:
            CommandExtractionResult containing extracted commands
        """
        try:
            # Build command examples from available commands
            command_examples = self._build_command_examples(available_commands)

            # Create extraction prompt
            system_prompt = self._build_extraction_prompt(command_examples, context)

            # Get format instructions from parser
            format_instructions = self.parser.get_format_instructions()

            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
            ]

            # Add conversation history if available
            for msg in context.history[-5:]:  # Last 5 messages for context
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(
                        SystemMessage(content=f"Previous response: {msg['content']}")
                    )

            # Add current input
            messages.append(HumanMessage(content=user_input))

            # Add format instructions
            messages.append(SystemMessage(content=format_instructions))

            # Get response from LLM
            logger.info("Extracting commands", user_input=user_input)

            # Use lower temperature for command extraction
            self.llm.temperature = self.config.command_extraction_temperature
            response = await self.llm.agenerate([messages])
            self.llm.temperature = self.config.temperature  # Reset

            # Get the raw output
            raw_output = response.generations[0][0].text
            logger.debug("Raw LLM response", response=raw_output[:200])

            # Parse using generic parser
            parsed_output = self.parser.parse(
                raw_output,
                pydantic_model=CommandExtractionOutput,
                original_prompt=user_input,
            )

            # Convert to CommandExtractionResult
            result = CommandExtractionResult(
                commands=[cmd.dict() for cmd in parsed_output.commands],
                confidence=parsed_output.overall_confidence,
                response_text=parsed_output.response_text,
                requires_clarification=parsed_output.requires_clarification,
                clarification_questions=parsed_output.clarification_questions,
                detected_language=parsed_output.detected_language,
            )

            logger.info(
                "Commands extracted successfully",
                num_commands=len(result.commands),
                confidence=result.confidence,
            )

            return result

        except Exception as e:
            logger.error("Failed to extract commands", error=str(e), exc_info=True)
            return self._create_error_response(user_input, str(e))

    async def generate_response(
        self, prompt: str, context: ConversationContext | None = None, **kwargs
    ) -> str:
        """
        Generate a general response from the LLM.

        Args:
            prompt: The prompt to send to the LLM
            context: Optional conversation context
            **kwargs: Additional parameters

        Returns:
            Generated response text
        """
        try:
            messages = [SystemMessage(content=prompt)]

            if context:
                # Add conversation history
                for msg in context.history[-5:]:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))

            # Use conversation temperature for general responses
            self.llm.temperature = self.config.conversation_temperature
            response = await self.llm.agenerate([messages])
            self.llm.temperature = self.config.temperature  # Reset

            return response.generations[0][0].text

        except Exception as e:
            logger.error("Failed to generate response", error=str(e))
            return f"I apologize, but I encountered an error: {str(e)}"

    async def handle_clarification(
        self, clarification_request: ClarificationRequest
    ) -> ClarificationResponse:
        """
        Handle ambiguous commands by requesting clarification.

        Args:
            clarification_request: Details about what needs clarification

        Returns:
            ClarificationResponse with clarified interpretation
        """
        try:
            prompt = f"""
The user provided this input: "{clarification_request.original_input}"

The following parts are ambiguous: {', '.join(clarification_request.ambiguous_parts)}

Suggestions for clarification: {', '.join(clarification_request.suggestions)}

Please provide a friendly response asking for clarification in the user's language.
Include the suggestions naturally in your response.
"""

            response_text = await self.generate_response(
                prompt, clarification_request.context
            )

            return ClarificationResponse(
                clarified_input="",  # Will be filled after user responds
                confidence=0.0,
                response_text=response_text,
            )

        except Exception as e:
            logger.error("Failed to handle clarification", error=str(e))
            return ClarificationResponse(
                clarified_input="",
                confidence=0.0,
                response_text="Could you please clarify what you meant?",
            )

    async def format_error_response(
        self, error: Exception, context: ConversationContext, user_input: str
    ) -> str:
        """
        Format an error into a user-friendly response.

        Args:
            error: The exception that occurred
            context: Current conversation context
            user_input: The original user input

        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__

        prompt = f"""
An error occurred while processing the command: "{user_input}"
Error type: {error_type}
Error message: {str(error)}

Please provide a helpful, friendly error message in the user's language.
Explain what went wrong and suggest what they can do.
Do not include technical details unless necessary.
"""

        return await self.generate_response(prompt, context)

    async def check_health(self) -> tuple[bool, str]:
        """
        Check if the OpenRouter API is accessible.

        Returns:
            Tuple of (is_healthy, status_message)
        """
        try:
            # Try a simple completion
            test_messages = [
                SystemMessage(content="Respond with 'OK' if you receive this.")
            ]
            response = await self.llm.agenerate([test_messages])

            if response and response.generations:
                return True, f"OpenRouter is healthy (model: {self.config.model})"
            else:
                return False, "OpenRouter returned empty response"

        except Exception as e:
            return False, f"OpenRouter health check failed: {str(e)}"

    def _build_extraction_prompt(
        self, command_examples: str, context: ConversationContext
    ) -> str:
        """Build the system prompt for command extraction using the new prompt builder."""
        from ..prompts.builder import prompt_builder

        # Use the new prompt builder
        return prompt_builder.build_extraction_prompt(
            user_input="",  # Will be added later in the messages
            available_commands=[],  # Will be populated from command_examples
            context={
                "drone_id": context.drone_id,
                "status": (
                    context.drone_state.get("status", "unknown")
                    if context.drone_state
                    else "disconnected"
                ),
                "battery": (
                    context.drone_state.get("battery", 0) if context.drone_state else 0
                ),
            },
        )

    def _build_command_examples(self, available_commands: list[dict[str, Any]]) -> str:
        """Build command examples from available commands."""
        examples = []

        for cmd in available_commands:
            if not cmd:
                continue

            name = cmd.get("metadata", {}).get("name", "unknown")
            description = cmd.get("spec", {}).get("description", {}).get("brief", "")
            params = cmd.get("spec", {}).get("parameters", {})

            param_list = []
            for param_name, param_spec in params.items():
                param_type = param_spec.get("type", "unknown")
                required = param_spec.get("required", False)
                default = param_spec.get("default", "none")
                param_list.append(
                    f"  - {param_name} ({param_type}): "
                    f"{'required' if required else f'optional, default={default}'}"
                )

            # Get examples
            cmd_examples = (
                cmd.get("spec", {}).get("description", {}).get("examples", [])
            )
            example_texts = []
            for ex in cmd_examples[:2]:  # Show max 2 examples
                text = ex.get("text", "")
                params = ex.get("params", {})
                example_texts.append(f'    "{text}" → {params}')

            examples.append(
                f"""
Command: {name}
Description: {description}
Parameters:
{chr(10).join(param_list)}
Examples:
{chr(10).join(example_texts)}
"""
            )

        return "\n".join(examples)

    def _create_error_response(
        self, user_input: str, error: str
    ) -> CommandExtractionResult:
        """
        Create an error response when extraction fails.

        Args:
            user_input: Original user input
            error: Error message

        Returns:
            CommandExtractionResult with error information
        """
        return CommandExtractionResult(
            commands=[],
            confidence=0.0,
            response_text="I'm sorry, I couldn't understand that command. Could you please rephrase?",
            error=f"Extraction error: {error}",
        )


# Convenience function for creating provider instance
def create_openrouter_provider(config: dict[str, Any]) -> OpenRouterProvider:
    """
    Create an OpenRouter provider instance.

    Args:
        config: Configuration dictionary

    Returns:
        OpenRouterProvider instance
    """
    openrouter_config = OpenRouterConfig(**config)
    return OpenRouterProvider(openrouter_config)
