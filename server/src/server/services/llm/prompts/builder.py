# server/src/server/services/llm/prompts/builder.py
"""
Smart prompt builder that assembles multi-layer prompts.

Handles dynamic content, validation, and optimization for
different scenarios and contexts.
"""

from typing import Any

import structlog

from .base import BasePromptTemplate
from .templates.extraction import CommandExtractionTemplate, create_extraction_examples

logger = structlog.get_logger()


class PromptBuilder:
    """
    Intelligent prompt builder for creating optimized prompts.

    Features:
    - Dynamic template selection
    - Context-aware customization
    - Validation and optimization
    - Caching for performance
    """

    def __init__(self):
        self.template_cache: dict[str, BasePromptTemplate] = {}
        self.examples_cache: dict[str, dict[str, str]] = {
            "extraction": create_extraction_examples()
        }

    def build_extraction_prompt(
        self,
        user_input: str,
        available_commands: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
        language_hint: str | None = None,
    ) -> str:
        """
        Build a command extraction prompt.

        Args:
            user_input: The user's input to process
            available_commands: List of available command definitions
            context: Optional context (drone state, etc.)
            language_hint: Optional language hint

        Returns:
            Optimized prompt string
        """
        # Get or create template
        template = self._get_template("extraction", CommandExtractionTemplate)

        # Prepare variables
        variables = {
            "user_input": user_input,
            "available_commands": self._format_available_commands(available_commands),
            **self.examples_cache["extraction"],
        }

        # Add context if provided
        if context:
            variables.update(
                {
                    "drone_id": context.get("drone_id", "unknown"),
                    "drone_status": context.get("status", "disconnected"),
                    "battery_level": context.get("battery", 0),
                }
            )

        # Add language-specific customizations
        if language_hint:
            self._customize_for_language(template, language_hint)

        # Render the prompt
        try:
            prompt = template.render(variables)

            # Validate the prompt
            self._validate_prompt(prompt)

            return prompt

        except Exception as e:
            logger.error(f"Failed to build extraction prompt: {e}")
            # Return a minimal fallback prompt
            return self._get_fallback_prompt(user_input)

    def _get_template(
        self, name: str, template_class: type[BasePromptTemplate]
    ) -> BasePromptTemplate:
        """Get or create a template instance."""
        if name not in self.template_cache:
            self.template_cache[name] = template_class()
        return self.template_cache[name]

    def _format_available_commands(self, commands: list[dict[str, Any]]) -> str:
        """Format available commands for inclusion in prompt."""
        if not commands:
            return "No specific commands available"

        formatted_commands = []
        for cmd in commands:
            if not cmd:
                continue

            name = cmd.get("metadata", {}).get("name", "unknown")
            brief = cmd.get("spec", {}).get("description", {}).get("brief", "")
            params = cmd.get("spec", {}).get("parameters", {})

            # Format parameters
            param_list = []
            for param_name, param_spec in params.items():
                param_type = param_spec.get("type", "any")
                required = param_spec.get("required", False)
                default = param_spec.get("default", None)

                if required:
                    param_list.append(f"{param_name} ({param_type}, required)")
                else:
                    param_list.append(
                        f"{param_name} ({param_type}, optional, default={default})"
                    )

            formatted_commands.append(
                f"- {name}: {brief}\n  Parameters: {', '.join(param_list) if param_list else 'none'}"
            )

        return "\n".join(formatted_commands)

    def _customize_for_language(
        self, template: BasePromptTemplate, language: str
    ) -> None:
        """Add language-specific customizations."""
        # This can be extended with language-specific instructions
        pass

    def _validate_prompt(self, prompt: str) -> None:
        """Validate the generated prompt."""
        if len(prompt) > 4000:  # Token limit approximation
            logger.warning(f"Prompt may be too long: {len(prompt)} characters")

        if "JSON" not in prompt:
            logger.warning("Prompt missing JSON format emphasis")

    def _get_fallback_prompt(self, user_input: str) -> str:
        """Get a minimal fallback prompt."""
        return f"""Extract drone commands from: "{user_input}"

Return ONLY this JSON structure:
{{
    "commands": [...],
    "response_text": "...",
    "requires_clarification": true/false,
    "clarification_questions": [...],
    "detected_language": "en",
    "overall_confidence": 0.0-1.0
}}

JSON ONLY:"""


# Singleton instance
prompt_builder = PromptBuilder()
