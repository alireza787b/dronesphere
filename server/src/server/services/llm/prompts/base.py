# server/src/server/services/llm/prompts/base.py
"""
Base prompt template system for multi-layer prompt generation.

This module provides the foundation for building consistent,
customizable prompts across different use cases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class PromptLayer(str, Enum):
    """Different layers in the prompt construction."""

    ROLE = "role"
    CONTEXT = "context"
    INSTRUCTIONS = "instructions"
    CONSTRAINTS = "constraints"
    EXAMPLES = "examples"
    FORMAT = "format"
    OUTPUT = "output"
    VALIDATION = "validation"


@dataclass
class PromptSection:
    """A section of the prompt with priority and content."""

    layer: PromptLayer
    content: str
    priority: int = 0  # Lower number = higher priority
    required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePromptTemplate(ABC):
    """
    Abstract base class for all prompt templates.

    Provides a layered approach to prompt construction with
    customizable sections and priorities.
    """

    def __init__(self):
        self.sections: list[PromptSection] = []
        self._build_template()

    @abstractmethod
    def _build_template(self) -> None:
        """Build the template sections. Must be implemented by subclasses."""
        pass

    def add_section(
        self,
        layer: PromptLayer,
        content: str,
        priority: int = 0,
        required: bool = True,
        **metadata,
    ) -> None:
        """Add a section to the prompt template."""
        section = PromptSection(
            layer=layer,
            content=content,
            priority=priority,
            required=required,
            metadata=metadata,
        )
        self.sections.append(section)

    def render(self, variables: dict[str, Any]) -> str:
        """
        Render the prompt with the given variables.

        Args:
            variables: Variables to interpolate into the template

        Returns:
            Rendered prompt string
        """
        # Sort sections by priority
        sorted_sections = sorted(self.sections, key=lambda s: s.priority)

        # Render each section
        rendered_parts = []
        for section in sorted_sections:
            if not section.required and not self._should_include_section(
                section, variables
            ):
                continue

            try:
                rendered_content = section.content.format(**variables)
                if rendered_content.strip():
                    rendered_parts.append(rendered_content)
            except KeyError as e:
                if section.required:
                    raise ValueError(
                        f"Missing required variable for {section.layer}: {e}"
                    )
                logger.debug(
                    f"Skipping optional section {section.layer} due to missing variable: {e}"
                )

        return "\n\n".join(rendered_parts)

    def _should_include_section(
        self, section: PromptSection, variables: dict[str, Any]
    ) -> bool:
        """Determine if an optional section should be included."""
        # Can be overridden by subclasses for custom logic
        return True

    def customize(self, layer: PromptLayer, new_content: str) -> None:
        """Customize a specific layer's content."""
        for section in self.sections:
            if section.layer == layer:
                section.content = new_content
                return
        # If layer doesn't exist, add it
        self.add_section(layer, new_content, priority=50)

    def get_required_variables(self) -> list[str]:
        """Get list of required variables for this template."""
        import re

        variables = set()

        for section in self.sections:
            if section.required:
                # Find all {variable} patterns
                matches = re.findall(r"\{(\w+)\}", section.content)
                variables.update(matches)

        return sorted(list(variables))
