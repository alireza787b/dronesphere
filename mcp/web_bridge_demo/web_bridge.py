"""
Enhanced LLM-Powered Web Bridge for DroneSphere
Path: web_bridge_demo/web_bridge.py
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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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
            "battery_min_flight": 20.0,
            "battery_critical": 15.0,
            "battery_excellent": 75.0,
            "max_safe_altitude": 50.0,
            "max_legal_altitude": 120.0,
            "min_takeoff_battery": 30.0,
            "min_nav_altitude": 1.0,
        }

    def analyze_command_safety(
        self, commands: List[Dict], telemetry: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """Analyze command safety based on current telemetry."""
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
                    "success": is_safe,
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

        # Add CORS middleware for cross-origin requests
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.llm_controller = EnhancedLLMController()
        self.setup_routes()

    def setup_routes(self):
        """Setup FastAPI routes."""

        # Mount static files
        self.app.mount("/static", StaticFiles(directory="static"), name="static")

        @self.app.get("/", response_class=HTMLResponse)
        async def serve_index():
            """Serve the main index.html file."""
            return FileResponse('static/index.html')

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

        @self.app.get("/api/drone-telemetry")
        async def get_drone_telemetry_proxy():
            """Proxy endpoint for direct drone telemetry to avoid CORS issues."""
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8001/telemetry", timeout=5.0)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return {"error": f"Drone telemetry error: {response.status_code}"}
            except Exception as e:
                logger.error(f"Drone telemetry proxy error: {e}")
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


def main():
    """Main entry point for enhanced LLM web bridge."""
    bridge = EnhancedLLMWebBridge()
    bridge.run()


if __name__ == "__main__":
    main()
