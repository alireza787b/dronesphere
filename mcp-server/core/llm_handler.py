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
3. rtl: {{"name": "rtl", "params": {{}}}}
4. wait: {{"name": "wait", "params": {{"duration": seconds}}}}

5. goto - SMART NAVIGATION (handles all coordinate types):
   a) GPS: {{"name": "goto", "params": {{"latitude": deg, "longitude": deg, "altitude": m}}}}
   b) NED from origin: {{"name": "goto", "params": {{"north": m, "east": m, "down": m}}}}
   c) Body frame: {{"name": "goto", "params": {{"forward": m, "right": m, "up_body": m}}}}
   d) Offset from current: {{"name": "goto", "params": {{"offset_north": m, "offset_east": m, "offset_up": m, "reference": "current"}}}}
   e) Offset from home: {{"name": "goto", "params": {{"offset_north": m, "offset_east": m, "offset_up": m, "reference": "home"}}}}

NAVIGATION RULES:
- "fly forward X": Use body frame: {{"forward": X, "maintain_altitude": true}}
- "go north X": Use offset: {{"offset_north": X, "reference": "current", "maintain_altitude": true}}
- "go X meters north from home": Use offset: {{"offset_north": X, "reference": "home"}}
- "move right X": Use body frame: {{"right": X, "maintain_altitude": true}}
- "go up X": Use offset: {{"offset_up": X, "reference": "current"}}
- "return home" / "go home" / "return to launch": Use rtl command (PX4 native)
- "go back to home" / "fly home": Use rtl command (NOT goto home position)
- NED down is NEGATIVE for altitude (e.g., down=-20 means 20m high)
- offset_up is POSITIVE for altitude (e.g., offset_up=20 means 20m up)
- Always add "maintain_altitude": true for horizontal-only movements

CRITICAL RULES:
- Detect sequences: "then", "after", "next" = multiple commands
- Understand ANY language, respond in user's language
- Return ONLY valid JSON array of commands
- For movement, prefer goto with appropriate coordinate type

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

            # RTL command (return home - use PX4 native RTL)
            elif any(
                word in part
                for word in [
                    'rtl',
                    'return home',
                    'go home',
                    'fly home',
                    'return to launch',
                    'go back home',
                ]
            ):
                commands.append({"name": "rtl", "params": {}})

            # Wait command
            elif 'wait' in part or 'hover' in part or 'stay' in part:
                match = re.search(r'(\d+)', part)
                duration = int(match.group(1)) if match else 5
                commands.append({"name": "wait", "params": {"duration": min(duration, 300)}})

            # Forward/backward/right/left (Body frame)
            elif any(word in part for word in ['forward', 'backward', 'right', 'left']):
                forward = right = up_val = 0

                # Extract distance
                match = re.search(r'(\d+)', part)
                distance = int(match.group(1)) if match else 5

                if 'forward' in part:
                    forward = distance
                elif 'backward' in part or 'back' in part:
                    forward = -distance

                if 'right' in part:
                    right = distance
                elif 'left' in part:
                    right = -distance

                commands.append(
                    {
                        "name": "goto",
                        "params": {"forward": forward, "right": right, "maintain_altitude": True},
                    }
                )

            # North/south/east/west (Offset from current)
            elif any(dir in part for dir in ['north', 'south', 'east', 'west']):
                offset_north = offset_east = offset_up = 0

                # Extract distance
                match = re.search(r'(\d+)', part)
                distance = int(match.group(1)) if match else 5

                if 'north' in part:
                    offset_north = distance
                elif 'south' in part:
                    offset_north = -distance

                if 'east' in part:
                    offset_east = distance
                elif 'west' in part:
                    offset_east = -distance

                # Check for "from home" or default to "current"
                reference = "home" if "home" in part or "origin" in part else "current"

                commands.append(
                    {
                        "name": "goto",
                        "params": {
                            "offset_north": offset_north,
                            "offset_east": offset_east,
                            "reference": reference,
                            "maintain_altitude": True,
                        },
                    }
                )

            # Up/down (Offset from current altitude)
            elif 'up' in part or 'down' in part:
                match = re.search(r'(\d+)', part)
                distance = int(match.group(1)) if match else 5

                if 'up' in part:
                    offset_up = distance
                else:  # down
                    offset_up = -distance

                commands.append(
                    {"name": "goto", "params": {"offset_up": offset_up, "reference": "current"}}
                )

        # If no commands parsed, try emergency keywords
        if not commands:
            if 'emergency' in text or 'stop' in text:
                commands.append({"name": "land", "params": {}})

        logger.info(f"Fallback parser result: {commands}")
        return commands
