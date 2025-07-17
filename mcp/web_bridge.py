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
                    }

                else:
                    # Handle status questions or non-command responses using telemetry
                    response_msg = result.get("explanation", "No commands to execute")

                    return {
                        "success": True,
                        "message": response_msg,
                        "original_request": message.message,
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


# Enhanced HTML Interface with Telemetry Features
HTML_INTERFACE = """<!DOCTYPE html>
<html>
<head>
    <title>DroneSphere - Enhanced AI Drone Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; color: #333; }
        .header h1 { color: #667eea; margin-bottom: 10px; font-size: 2.5em; }
        .ai-badge { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; display: inline-block; margin-bottom: 10px; }
        .telemetry-badge { background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; display: inline-block; margin-left: 10px; }
        .status-panel { background: linear-gradient(45deg, #f8f9fa, #e9ecef); padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #667eea; }
        .chat-container { margin-bottom: 30px; }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        .input-group input { flex: 1; padding: 15px; font-size: 16px; border: 2px solid #ddd; border-radius: 10px; transition: border-color 0.3s; }
        .input-group input:focus { border-color: #667eea; outline: none; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .input-group button { padding: 15px 25px; background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; border-radius: 10px; cursor: pointer; font-size: 16px; font-weight: bold; transition: transform 0.2s; }
        .input-group button:hover { transform: translateY(-2px); }
        .input-group button:disabled { background: #ccc; transform: none; cursor: not-allowed; }
        .chat-history { min-height: 400px; max-height: 600px; overflow-y: auto; border: 2px solid #eee; padding: 25px; margin-bottom: 20px; background: #fafafa; border-radius: 10px; }
        .message { margin-bottom: 20px; padding: 15px; border-radius: 12px; animation: fadeIn 0.3s ease-in; }
        .user-message { background: linear-gradient(45deg, #e3f2fd, #bbdefb); margin-left: 10%; border-left: 4px solid #2196f3; }
        .bot-message { background: linear-gradient(45deg, #f1f8e9, #c8e6c9); margin-right: 10%; border-left: 4px solid #4caf50; }
        .error-message { background: linear-gradient(45deg, #ffebee, #ffcdd2); margin-right: 10%; border-left: 4px solid #f44336; }
        .examples { background: linear-gradient(45deg, #e8f4f8, #d1ecf1); padding: 25px; border-radius: 10px; }
        .example { background: white; padding: 12px; margin: 10px 0; border-radius: 8px; cursor: pointer; border: 2px solid transparent; transition: all 0.3s; }
        .example:hover { background: #f0f8ff; border-color: #667eea; transform: translateY(-2px); }
        .language-examples { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-top: 15px; }
        .lang-group { background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .timestamp { font-size: 11px; color: #888; margin-top: 8px; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚁 DroneSphere Enhanced</h1>
            <div class="ai-badge">🧠 AI Expert</div>
            <div class="telemetry-badge">📊 Live Telemetry</div>
            <p>Professional drone control with real-time telemetry and safety expert oversight</p>
        </div>

        <div class="status-panel">
            <div id="systemStatus">
                <strong>🤖 Enhanced AI System:</strong> <span id="statusText">Initializing...</span>
            </div>
        </div>

        <div class="chat-container">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Ask about telemetry: 'What's my battery voltage?' or command: 'take off to 15 meters'" />
                <button id="sendButton" onclick="sendMessage()">Send</button>
            </div>

            <div id="chatHistory" class="chat-history">
                <div class="bot-message">
                    <strong>🤖 DroneSphere Expert:</strong> Ready with live telemetry awareness! I can answer technical questions and provide expert safety review.
                    <div class="timestamp">Enhanced AI • Live telemetry • Safety expert active</div>
                </div>
            </div>
        </div>

        <div class="examples">
            <h3>💡 Enhanced Commands & Questions:</h3>

            <div class="language-examples">
                <div class="lang-group">
                    <h4>🔋 Technical Questions</h4>
                    <div class="example" onclick="setCommand('What is my battery voltage?')">⚡ "What is my battery voltage?"</div>
                    <div class="example" onclick="setCommand('Where am I exactly?')">📍 "Where am I exactly?"</div>
                    <div class="example" onclick="setCommand('What is my current altitude?')">📏 "What is my current altitude?"</div>
                </div>

                <div class="lang-group">
                    <h4>🇮🇷 Persian Technical</h4>
                    <div class="example" onclick="setCommand('ولتاژ باتری چنده؟')">⚡ "ولتاژ باتری چنده؟"</div>
                    <div class="example" onclick="setCommand('کجام الان؟')">📍 "کجام الان؟"</div>
                    <div class="example" onclick="setCommand('ارتفاعم چقدره؟')">📏 "ارتفاعم چقدره؟"</div>
                </div>

                <div class="lang-group">
                    <h4>🛡️ Safety Commands</h4>
                    <div class="example" onclick="setCommand('take off to 200 meters')">⚠️ Test safety limits</div>
                    <div class="example" onclick="setCommand('Is it safe to fly?')">🔍 "Is it safe to fly?"</div>
                </div>

                <div class="lang-group">
                    <h4>🧠 Expert Commands</h4>
                    <div class="example" onclick="setCommand('take off to 15m, wait 3s, then land')">⚡ Multi-step missions</div>
                    <div class="example" onclick="setCommand('fly to coordinates 47.398, 8.546')">🗺️ GPS navigation</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let chatHistory = document.getElementById('chatHistory');
        let messageInput = document.getElementById('messageInput');
        let sendButton = document.getElementById('sendButton');

        function addMessage(content, type = 'bot') {
            let messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            messageDiv.innerHTML = content + `<div class="timestamp">${new Date().toLocaleTimeString()}</div>`;
            chatHistory.appendChild(messageDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }

        function setCommand(command) {
            messageInput.value = command;
            messageInput.focus();
        }

        function setLoading(loading) {
            sendButton.disabled = loading;
            sendButton.textContent = loading ? '🤖 Expert Analyzing...' : 'Send';
        }

        async function sendMessage() {
            let message = messageInput.value.trim();
            if (!message) return;

            addMessage(`<strong>👤 You:</strong> ${message}`, 'user');
            messageInput.value = '';
            setLoading(true);

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message, target_drone: 1 })
                });

                const result = await response.json();

                if (result.success) {
                    addMessage(`<strong>🤖 Expert:</strong> ${result.message}`, 'bot');
                } else {
                    addMessage(`<strong>🤖 Expert:</strong> ${result.message}`, 'error');
                }

            } catch (error) {
                addMessage(`<strong>🤖 Expert:</strong> Connection error: ${error.message}`, 'error');
            } finally {
                setLoading(false);
            }
        }

        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !sendButton.disabled) {
                sendMessage();
            }
        });

        // Update status
        function updateStatus() {
            document.getElementById('statusText').innerHTML = `
                <span style="color: #4caf50;">✅ Expert AI</span> |
                <span style="color: #2196f3;">📊 Live Telemetry</span> |
                <span style="color: #ff9800;">🛡️ Safety Active</span>
            `;
        }

        updateStatus();
    </script>
</body>
</html>"""


def main():
    """Main entry point for enhanced LLM web bridge."""
    bridge = EnhancedLLMWebBridge()
    bridge.run()


if __name__ == "__main__":
    main()
