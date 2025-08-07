"""LLM Handler - Natural language to drone commands."""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMHandler:
    """Parse natural language to drone commands using LLM."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize LLM client.

        Args:
            api_key: OpenRouter/OpenAI API key
            model: Model name (e.g., openai/gpt-4o-mini)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "openai/gpt-4o-mini-2024-07-18")

        if not self.api_key or self.api_key == "your_key_here":
            logger.warning("No valid API key found. Using fallback command parsing only.")
            self.client = None
        else:
            # Log initialization
            logger.info(f"LLM Handler initialized with model: {self.model}")

            # Initialize Async OpenAI client with OpenRouter
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=8.0,  # 8 second timeout (well under MCP's 30s)
            )

    async def parse_command(
        self, user_input: str, telemetry: Dict[str, Any], safety_rules: str = ""
    ) -> List[Dict[str, Any]]:
        """Parse natural language to drone command sequence.

        Args:
            user_input: Natural language command from user
            telemetry: Current drone telemetry for context
            safety_rules: Additional safety rules to apply

        Returns:
            List of command dicts ready for DroneSphere API
        """

        # Try LLM parsing first if client available
        if self.client:
            try:
                commands = await self._parse_with_llm(user_input, telemetry, safety_rules)
                if commands:
                    return commands
            except asyncio.TimeoutError:
                logger.warning("LLM timeout, using fallback parser")
            except Exception as e:
                logger.warning(f"LLM failed: {e}, using fallback parser")

        # Fallback to simple rule-based parsing
        return self._fallback_parser(user_input, telemetry)

    async def _parse_with_llm(
        self, user_input: str, telemetry: Dict[str, Any], safety_rules: str
    ) -> List[Dict[str, Any]]:
        """Parse using LLM with timeout protection."""

        # Get current altitude for context
        current_altitude = telemetry.get('position', {}).get('relative_altitude', 0.0)
        battery_percent = telemetry.get('battery', {}).get('remaining_percent', 100.0)

        system_prompt = f"""You are an expert drone control system.

CURRENT DRONE STATE:
- Altitude: {current_altitude:.1f}m
- Battery: {battery_percent:.0f}%
- Armed: {telemetry.get('armed', False)}

AVAILABLE COMMANDS:
1. takeoff: {{"name": "takeoff", "params": {{"altitude": 1-120}}}}
2. land: {{"name": "land", "params": {{}}}}
3. goto (NED): {{"name": "goto", "params": {{"north": m, "east": m, "down": m}}}}
4. goto (GPS): {{"name": "goto", "params": {{"latitude": deg, "longitude": deg, "altitude": m}}}}
5. wait: {{"name": "wait", "params": {{"duration": seconds}}}}
6. rtl: {{"name": "rtl", "params": {{}}}}

CRITICAL RULES:
- NED: down is NEGATIVE for altitude (e.g., -20 = 20m high)
- When user doesn't specify altitude in movement, use current altitude
- Detect sequences: "then", "after", "next" = multiple commands
- Understand ANY language, respond in user's language
- Return ONLY valid JSON array of commands

{safety_rules}

OUTPUT: Return ONLY the JSON array, no explanation."""

        try:
            # Use asyncio timeout for extra protection
            async with asyncio.timeout(7):  # 7 seconds max
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input},
                    ],
                    temperature=0.1,
                    max_tokens=500,  # Reduced for faster response
                )

            content = response.choices[0].message.content.strip()

            # Extract JSON from response
            if '[' in content and ']' in content:
                start = content.find('[')
                end = content.rfind(']') + 1
                json_str = content[start:end]
                commands = json.loads(json_str)

                # Validate command structure
                valid_commands = []
                for cmd in commands:
                    if isinstance(cmd, dict) and "name" in cmd and "params" in cmd:
                        valid_commands.append(cmd)

                return valid_commands

        except asyncio.TimeoutError:
            logger.warning("LLM request timed out")
            raise
        except Exception as e:
            logger.error(f"LLM parsing error: {e}")
            raise

        return []

    def _fallback_parser(self, user_input: str, telemetry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple rule-based command parser as fallback.

        Args:
            user_input: Natural language command
            telemetry: Current telemetry for context

        Returns:
            List of parsed commands
        """
        commands = []
        text = user_input.lower()

        # Get current altitude for context
        current_alt = telemetry.get('position', {}).get('relative_altitude', 0.0)

        # Split by sequence indicators
        parts = []
        for indicator in ['then', 'after that', 'next', 'and then']:
            if indicator in text:
                splits = text.split(indicator)
                parts = [s.strip() for s in splits if s.strip()]
                break

        if not parts:
            parts = [text]

        # Parse each part
        for part in parts:
            # Takeoff command
            if 'takeoff' in part or 'take off' in part or 'بلند' in part:
                match = re.search(r'(\d+)', part)
                altitude = int(match.group(1)) if match else 10
                commands.append({"name": "takeoff", "params": {"altitude": min(altitude, 120)}})

            # Land command
            elif 'land' in part or 'فرود' in part:
                commands.append({"name": "land", "params": {}})

            # RTL command
            elif 'rtl' in part or 'return' in part or 'home' in part:
                commands.append({"name": "rtl", "params": {}})

            # Wait command
            elif 'wait' in part or 'hover' in part or 'stay' in part:
                match = re.search(r'(\d+)', part)
                duration = int(match.group(1)) if match else 5
                commands.append({"name": "wait", "params": {"duration": min(duration, 300)}})

            # Goto command (simple NED)
            elif any(dir in part for dir in ['north', 'south', 'east', 'west', 'up', 'down']):
                north = east = down = 0

                # Extract distance
                match = re.search(r'(\d+)', part)
                distance = int(match.group(1)) if match else 5

                if 'north' in part:
                    north = distance
                elif 'south' in part:
                    north = -distance

                if 'east' in part:
                    east = distance
                elif 'west' in part:
                    east = -distance

                if 'up' in part:
                    down = -distance  # Up means negative down
                elif 'down' in part:
                    down = distance
                else:
                    # Maintain current altitude if not specified
                    down = -current_alt

                commands.append(
                    {"name": "goto", "params": {"north": north, "east": east, "down": down}}
                )

        # If no commands parsed, try emergency keywords
        if not commands:
            if 'emergency' in text or 'stop' in text:
                commands.append({"name": "land", "params": {}})

        logger.info(f"Fallback parser result: {commands}")
        return commands
