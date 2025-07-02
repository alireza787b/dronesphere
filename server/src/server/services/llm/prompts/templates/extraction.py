# server/src/server/services/llm/prompts/templates/extraction.py
"""
Command extraction prompt templates with multi-layer construction.
OPTIMIZED VERSION - Shorter but more effective.
"""

from typing import Any, Dict, List, Optional

from ..base import BasePromptTemplate, PromptLayer


class CommandExtractionTemplate(BasePromptTemplate):
    """
    Optimized template for extracting commands from natural language.
    """
    
    def _build_template(self) -> None:
        """Build the multi-layer extraction template."""
        
        # Layer 1: Role Definition (Priority 0)
        self.add_section(
            PromptLayer.ROLE,
            """You are a STRICT drone command parser. Critical rules:
1. You can ONLY use command names from the available commands list
2. NEVER invent or modify command names
3. If a command isn't in the list, return empty commands array
4. Match commands EXACTLY - 'move' is NOT 'move_local'""",
            priority=0
        )
        
        # Layer 2: Available Commands (Priority 5)
        self.add_section(
            PromptLayer.CONTEXT,
            """AVAILABLE COMMANDS (USE ONLY THESE EXACT NAMES):
{available_commands}

⚠️ CRITICAL: You MUST use the EXACT command names above. Do NOT create new commands.""",
            priority=5
        )
        
        # Layer 3: Core Instructions (Priority 20)
        self.add_section(
            PromptLayer.INSTRUCTIONS,
            """Command Matching Rules:
1. User says "take off" → use "takeoff" (if available)
2. User says "land" → use "land" (if available)
3. User says "move X north, Y east" → use "move_local" with north/east parameters
4. User says "fly" without clear command → requires_clarification = true
5. User asks for unavailable action → commands = [] and explain in response_text

Parameter Extraction:
- For move_local: north/south is Y-axis, east/west is X-axis, up/down is Z-axis
- Climbing means negative down value (up = -down)
- Extract all numeric values with units""",
            priority=20
        )
        
        # Layer 4: Examples with Strict Matching (Priority 30)
        self.add_section(
            PromptLayer.EXAMPLES,
            """EXAMPLES OF STRICT MATCHING:

Input: "Move 5m north and 2m east"
Available: ["takeoff", "land", "move_local"]
Output: Use "move_local" with north=5, east=2

Input: "Do a flip"
Available: ["takeoff", "land", "move_local"]
Output: commands=[] because "flip" is NOT available

Input: "Fly north"
Available: ["takeoff", "land", "move_local"]
Output: Use "move_local" but requires_clarification for distance""",
            priority=30
        )
        
        # Layer 5: Output Format (Priority 50)
        self.add_section(
            PromptLayer.FORMAT,
            """RETURN THIS EXACT JSON (NO MARKDOWN):
{{
    "commands": [
        {{
            "name": "MUST_BE_FROM_AVAILABLE_LIST",
            "category": "flight/navigation/etc",
            "parameters": {{}},
            "confidence": 0.0-1.0,
            "original_phrase": "user input"
        }}
    ],
    "response_text": "response in user language",
    "requires_clarification": boolean,
    "clarification_questions": [],
    "detected_language": "en/fa/es/etc",
    "overall_confidence": 0.0-1.0
}}

User Input: "{user_input}"

RESPOND WITH PURE JSON:""",
            priority=50
        )



def create_extraction_examples() -> Dict[str, str]:
    """Create optimized example JSON outputs."""
    
    return {
        "example_clear": """{
    "commands": [{
        "name": "takeoff",
        "category": "flight",
        "parameters": {"altitude": 20.0},
        "confidence": 0.95,
        "original_phrase": "take off to 20 meters"
    }],
    "response_text": "Taking off to 20 meters",
    "requires_clarification": false,
    "clarification_questions": [],
    "detected_language": "en",
    "overall_confidence": 0.95
}""",
        
        "example_ambiguous": """{
    "commands": [],
    "response_text": "What altitude would you like?",
    "requires_clarification": true,
    "clarification_questions": ["Please specify altitude in meters"],
    "detected_language": "en",
    "overall_confidence": 0.3
}"""
    }

