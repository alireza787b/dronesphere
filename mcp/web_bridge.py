"""Enhanced LLM-Powered Web Bridge for DroneSphere

Professional system with always-on telemetry, safety expert review, and real-time drone awareness.
Supports multiple languages, complex commands, natural conversation, and expert safety oversight.

Key Features:
- Always-on telemetry integration before every LLM prompt
- Professional drone safety expert with command review
- Real-time technical data responses (battery, position, altitude)
- Smart caching to avoid excessive API calls
- Extensible architecture for new telemetry fields
- Multi-language support with live data awareness

Path: mcp/web_bridge.py
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from openai import OpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dronesphere-enhanced-bridge")


class ChatMessage(BaseModel):
    """Chat message from user."""

    message: str
    target_drone: int = 1


class TelemetryManager:
    """Professional telemetry management with caching and error handling."""

    def __init__(self, cache_duration_seconds: int = 2):
        """Initialize telemetry manager with smart caching."""
        self.cache_duration = timedelta(seconds=cache_duration_seconds)
        self.cached_telemetry: Optional[Dict] = None
        self.cache_timestamp: Optional[datetime] = None
        self.last_error: Optional[str] = None

    async def get_live_telemetry(self, drone_id: int = 1) -> Dict[str, Any]:
        """Get live telemetry with smart caching and error handling."""

        # Check cache first (avoid excessive API calls)
        if self._is_cache_valid():
            logger.debug("Using cached telemetry data")
            return self.cached_telemetry

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8001/telemetry", timeout=5.0)

                if response.status_code == 200:
                    telemetry = response.json()

                    # Update cache
                    self.cached_telemetry = telemetry
                    self.cache_timestamp = datetime.now()
                    self.last_error = None

                    logger.debug("Successfully fetched live telemetry")
                    return telemetry
                else:
                    error_msg = f"Telemetry API error: {response.status_code}"
                    logger.warning(error_msg)
                    return self._get_fallback_telemetry(error_msg)

        except asyncio.TimeoutError:
            error_msg = "Telemetry timeout - drone may be unresponsive"
            logger.warning(error_msg)
            return self._get_fallback_telemetry(error_msg)
        except Exception as e:
            error_msg = f"Telemetry fetch error: {str(e)}"
            logger.error(error_msg)
            return self._get_fallback_telemetry(error_msg)

    def _is_cache_valid(self) -> bool:
        """Check if cached telemetry is still valid."""
        if not self.cached_telemetry or not self.cache_timestamp:
            return False
        return datetime.now() - self.cache_timestamp < self.cache_duration

    def _get_fallback_telemetry(self, error_msg: str) -> Dict[str, Any]:
        """Provide fallback telemetry when live data unavailable."""
        self.last_error = error_msg

        # Return cached data if available, otherwise basic fallback
        if self.cached_telemetry:
            logger.info("Using cached telemetry due to fetch error")
            return {**self.cached_telemetry, "telemetry_error": error_msg}

        return {
            "drone_id": 1,
            "timestamp": datetime.now().timestamp(),
            "telemetry_error": error_msg,
            "position": {"error": "No live data available"},
            "battery": {"error": "No live data available"},
            "flight_mode": "UNKNOWN",
            "armed": "unknown",
            "connected": False,
        }

    def format_for_llm(self, telemetry: Dict[str, Any]) -> str:
        """Format telemetry data for LLM system prompt (extensible)."""

        if "telemetry_error" in telemetry:
            return f"""
TELEMETRY STATUS: ⚠️ {telemetry['telemetry_error']}
(Using cached data if available - may not be current)
"""

        # Extract telemetry fields (easily extensible for new fields)
        timestamp = datetime.fromtimestamp(telemetry.get('timestamp', 0))

        # Position data
        pos = telemetry.get('position', {})
        latitude = pos.get('latitude', 'Unknown')
        longitude = pos.get('longitude', 'Unknown')
        altitude_msl = pos.get('altitude', 'Unknown')
        altitude_rel = pos.get('relative_altitude', 'Unknown')

        # Attitude data
        att = telemetry.get('attitude', {})
        roll = att.get('roll', 'Unknown')
        pitch = att.get('pitch', 'Unknown')
        yaw = att.get('yaw', 'Unknown')

        # Battery data
        bat = telemetry.get('battery', {})
        voltage = bat.get('voltage', 'Unknown')
        battery_pct = bat.get('remaining_percent', 'Unknown')

        # System status
        flight_mode = telemetry.get('flight_mode', 'Unknown')
        armed = telemetry.get('armed', 'Unknown')
        connected = telemetry.get('connected', 'Unknown')

        return f"""
🚁 LIVE TELEMETRY DATA (Updated: {timestamp.strftime('%H:%M:%S')}):

📍 POSITION & NAVIGATION:
  • GPS Location: {latitude:.6f}°, {longitude:.6f}°
  • Altitude MSL: {altitude_msl:.1f}m (Mean Sea Level)
  • Altitude Relative: {altitude_rel:.1f}m (Above takeoff point)
  • Attitude: Roll {roll:.1f}°, Pitch {pitch:.1f}°, Yaw {yaw:.1f}°

🔋 POWER & SYSTEMS:
  • Battery Voltage: {voltage:.1f}V
  • Battery Remaining: {battery_pct:.0f}%
  • Flight Mode: {flight_mode}
  • Armed: {armed}
  • Connected: {connected}

📊 SYSTEM ASSESSMENT:
  • Battery Status: {'✅ EXCELLENT' if isinstance(battery_pct, (int, float)) and battery_pct > 75 else '✅ GOOD' if isinstance(battery_pct, (int, float)) and battery_pct > 25 else '⚠️ LOW' if isinstance(battery_pct, (int, float)) and battery_pct > 15 else '🔴 CRITICAL'}
  • Flight Readiness: {'✅ READY' if armed and connected else '⚠️ NOT READY'}
  • Position Valid: {'✅ GPS LOCK' if isinstance(latitude, (int, float)) else '❌ NO GPS'}
"""


class DroneExpert:
    """Professional drone safety expert system."""

    def __init__(self):
        """Initialize drone expert with safety rules."""
        self.safety_rules = {
            "battery_min_flight": 20.0,  # Minimum battery % for flight operations
            "battery_critical": 15.0,  # Critical battery level
            "battery_excellent": 75.0,  # Excellent battery level
            "max_safe_altitude": 50.0,  # Maximum safe altitude for beginners
            "max_legal_altitude": 120.0,  # Legal altitude limit
            "min_takeoff_battery": 30.0,  # Minimum battery for takeoff
            "min_nav_altitude": 1.0,  # Minimum altitude for navigation
        }

    def analyze_command_safety(
        self, commands: List[Dict], telemetry: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Analyze command safety based on current telemetry.

        Returns:
            (is_safe, warnings, suggestions)
        """
        warnings = []
        suggestions = []
        is_safe = True

        # Extract telemetry safely
        battery_pct = telemetry.get('battery', {}).get('remaining_percent', 100)
        armed = telemetry.get('armed', False)
        connected = telemetry.get('connected', True)
        flight_mode = telemetry.get('flight_mode', 'UNKNOWN')
        altitude_rel = telemetry.get('position', {}).get('relative_altitude', 0)

        for cmd in commands:
            cmd_name = cmd.get('name', '').lower()
            params = cmd.get('params', {})

            # Takeoff safety checks
            if cmd_name == 'takeoff':
                if (
                    isinstance(battery_pct, (int, float))
                    and battery_pct < self.safety_rules["min_takeoff_battery"]
                ):
                    warnings.append(
                        f"🔋 Battery at {battery_pct:.0f}% - Recommended minimum {self.safety_rules['min_takeoff_battery']:.0f}% for takeoff"
                    )
                    suggestions.append("Consider charging battery before flight")

                takeoff_alt = params.get('altitude', 0)
                if takeoff_alt > self.safety_rules["max_safe_altitude"]:
                    warnings.append(
                        f"⚠️ Takeoff altitude {takeoff_alt}m exceeds safe beginner limit ({self.safety_rules['max_safe_altitude']}m)"
                    )
                    suggestions.append(
                        f"Consider starting with {self.safety_rules['max_safe_altitude']}m or lower"
                    )

                if takeoff_alt > self.safety_rules["max_legal_altitude"]:
                    warnings.append(
                        f"🚨 ILLEGAL: Altitude {takeoff_alt}m exceeds legal limit ({self.safety_rules['max_legal_altitude']}m)"
                    )
                    is_safe = False
                    suggestions.append(
                        f"Reduce altitude to {self.safety_rules['max_legal_altitude']}m or lower"
                    )

            # Navigation safety checks
            elif cmd_name == 'goto':
                if (
                    isinstance(altitude_rel, (int, float))
                    and altitude_rel < self.safety_rules["min_nav_altitude"]
                ):
                    warnings.append(
                        "🛬 Drone appears to be on ground - takeoff required before navigation"
                    )
                    suggestions.append("Execute takeoff command first")

                if (
                    isinstance(battery_pct, (int, float))
                    and battery_pct < self.safety_rules["battery_min_flight"]
                ):
                    warnings.append(
                        f"🔋 Battery at {battery_pct:.0f}% - Too low for navigation ({self.safety_rules['battery_min_flight']:.0f}% minimum)"
                    )
                    is_safe = False
                    suggestions.append("Land immediately and charge battery")

            # Battery critical check for all flight commands
            if cmd_name in ['takeoff', 'goto'] and isinstance(battery_pct, (int, float)):
                if battery_pct < self.safety_rules["battery_critical"]:
                    warnings.append(
                        f"🚨 CRITICAL: Battery at {battery_pct:.0f}% - Emergency landing required"
                    )
                    is_safe = False
                    suggestions.append("Execute immediate emergency landing")

        return is_safe, warnings, suggestions

    def format_safety_assessment(
        self, is_safe: bool, warnings: List[str], suggestions: List[str]
    ) -> str:
        """Format safety assessment for LLM response."""

        if not warnings:
            return "✅ **SAFETY CHECK**: All systems normal, command appears safe to execute."

        assessment = f"{'⚠️ **SAFETY REVIEW**' if is_safe else '🚨 **SAFETY ALERT**'}:\n\n"

        if warnings:
            assessment += "**Warnings:**\n"
            for warning in warnings:
                assessment += f"• {warning}\n"
            assessment += "\n"

        if suggestions:
            assessment += "**Recommendations:**\n"
            for suggestion in suggestions:
                assessment += f"• {suggestion}\n"
            assessment += "\n"

        if not is_safe:
            assessment += "🛑 **Command execution blocked for safety reasons.**\n"
        else:
            assessment += "✅ **Proceeding with caution - review warnings above.**\n"

        return assessment


class EnhancedLLMController:
    """Enhanced LLM controller with always-on telemetry and safety expert."""

    def __init__(self):
        """Initialize enhanced LLM controller."""
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.error("No API key found! Set OPENROUTER_API_KEY or OPENAI_API_KEY")
            self.client = None
            return

        # Initialize components
        base_url = (
            "https://openrouter.ai/api/v1"
            if os.getenv("OPENROUTER_API_KEY")
            else "https://api.openai.com/v1"
        )
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

        self.model = os.getenv("LLM_MODEL", "anthropic/claude-3-sonnet")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

        # Initialize telemetry and safety systems
        self.telemetry_manager = TelemetryManager()
        self.drone_expert = DroneExpert()

        logger.info(f"Enhanced LLM Controller initialized with model: {self.model}")

    async def process_command_with_telemetry(
        self, user_input: str, target_drone: int = 1
    ) -> Dict[str, Any]:
        """Process command with always-on telemetry and safety review."""

        if not self.client:
            return {
                "success": False,
                "error": "LLM not configured. Please set OPENROUTER_API_KEY or OPENAI_API_KEY",
                "commands": [],
            }

        try:
            # 1. Always fetch live telemetry first
            logger.info("Fetching live telemetry for LLM context...")
            telemetry = await self.telemetry_manager.get_live_telemetry(target_drone)

            # 2. Create expert system prompt with telemetry
            system_prompt = self._create_expert_prompt_with_telemetry(telemetry)

            # 3. Process with LLM
            logger.info(f"Processing command with enhanced LLM: {user_input}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                temperature=self.temperature,
                max_tokens=1000,
                extra_headers={
                    "HTTP-Referer": os.getenv("SITE_URL", ""),
                    "X-Title": os.getenv("SITE_NAME", "DroneSphere Enhanced"),
                },
            )

            content = response.choices[0].message.content
            logger.info(f"LLM response received: {content[:100]}...")

            # 4. Parse commands from LLM response
            commands = self._parse_llm_response(content)

            # 5. Safety expert review
            if commands:
                is_safe, warnings, suggestions = self.drone_expert.analyze_command_safety(
                    commands, telemetry
                )
                safety_assessment = self.drone_expert.format_safety_assessment(
                    is_safe, warnings, suggestions
                )

                return {
                    "success": is_safe,  # Only succeed if safe
                    "commands": commands if is_safe else [],
                    "explanation": content,
                    "safety_assessment": safety_assessment,
                    "telemetry_data": telemetry,
                    "warnings": warnings,
                    "blocked_for_safety": not is_safe,
                }
            else:
                return {
                    "success": True,
                    "commands": [],
                    "explanation": content,
                    "telemetry_data": telemetry,
                }

        except Exception as e:
            logger.error(f"Enhanced LLM processing error: {e}")
            return {"success": False, "error": f"LLM processing error: {str(e)}", "commands": []}

    def _create_expert_prompt_with_telemetry(self, telemetry: Dict[str, Any]) -> str:
        """Create expert system prompt with live telemetry data."""

        telemetry_section = self.telemetry_manager.format_for_llm(telemetry)

        return f"""You are a professional drone pilot and safety expert with years of experience. You have complete situational awareness through live telemetry data.

{telemetry_section}

🎯 YOUR ROLE AS EXPERT DRONE PILOT:
• Analyze live telemetry data to provide accurate, real-time information
• Review all commands for safety before recommending execution
• Provide technical expertise and professional advice
• Always prioritize safety and responsible flying
• Give precise answers to technical questions using live data

📋 AVAILABLE COMMANDS:
1. takeoff: {{"name": "takeoff", "params": {{"altitude": 1-50}}}}
2. land: {{"name": "land", "params": {{}}}}
3. goto (GPS): {{"name": "goto", "params": {{"latitude": float, "longitude": float, "altitude": float}}}}
4. goto (NED): {{"name": "goto", "params": {{"north": float, "east": float, "down": float}}}}
5. wait: {{"name": "wait", "params": {{"duration": 0.1-300, "message": "optional"}}}}
6. rtl: {{"name": "rtl", "params": {{}}}}

🌍 MULTI-LANGUAGE SUPPORT:
- English: "take off to 15 meters", "what's my battery voltage?", "where am I?"
- Persian: "بلند شو به 15 متر", "ولتاژ باتری چنده؟", "کجام؟"
- Spanish: "despegar a 15 metros", "¿cuál es el voltaje de la batería?"

⚠️ SAFETY PROTOCOLS:
• Review battery levels before flight operations
• Check GPS lock before navigation commands
• Verify drone is airborne before goto commands
• Alert about dangerous altitude or battery levels
• Block unsafe commands and suggest alternatives

📊 WHEN ANSWERING TECHNICAL QUESTIONS:
• Use LIVE telemetry data from above section
• Be specific and precise with numbers
• Explain what the values mean in context
• Provide professional recommendations

🎯 RESPONSE FORMAT:
For commands: Return JSON array: [{{"name": "command", "params": {{"param": value}}}}]
For questions: Provide detailed answers using live telemetry data
For status: Use real-time data from telemetry section above

IMPORTANT:
- You have live access to all drone data - use it to provide expert-level responses!
- For status/technical questions, return empty array [] for commands and answer using telemetry
- Always be precise with technical data from telemetry section
"""

    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract command JSON."""
        try:
            cleaned = llm_response.strip()

            # Remove markdown formatting
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Find JSON array
            start_bracket = cleaned.find('[')
            end_bracket = cleaned.rfind(']')

            if start_bracket != -1 and end_bracket != -1:
                json_str = cleaned[start_bracket : end_bracket + 1]
                commands = json.loads(json_str)

                if isinstance(commands, dict):
                    commands = [commands]

                # Validate commands
                valid_commands = []
                for cmd in commands:
                    if isinstance(cmd, dict) and "name" in cmd and "params" in cmd:
                        valid_commands.append(cmd)

                return valid_commands

            return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return []

    async def _get_drone_status(self) -> Dict[str, Any]:
        """Get current drone status from DroneSphere."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8002/fleet/health", timeout=10.0)
                if response.status_code == 200:
                    fleet_health = response.json()
                    return fleet_health.get("drones", {}).get("1", {})
                else:
                    return {"error": f"Status check failed: {response.status_code}"}
        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}


class EnhancedLLMWebBridge:
    """Enhanced LLM-powered web bridge with always-on telemetry."""

    def __init__(self):
        """Initialize enhanced web bridge."""
        self.app = FastAPI(
            title="DroneSphere Enhanced LLM Interface",
            description="Professional drone control with always-on telemetry and safety expert",
            version="3.0.0",
        )
        self.llm_controller = EnhancedLLMController()
        self.setup_routes()

    def setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def web_interface():
            """Serve the enhanced web interface."""
            return HTML_INTERFACE

        @self.app.post("/chat")
        async def process_chat(message: ChatMessage):
            """Process natural language chat message with enhanced LLM and telemetry."""
            try:
                # Process with enhanced telemetry and safety system
                result = await self.llm_controller.process_command_with_telemetry(
                    message.message, message.target_drone
                )

                if result["success"] and result.get("commands"):
                    # Execute commands if safe
                    execution_result = await self._execute_commands(
                        result["commands"], message.target_drone
                    )

                    if execution_result["success"]:
                        response_msg = f"✅ **Expert Analysis & Execution Complete**\n\n"
                        if "safety_assessment" in result:
                            response_msg += result["safety_assessment"] + "\n"
                        response_msg += (
                            f"**Commands**: {len(result['commands'])} executed successfully\n"
                        )
                        response_msg += (
                            f"**LLM Understanding**: Parsed and validated your request\n"
                        )

                        # Add command details
                        for i, cmd in enumerate(result["commands"], 1):
                            response_msg += f"\n{i}. **{cmd['name']}**: {cmd['params']}"
                    else:
                        response_msg = f"❌ **Command Execution Failed**: {execution_result.get('error', 'Unknown error')}"
                        if "safety_assessment" in result:
                            response_msg += f"\n\n{result['safety_assessment']}"

                    return {
                        "success": execution_result["success"],
                        "message": response_msg,
                        "original_request": message.message,
                        "telemetry": result.get("telemetry_data", {}),
                    }

                elif result.get("blocked_for_safety"):
                    response_msg = f"🛑 **Safety System Active**\n\n"
                    response_msg += result.get(
                        "safety_assessment", "Command blocked for safety reasons"
                    )

                    return {
                        "success": False,
                        "message": response_msg,
                        "original_request": message.message,
                        "telemetry": result.get("telemetry_data", {}),
                    }

                else:
                    # Handle status questions or non-command responses using telemetry
                    response_msg = result.get("explanation", "No commands to execute")

                    return {
                        "success": True,
                        "message": response_msg,
                        "original_request": message.message,
                        "telemetry": result.get("telemetry_data", {}),
                    }

            except Exception as e:
                logger.error(f"Enhanced chat processing error: {e}")
                return {
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "original_request": message.message,
                }

        @self.app.get("/status/{drone_id}")
        async def get_drone_status(drone_id: int):
            """Get enhanced drone status with telemetry."""
            try:
                # Get both fleet status and telemetry
                drone_status = await self.llm_controller._get_drone_status()
                telemetry = await self.llm_controller.telemetry_manager.get_live_telemetry(drone_id)

                return {"status": drone_status, "telemetry": telemetry}
            except Exception as e:
                logger.error(f"Status check error: {e}")
                return {"status": {"error": str(e)}}

        @self.app.get("/telemetry/{drone_id}")
        async def get_telemetry(drone_id: int):
            """Get live telemetry data."""
            try:
                telemetry = await self.llm_controller.telemetry_manager.get_live_telemetry(drone_id)
                return telemetry
            except Exception as e:
                logger.error(f"Telemetry fetch error: {e}")
                return {"error": str(e)}

    async def _execute_commands(self, commands: List[Dict], target_drone: int) -> Dict[str, Any]:
        """Execute commands through DroneSphere."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8002/fleet/commands",
                    json={
                        "commands": commands,
                        "target_drone": target_drone,
                        "queue_mode": "override",
                    },
                    timeout=60.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": f"Server error: {response.status_code} - {response.text}",
                    }

        except Exception as e:
            return {"success": False, "error": f"Communication error: {str(e)}"}

    def run(self):
        """Run the enhanced LLM web bridge server."""
        import uvicorn

        logger.info("Starting DroneSphere Enhanced LLM Web Bridge...")
        logger.info("🌐 Web interface: http://localhost:3001")
        logger.info("🧠 Enhanced LLM Integration: ACTIVE")
        logger.info("📊 Always-On Telemetry: ACTIVE")
        logger.info("🛡️ Safety Expert System: ACTIVE")
        logger.info(f"🤖 Model: {self.llm_controller.model}")
        logger.info("🌍 Multi-language support: English, Persian, Spanish, French, German")

        uvicorn.run(self.app, host="0.0.0.0", port=3001, log_level="info")


# Enhanced HTML Interface with Premium UI/UX Design
HTML_INTERFACE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DroneSphere Pro - Advanced AI Flight Control</title>

    <!-- Font imports -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

    <!-- Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

    <style>
        /* CSS Variables for theming */
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --secondary: #8b5cf6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #0f172a;
            --dark-secondary: #1e293b;
            --dark-tertiary: #334155;
            --light: #f8fafc;
            --light-secondary: #f1f5f9;
            --light-tertiary: #e2e8f0;
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --text-light: #cbd5e1;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
            --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
            --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-dark: linear-gradient(135deg, #1a202c 0%, #2d3748 100%);
            --gradient-success: linear-gradient(135deg, #10b981 0%, #059669 100%);
            --gradient-danger: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%);
        }

        /* Dark mode variables */
        [data-theme="dark"] {
            --text-primary: #f8fafc;
            --text-secondary: #cbd5e1;
            --text-light: #64748b;
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-tertiary: #334155;
            --border-color: #334155;
        }

        [data-theme="light"] {
            --bg-primary: #ffffff;
            --bg-secondary: #f8fafc;
            --bg-tertiary: #f1f5f9;
            --border-color: #e2e8f0;
        }

        /* Global Styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
            transition: all 0.3s ease;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-dark);
        }

        /* Main Layout */
        .app-container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background: var(--bg-primary);
        }

        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            backdrop-filter: blur(10px);
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: var(--shadow);
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo {
            width: 48px;
            height: 48px;
            background: var(--gradient-primary);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            color: white;
            box-shadow: var(--shadow-lg);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .brand-name {
            font-size: 1.5rem;
            font-weight: 800;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .status-badges {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }

        .status-badge {
            padding: 0.5rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 0.875rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.3s ease;
            box-shadow: var(--shadow-sm);
        }

        .status-badge:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }

        .status-badge.active {
            background: var(--gradient-success);
            color: white;
            border-color: transparent;
        }

        .status-badge.warning {
            background: var(--gradient-danger);
            color: white;
            border-color: transparent;
        }

        .header-actions {
            display: flex;
            gap: 1rem;
            align-items: center;
        }

        .theme-toggle {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            font-size: 1.1rem;
        }

        .theme-toggle:hover {
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }

        /* Main Content Area */
        .main-content {
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 2rem;
            animation: fadeIn 0.5s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Telemetry Panel */
        .telemetry-panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.5rem;
            height: fit-content;
            box-shadow: var(--shadow-lg);
            position: sticky;
            top: 100px;
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
        }

        .panel-title {
            font-size: 1.25rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .telemetry-grid {
            display: grid;
            gap: 1rem;
        }

        .telemetry-item {
            background: var(--bg-tertiary);
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .telemetry-item:hover {
            transform: translateX(4px);
            box-shadow: var(--shadow);
            border-color: var(--primary);
        }

        .telemetry-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .telemetry-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }

        .telemetry-unit {
            font-size: 0.875rem;
            color: var(--text-secondary);
            font-weight: 400;
        }

        /* Progress Bars */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--bg-primary);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 0.5rem;
        }

        .progress-fill {
            height: 100%;
            background: var(--gradient-success);
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        .progress-fill.warning {
            background: var(--gradient-danger);
        }

        /* 3D Map Visualization */
        .map-container {
            background: var(--bg-tertiary);
            border-radius: 12px;
            padding: 1rem;
            margin-top: 1rem;
            height: 200px;
            position: relative;
            overflow: hidden;
            border: 1px solid var(--border-color);
        }

        .map-placeholder {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(45deg, var(--primary) 25%, transparent 25%, transparent 75%, var(--primary) 75%, var(--primary)),
                        linear-gradient(45deg, var(--primary) 25%, transparent 25%, transparent 75%, var(--primary) 75%, var(--primary));
            background-size: 30px 30px;
            background-position: 0 0, 15px 15px;
            opacity: 0.1;
            position: relative;
        }

        .drone-icon {
            position: absolute;
            width: 40px;
            height: 40px;
            background: var(--primary);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
            box-shadow: var(--shadow-xl);
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-10px) rotate(180deg); }
        }

        /* Chat Section */
        .chat-section {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            height: calc(100vh - 200px);
            box-shadow: var(--shadow-lg);
        }

        .chat-header {
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 1rem;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1rem 0;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .message {
            max-width: 80%;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .message.user {
            align-self: flex-end;
            animation: slideInRight 0.3s ease-out;
        }

        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .message-bubble {
            padding: 1rem 1.5rem;
            border-radius: 16px;
            position: relative;
            box-shadow: var(--shadow);
        }

        .message.user .message-bubble {
            background: var(--gradient-primary);
            color: white;
            border-bottom-right-radius: 4px;
        }

        .message.assistant .message-bubble {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-bottom-left-radius: 4px;
        }

        .message-time {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .message.user .message-time {
            text-align: right;
            color: rgba(255, 255, 255, 0.8);
        }

        /* Chat Input */
        .chat-input-container {
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }

        .chat-input-wrapper {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
        }

        .chat-input {
            flex: 1;
            background: var(--bg-tertiary);
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            font-size: 1rem;
            font-family: inherit;
            resize: none;
            min-height: 56px;
            max-height: 120px;
            transition: all 0.3s ease;
            color: var(--text-primary);
        }

        .chat-input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }

        .send-button {
            width: 56px;
            height: 56px;
            border-radius: 12px;
            background: var(--gradient-primary);
            color: white;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            transition: all 0.3s ease;
            box-shadow: var(--shadow);
        }

        .send-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: var(--shadow-xl);
        }

        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            background: var(--text-secondary);
        }

        /* Quick Commands */
        .quick-commands {
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border-color);
        }

        .quick-commands-header {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
            font-weight: 600;
        }

        .commands-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.5rem;
        }

        .command-chip {
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .command-chip:hover {
            background: var(--primary);
            color: white;
            transform: translateY(-2px);
            box-shadow: var(--shadow);
            border-color: transparent;
        }

        .command-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-primary);
            border-radius: 4px;
            font-size: 0.75rem;
        }

        .command-chip:hover .command-icon {
            background: rgba(255, 255, 255, 0.2);
        }

        /* Loading Animation */
        .typing-indicator {
            display: flex;
            gap: 0.25rem;
            padding: 1rem;
        }

        .typing-dot {
            width: 8px;
            height: 8px;
            background: var(--text-secondary);
            border-radius: 50%;
            animation: typing 1.4s ease-in-out infinite;
        }

        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
            30% { transform: translateY(-10px); opacity: 1; }
        }

        /* Responsive Design */
        @media (max-width: 1024px) {
            .main-content {
                grid-template-columns: 1fr;
            }

            .telemetry-panel {
                position: relative;
                top: 0;
            }

            .chat-section {
                height: auto;
                min-height: 600px;
            }
        }

        @media (max-width: 768px) {
            .header-content {
                padding: 1rem;
            }

            .main-content {
                padding: 1rem;
                gap: 1rem;
            }

            .status-badges {
                display: none;
            }

            .brand-name {
                font-size: 1.25rem;
            }

            .message {
                max-width: 90%;
            }

            .commands-grid {
                grid-template-columns: 1fr;
            }
        }

        /* Markdown Styles */
        .message-content {
            line-height: 1.6;
        }

        .message-content strong {
            font-weight: 600;
            color: var(--primary);
        }

        .message.user .message-content strong {
            color: white;
            font-weight: 700;
        }

        .message-content code {
            background: var(--bg-primary);
            padding: 0.125rem 0.375rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875em;
        }

        .message.user .message-content code {
            background: rgba(255, 255, 255, 0.2);
        }

        .message-content ul, .message-content ol {
            margin: 0.5rem 0 0.5rem 1.5rem;
        }

        .message-content li {
            margin: 0.25rem 0;
        }

        /* Safety Indicators */
        .safety-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.75rem;
            background: var(--bg-tertiary);
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0.5rem 0;
        }

        .safety-indicator.safe {
            background: var(--gradient-success);
            color: white;
        }

        .safety-indicator.warning {
            background: var(--gradient-danger);
            color: white;
        }

        /* Notification Toast */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem 1.5rem;
            box-shadow: var(--shadow-2xl);
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideUp 0.3s ease-out;
            z-index: 2000;
        }

        @keyframes slideUp {
            from { transform: translateY(100px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .toast.success {
            border-left: 4px solid var(--success);
        }

        .toast.error {
            border-left: 4px solid var(--danger);
        }

        .toast-icon {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }

        .toast.success .toast-icon {
            background: var(--success);
            color: white;
        }

        .toast.error .toast-icon {
            background: var(--danger);
            color: white;
        }
    </style>
</head>
<body data-theme="dark">
    <div class="app-container">
        <!-- Header -->
        <header class="header">
            <div class="header-content">
                <div class="logo-section">
                    <div class="logo">
                        <i class="fas fa-helicopter"></i>
                    </div>
                    <h1 class="brand-name">DroneSphere Pro</h1>
                </div>

                <div class="status-badges">
                    <div class="status-badge active">
                        <i class="fas fa-brain"></i>
                        <span>AI Expert</span>
                    </div>
                    <div class="status-badge active">
                        <i class="fas fa-satellite-dish"></i>
                        <span>Live Telemetry</span>
                    </div>
                    <div class="status-badge active">
                        <i class="fas fa-shield-alt"></i>
                        <span>Safety Active</span>
                    </div>
                </div>

                <div class="header-actions">
                    <button class="theme-toggle" onclick="toggleTheme()">
                        <i class="fas fa-moon" id="themeIcon"></i>
                    </button>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="main-content">
            <!-- Telemetry Panel -->
            <aside class="telemetry-panel">
                <div class="panel-header">
                    <h2 class="panel-title">
                        <i class="fas fa-chart-line"></i>
                        Live Telemetry
                    </h2>
                    <div class="status-badge active" style="font-size: 0.75rem;">
                        <i class="fas fa-circle"></i>
                        Connected
                    </div>
                </div>

                <div class="telemetry-grid">
                    <!-- Battery -->
                    <div class="telemetry-item">
                        <div class="telemetry-label">
                            <i class="fas fa-battery-three-quarters"></i>
                            Battery Level
                        </div>
                        <div class="telemetry-value">
                            <span id="batteryValue">--</span><span class="telemetry-unit">%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" id="batteryProgress" style="width: 0%"></div>
                        </div>
                    </div>

                    <!-- Altitude -->
                    <div class="telemetry-item">
                        <div class="telemetry-label">
                            <i class="fas fa-arrows-alt-v"></i>
                            Altitude (MSL)
                        </div>
                        <div class="telemetry-value">
                            <span id="altitudeValue">--</span><span class="telemetry-unit">m</span>
                        </div>
                    </div>

                    <!-- GPS -->
                    <div class="telemetry-item">
                        <div class="telemetry-label">
                            <i class="fas fa-map-marker-alt"></i>
                            GPS Position
                        </div>
                        <div class="telemetry-value" style="font-size: 1rem;">
                            <div>LAT: <span id="latValue">--</span>°</div>
                            <div>LON: <span id="lonValue">--</span>°</div>
                        </div>
                    </div>

                    <!-- Voltage -->
                    <div class="telemetry-item">
                        <div class="telemetry-label">
                            <i class="fas fa-bolt"></i>
                            Voltage
                        </div>
                        <div class="telemetry-value">
                            <span id="voltageValue">--</span><span class="telemetry-unit">V</span>
                        </div>
                    </div>

                    <!-- Flight Mode -->
                    <div class="telemetry-item">
                        <div class="telemetry-label">
                            <i class="fas fa-plane"></i>
                            Flight Mode
                        </div>
                        <div class="telemetry-value" style="font-size: 1rem;">
                            <span id="flightModeValue">--</span>
                        </div>
                    </div>
                </div>

                <!-- Map Visualization -->
                <div class="map-container">
                    <div class="map-placeholder">
                        <div class="drone-icon" id="droneIcon">
                            <i class="fas fa-helicopter"></i>
                        </div>
                    </div>
                </div>
            </aside>

            <!-- Chat Section -->
            <section class="chat-section">
                <div class="chat-header">
                    <h2 class="panel-title">
                        <i class="fas fa-comments"></i>
                        AI Flight Assistant
                    </h2>
                </div>

                <div class="chat-messages" id="chatMessages">
                    <div class="message assistant">
                        <div class="message-bubble">
                            <div class="message-content">
                                <strong>Welcome to DroneSphere Pro!</strong> 🚁<br><br>
                                I'm your AI flight expert with real-time telemetry awareness. I can help you with:
                                <ul>
                                    <li>Flight commands and navigation</li>
                                    <li>Technical questions about your drone</li>
                                    <li>Safety assessments and recommendations</li>
                                    <li>Multi-language support (English, Persian, Spanish)</li>
                                </ul>
                                How can I assist you today?
                            </div>
                        </div>
                        <div class="message-time">
                            <i class="far fa-clock"></i>
                            <span>${new Date().toLocaleTimeString()}</span>
                        </div>
                    </div>
                </div>

                <div class="chat-input-container">
                    <div class="chat-input-wrapper">
                        <textarea
                            class="chat-input"
                            id="chatInput"
                            placeholder="Type your command or question..."
                            rows="1"
                            onkeydown="handleKeyPress(event)"
                            oninput="autoResize(this)"
                        ></textarea>
                        <button class="send-button" id="sendButton" onclick="sendMessage()">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    </div>

                    <div class="quick-commands">
                        <div class="quick-commands-header">Quick Commands</div>
                        <div class="commands-grid">
                            <div class="command-chip" onclick="setCommand('What is my battery level?')">
                                <div class="command-icon">🔋</div>
                                <span>Battery Status</span>
                            </div>
                            <div class="command-chip" onclick="setCommand('Take off to 15 meters')">
                                <div class="command-icon">🚁</div>
                                <span>Take Off</span>
                            </div>
                            <div class="command-chip" onclick="setCommand('Where am I?')">
                                <div class="command-icon">📍</div>
                                <span>GPS Location</span>
                            </div>
                            <div class="command-chip" onclick="setCommand('Land safely')">
                                <div class="command-icon">🛬</div>
                                <span>Land</span>
                            </div>
                            <div class="command-chip" onclick="setCommand('Is it safe to fly?')">
                                <div class="command-icon">🛡️</div>
                                <span>Safety Check</span>
                            </div>
                            <div class="command-chip" onclick="setCommand('Return to home')">
                                <div class="command-icon">🏠</div>
                                <span>RTL</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    </div>

    <script>
        // Theme Management
        const theme = localStorage.getItem('theme') || 'dark';
        document.body.setAttribute('data-theme', theme);
        updateThemeIcon();

        function toggleTheme() {
            const currentTheme = document.body.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon();
            showToast('Theme changed to ' + newTheme + ' mode', 'success');
        }

        function updateThemeIcon() {
            const theme = document.body.getAttribute('data-theme');
            const icon = document.getElementById('themeIcon');
            icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
        }

        // Chat functionality
        const chatMessages = document.getElementById('chatMessages');
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function setCommand(command) {
            chatInput.value = command;
            chatInput.focus();
            autoResize(chatInput);
        }

        async function sendMessage() {
            const message = chatInput.value.trim();
            if (!message) return;

            // Add user message
            addMessage(message, 'user');

            // Clear input
            chatInput.value = '';
            autoResize(chatInput);

            // Disable send button and show loading
            sendButton.disabled = true;
            addTypingIndicator();

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message, target_drone: 1 })
                });

                const result = await response.json();

                removeTypingIndicator();

                // Add assistant response
                addMessage(result.message, 'assistant', result.success);

                // Update telemetry if available
                if (result.telemetry) {
                    updateTelemetry(result.telemetry);
                }

                // Show toast notification
                if (result.success) {
                    showToast('Command processed successfully', 'success');
                } else if (result.blocked_for_safety) {
                    showToast('Command blocked for safety reasons', 'error');
                }

            } catch (error) {
                removeTypingIndicator();
                addMessage('Connection error: ' + error.message, 'assistant', false);
                showToast('Connection error', 'error');
            } finally {
                sendButton.disabled = false;
            }
        }

        function addMessage(content, type, success = true) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + type;

            // Convert markdown-style formatting
            content = formatMessage(content);

            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="message-content">${content}</div>
                </div>
                <div class="message-time">
                    <i class="far fa-clock"></i>
                    <span>${new Date().toLocaleTimeString()}</span>
                </div>
            `;

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function formatMessage(content) {
            // Basic markdown formatting
            content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            content = content.replace(/\n/g, '<br>');
            content = content.replace(/• /g, '<li>');

            // Wrap lists
            if (content.includes('<li>')) {
                content = content.replace(/(<li>.*?)(<br>|$)/g, '<ul>$1</ul>');
            }

            // Add safety indicators
            if (content.includes('SAFETY CHECK') && content.includes('✅')) {
                content += '<div class="safety-indicator safe"><i class="fas fa-check-circle"></i> Safe to Execute</div>';
            } else if (content.includes('SAFETY ALERT') || content.includes('🚨')) {
                content += '<div class="safety-indicator warning"><i class="fas fa-exclamation-triangle"></i> Safety Warning</div>';
            }

            return content;
        }

        function addTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant typing';
            typingDiv.id = 'typingIndicator';
            typingDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function removeTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        // Telemetry Updates
        function updateTelemetry(telemetry) {
            // Battery
            const battery = telemetry.battery?.remaining_percent;
            if (battery !== undefined) {
                document.getElementById('batteryValue').textContent = Math.round(battery);
                const batteryProgress = document.getElementById('batteryProgress');
                batteryProgress.style.width = battery + '%';
                batteryProgress.className = battery < 20 ? 'progress-fill warning' : 'progress-fill';
            }

            // Position
            const position = telemetry.position;
            if (position) {
                if (position.latitude) {
                    document.getElementById('latValue').textContent = position.latitude.toFixed(6);
                }
                if (position.longitude) {
                    document.getElementById('lonValue').textContent = position.longitude.toFixed(6);
                }
                if (position.altitude !== undefined) {
                    document.getElementById('altitudeValue').textContent = position.altitude.toFixed(1);
                }
            }

            // Voltage
            const voltage = telemetry.battery?.voltage;
            if (voltage !== undefined) {
                document.getElementById('voltageValue').textContent = voltage.toFixed(1);
            }

            // Flight Mode
            if (telemetry.flight_mode) {
                document.getElementById('flightModeValue').textContent = telemetry.flight_mode;
            }

            // Update drone icon position (simulated)
            const droneIcon = document.getElementById('droneIcon');
            if (position && position.relative_altitude > 0) {
                const altitude = Math.min(position.relative_altitude / 50, 1); // Normalize to 0-1
                droneIcon.style.bottom = (20 + altitude * 60) + '%';
            }
        }

        // Toast Notifications
        function showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = 'toast ' + type;
            toast.innerHTML = `
                <div class="toast-icon">
                    <i class="fas ${type === 'success' ? 'fa-check' : 'fa-exclamation'}"></i>
                </div>
                <div>${message}</div>
            `;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.style.animation = 'slideUp 0.3s ease-out reverse';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }

        // Periodic telemetry updates
        async function fetchTelemetry() {
            try {
                const response = await fetch('/telemetry/1');
                if (response.ok) {
                    const telemetry = await response.json();
                    updateTelemetry(telemetry);
                }
            } catch (error) {
                console.error('Telemetry fetch error:', error);
            }
        }

        // Update telemetry every 2 seconds
        setInterval(fetchTelemetry, 2000);

        // Initial telemetry fetch
        fetchTelemetry();

        // Focus on input on load
        chatInput.focus();
    </script>
</body>
</html>"""


def main():
    """Main entry point for enhanced LLM web bridge."""
    bridge = EnhancedLLMWebBridge()
    bridge.run()


if __name__ == "__main__":
    main()
