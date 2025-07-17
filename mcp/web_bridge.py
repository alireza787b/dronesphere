"""LLM-Powered Web Bridge for DroneSphere

This version uses real LLM APIs (OpenRouter/OpenAI) for intelligent command parsing.
Supports multiple languages, complex commands, and natural conversation.

Path: mcp/web_bridge_llm.py
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

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
logger = logging.getLogger("dronesphere-llm-bridge")


class ChatMessage(BaseModel):
    """Chat message from user."""

    message: str
    target_drone: int = 1


class LLMDroneController:
    """LLM-powered drone command controller."""

    def __init__(self):
        """Initialize LLM client."""
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            logger.error("No API key found! Set OPENROUTER_API_KEY or OPENAI_API_KEY")
            self.client = None
            return

        # Initialize OpenAI client (works with OpenRouter too)
        base_url = (
            "https://openrouter.ai/api/v1"
            if os.getenv("OPENROUTER_API_KEY")
            else "https://api.openai.com/v1"
        )
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

        # Model configuration
        self.model = os.getenv("LLM_MODEL", "anthropic/claude-3-sonnet")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))

        logger.info(f"LLM Controller initialized with model: {self.model}")

    async def process_command(self, user_input: str, drone_status: Dict = None) -> Dict[str, Any]:
        """Process natural language command using LLM."""

        if not self.client:
            return {
                "success": False,
                "error": "LLM not configured. Please set OPENROUTER_API_KEY or OPENAI_API_KEY",
                "commands": [],
            }

        try:
            # Get drone status for context
            if not drone_status:
                drone_status = await self._get_drone_status()

            # Create system prompt
            system_prompt = self._create_system_prompt(drone_status)

            # Call LLM API
            logger.info(f"Processing command with LLM: {user_input}")
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
                    "X-Title": os.getenv("SITE_NAME", "DroneSphere LLM"),
                },
            )

            content = response.choices[0].message.content
            logger.info(f"LLM response: {content}")

            # Parse LLM response
            commands = self._parse_llm_response(content)

            if commands:
                return {"success": True, "commands": commands, "explanation": content}
            else:
                return {
                    "success": False,
                    "error": "Could not parse valid commands from input",
                    "explanation": content,
                    "commands": [],
                }

        except Exception as e:
            logger.error(f"LLM processing error: {e}")
            return {"success": False, "error": f"LLM error: {str(e)}", "commands": []}

    def _create_system_prompt(self, drone_status: Dict) -> str:
        """Create comprehensive system prompt for LLM with ALL commands."""
        return f"""You are an expert drone command interpreter. Convert natural language to JSON commands.

AVAILABLE COMMANDS:
1. takeoff: {{"name": "takeoff", "params": {{"altitude": 1-50}}}}
2. land: {{"name": "land", "params": {{}}}}
3. goto (GPS): {{"name": "goto", "params": {{"latitude": float, "longitude": float, "altitude": float}}}}
4. goto (NED): {{"name": "goto", "params": {{"north": float, "east": float, "down": float}}}}
5. wait: {{"name": "wait", "params": {{"duration": 0.1-300, "message": "optional"}}}}
6. rtl: {{"name": "rtl", "params": {{}}}}

CURRENT DRONE STATUS:
{json.dumps(drone_status, indent=2)}

MULTI-LANGUAGE COMMAND EXAMPLES:

TAKEOFF COMMANDS:
- English: "take off to 15 meters", "launch to 20m", "go up 10 meters"
- Persian: "بلند شو به 15 متر", "پرواز کن تا 20 متری", "15 متر بالا برو"
- Spanish: "despegar a 15 metros", "subir a 20 metros"
- French: "décoller à 15 mètres", "monter à 20 mètres"

LANDING COMMANDS:
- English: "land", "land here", "come down", "land the drone"
- Persian: "فرود بیا", "فرود بیا همینجا", "پایین بیا", "زمین بنشین"
- Spanish: "aterrizar", "aterrizar aquí"
- French: "atterrir", "atterrir ici"

NAVIGATION COMMANDS (GPS):
- English: "fly to coordinates 47.398, 8.546", "go to GPS 47.398, 8.546 at 503m altitude"
- Persian: "برو به مختصات 47.398, 8.546", "به جی پی اس 47.398, 8.546 پرواز کن"
- Spanish: "volar a coordenadas 47.398, 8.546"

NAVIGATION COMMANDS (NED - Relative):
- English: "go 50 meters north", "fly 30m east and 20m north", "move 50m north, 30m east, up 15m"
- Persian: "50 متر شمال برو", "30 متر شرق و 20 متر شمال پرواز کن"
- Spanish: "ir 50 metros al norte", "volar 30m este y 20m norte"

WAIT COMMANDS:
- English: "wait 5 seconds", "pause for 3 seconds", "hold position for 10 seconds"
- Persian: "5 ثانیه صبر کن", "3 ثانیه منتظر بمان", "10 ثانیه همینجا بمان"
- Spanish: "esperar 5 segundos", "pausar por 3 segundos"

RETURN TO LAUNCH:
- English: "return home", "go back", "return to launch", "come back to start"
- Persian: "خانه برگرد", "به نقطه شروع برگرد", "برگرد عقب"
- Spanish: "volver a casa", "regresar al inicio"

COORDINATE SYSTEMS:
- GPS: Absolute coordinates (lat/lon/altitude_MSL)
  Example: Zurich at 15m height = lat: 47.398, lon: 8.546, alt: 503.0 (488m ground + 15m)
- NED: Relative to takeoff point (north/east/down from origin)
  Example: 50m north, 30m east, 15m up = north: 50, east: 30, down: -15 (negative = up)

COMMAND COMBINATIONS:
- English: "take off to 15m, wait 3 seconds, then land"
- Persian: "15 متر بلند شو، 3 ثانیه صبر کن، بعد فرود بیا"
- Spanish: "despegar a 15m, esperar 3 segundos, luego aterrizar"

SAFETY RULES:
- Takeoff altitude: 1-50m only
- GPS altitude is MSL (Mean Sea Level) - add ground elevation to desired height
- NED down: negative=up, positive=down from origin
- goto requires drone to be airborne (use takeoff first if on ground)
- Always prioritize safety

RESPONSE FORMAT:
Return ONLY a JSON array of commands, nothing else:
[{{"name": "command", "params": {{"param": value}}}}]

COMPLETE EXAMPLES:

User: "take off to 15 meters"
Response: [{{"name": "takeoff", "params": {{"altitude": 15}}}}]

User: "بلند شو به 20 متر" (Persian: take off to 20 meters)
Response: [{{"name": "takeoff", "params": {{"altitude": 20}}}}]

User: "land here now"
Response: [{{"name": "land", "params": {{}}}}]

User: "فرود بیا همینجا الان" (Persian: land here now)
Response: [{{"name": "land", "params": {{}}}}]

User: "fly to coordinates 47.398, 8.546 at 503 meters altitude"
Response: [{{"name": "goto", "params": {{"latitude": 47.398, "longitude": 8.546, "altitude": 503.0}}}}]

User: "go 50 meters north and 30 meters east, then up 15 meters"
Response: [{{"name": "goto", "params": {{"north": 50, "east": 30, "down": -15}}}}]

User: "wait 5 seconds"
Response: [{{"name": "wait", "params": {{"duration": 5}}}}]

User: "5 ثانیه صبر کن" (Persian: wait 5 seconds)
Response: [{{"name": "wait", "params": {{"duration": 5}}}}]

User: "return home"
Response: [{{"name": "rtl", "params": {{}}}}]

User: "خانه برگرد" (Persian: return home)
Response: [{{"name": "rtl", "params": {{}}}}]

User: "take off to 15m, wait 3 seconds, then land"
Response: [{{"name": "takeoff", "params": {{"altitude": 15}}}}, {{"name": "wait", "params": {{"duration": 3}}}}, {{"name": "land", "params": {{}}}}]

User: "15 متر بلند شو، 3 ثانیه صبر کن، بعد فرود بیا" (Persian: take off to 15m, wait 3 seconds, then land)
Response: [{{"name": "takeoff", "params": {{"altitude": 15}}}}, {{"name": "wait", "params": {{"duration": 3}}}}, {{"name": "land", "params": {{}}}}]

IMPORTANT:
- For status/telemetry requests (battery, voltage, etc.), return empty array [] and I'll handle separately
- For unsupported commands, return empty array []
- Always return valid JSON array format
- Support multi-step commands by returning multiple command objects in the array
- Understand natural language variations and synonyms
"""

    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract command JSON."""
        try:
            # Clean response and extract JSON
            cleaned = llm_response.strip()

            # Remove markdown formatting if present
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            # Find JSON array in response
            start_bracket = cleaned.find('[')
            end_bracket = cleaned.rfind(']')

            if start_bracket != -1 and end_bracket != -1:
                json_str = cleaned[start_bracket : end_bracket + 1]
                commands = json.loads(json_str)

                # Ensure it's a list
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
            logger.error(f"Raw response: {llm_response}")
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


class LLMWebBridge:
    """LLM-powered web bridge for drone control."""

    def __init__(self):
        """Initialize web bridge with LLM controller."""
        self.app = FastAPI(
            title="DroneSphere LLM Interface",
            description="Intelligent natural language drone control",
            version="2.0.0",
        )
        self.llm_controller = LLMDroneController()
        self.setup_routes()

    def setup_routes(self):
        """Setup FastAPI routes."""

        @self.app.get("/", response_class=HTMLResponse)
        async def web_interface():
            """Serve the web interface."""
            return HTML_INTERFACE

        @self.app.post("/chat")
        async def process_chat(message: ChatMessage):
            """Process natural language chat message via LLM."""
            try:
                # Check if it's a status request
                user_lower = message.message.lower()
                if any(
                    word in user_lower
                    for word in ["status", "battery", "voltage", "telemetry", "health"]
                ):
                    # Handle status requests directly
                    drone_status = await self.llm_controller._get_drone_status()
                    status_info = await self._format_status_response(drone_status, message.message)
                    return {
                        "success": True,
                        "message": status_info,
                        "original_request": message.message,
                    }

                # Process command with LLM
                result = await self.llm_controller.process_command(message.message)

                if result["success"] and result["commands"]:
                    # Execute commands through DroneSphere
                    execution_result = await self._execute_commands(
                        result["commands"], message.target_drone
                    )

                    if execution_result["success"]:
                        response_msg = f"✅ Command executed successfully!\n\n"
                        response_msg += f"**Original Request**: {message.message}\n"
                        response_msg += f"**Commands**: {len(result['commands'])} executed\n"
                        response_msg += f"**LLM Understanding**: Parsed your request correctly"

                        # Add command details
                        for i, cmd in enumerate(result["commands"], 1):
                            response_msg += f"\n{i}. **{cmd['name']}**: {cmd['params']}"
                    else:
                        response_msg = (
                            f"❌ Command failed: {execution_result.get('error', 'Unknown error')}"
                        )

                    return {
                        "success": execution_result["success"],
                        "message": response_msg,
                        "original_request": message.message,
                    }
                else:
                    return {
                        "success": False,
                        "message": result.get(
                            "error", "Could not understand the command. Please try rephrasing."
                        ),
                        "original_request": message.message,
                    }

            except Exception as e:
                logger.error(f"Chat processing error: {e}")
                return {
                    "success": False,
                    "message": f"Error: {str(e)}",
                    "original_request": message.message,
                }

        @self.app.get("/status/{drone_id}")
        async def get_drone_status(drone_id: int):
            """Get drone status."""
            try:
                drone_status = await self.llm_controller._get_drone_status()
                return {"status": drone_status}
            except Exception as e:
                logger.error(f"Status check error: {e}")
                return {"status": {"error": str(e)}}

    async def _format_status_response(self, drone_status: Dict, original_request: str) -> str:
        """Format drone status response for user."""
        if "error" in drone_status:
            return f"❌ **Status Error**: {drone_status['error']}"

        response = f"📊 **Drone Status Report**\n\n"
        response += f"**Request**: {original_request}\n"
        response += f"**Overall Status**: {drone_status.get('status', 'Unknown')}\n"

        if "backend_connected" in drone_status:
            backend = "✅ Connected" if drone_status["backend_connected"] else "❌ Disconnected"
            response += f"**Backend**: {backend}\n"

        if "executor_ready" in drone_status:
            executor = "✅ Ready" if drone_status["executor_ready"] else "❌ Not Ready"
            response += f"**Executor**: {executor}\n"

        if "uptime" in drone_status:
            response += f"**Uptime**: {drone_status['uptime']} seconds\n"

        response += f"\n*Note: Battery voltage requires telemetry endpoint access*"

        return response

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
        """Run the LLM web bridge server."""
        import uvicorn

        logger.info("Starting DroneSphere LLM Web Bridge...")
        logger.info("🌐 Web interface: http://localhost:3001")
        logger.info("🧠 LLM Integration: ACTIVE")
        logger.info(f"🤖 Model: {self.llm_controller.model}")
        logger.info("🌍 Multi-language support: English, Persian, Spanish, French, German")

        uvicorn.run(self.app, host="0.0.0.0", port=3001, log_level="info")


# Enhanced HTML Interface
HTML_INTERFACE = """<!DOCTYPE html>
<html>
<head>
    <title>DroneSphere - AI-Powered Drone Control</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; color: #333; }
        .header h1 { color: #667eea; margin-bottom: 10px; font-size: 2.5em; }
        .ai-badge { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9em; display: inline-block; margin-bottom: 10px; }
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
            <h1>🚁 DroneSphere</h1>
            <div class="ai-badge">🧠 AI-Powered • Multi-Language</div>
            <p>Control your drone using natural language in multiple languages</p>
        </div>

        <div class="status-panel">
            <div id="systemStatus">
                <strong>🤖 AI System Status:</strong> <span id="statusText">Initializing...</span>
            </div>
        </div>

        <div class="chat-container">
            <div class="input-group">
                <input type="text" id="messageInput" placeholder="Enter your command in any language (e.g., 'take off to 15 meters' or 'بلند شو به 15 متر')" />
                <button id="sendButton" onclick="sendMessage()">Send</button>
            </div>

            <div id="chatHistory" class="chat-history">
                <div class="bot-message">
                    <strong>🤖 DroneSphere AI:</strong> Ready for intelligent commands! I understand multiple languages and complex instructions.
                    <div class="timestamp">AI-powered • Multi-language support active</div>
                </div>
            </div>
        </div>

        <div class="examples">
            <h3>💡 Try These Commands (Any Language):</h3>

            <div class="language-examples">
                <div class="lang-group">
                    <h4>🇺🇸 English</h4>
                    <div class="example" onclick="setCommand('take off to 15 meters')">🚀 "take off to 15 meters"</div>
                    <div class="example" onclick="setCommand('what is the battery status')">🔋 "what is the battery status"</div>
                </div>

                <div class="lang-group">
                    <h4>🇮🇷 Persian/Farsi</h4>
                    <div class="example" onclick="setCommand('بلند شو به 15 متر')">🚀 "بلند شو به 15 متر"</div>
                    <div class="example" onclick="setCommand('فرود بیا')">🛬 "فرود بیا"</div>
                </div>

                <div class="lang-group">
                    <h4>🇪🇸 Spanish</h4>
                    <div class="example" onclick="setCommand('despegar a 15 metros')">🚀 "despegar a 15 metros"</div>
                    <div class="example" onclick="setCommand('aterrizar')">🛬 "aterrizar"</div>
                </div>

                <div class="lang-group">
                    <h4>🇫🇷 French</h4>
                    <div class="example" onclick="setCommand('décoller à 15 mètres')">🚀 "décoller à 15 mètres"</div>
                    <div class="example" onclick="setCommand('atterrir')">🛬 "atterrir"</div>
                </div>
            </div>

            <h4 style="margin-top: 20px;">🧠 Advanced AI Commands:</h4>
            <div class="example" onclick="setCommand('fly to coordinates 47.398, 8.546 at 20 meters height')">🗺️ Complex navigation with GPS coordinates</div>
            <div class="example" onclick="setCommand('go 50 meters north, wait 3 seconds, then land')">⚡ Multi-step mission sequences</div>
            <div class="example" onclick="setCommand('check the drone health and battery status')">📊 Intelligent status queries</div>
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
            sendButton.textContent = loading ? '🤖 AI Processing...' : 'Send';
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
                    addMessage(`<strong>🤖 DroneSphere AI:</strong> ${result.message}`, 'bot');
                } else {
                    addMessage(`<strong>🤖 DroneSphere AI:</strong> ${result.message}`, 'error');
                }

            } catch (error) {
                addMessage(`<strong>🤖 DroneSphere AI:</strong> Connection error: ${error.message}`, 'error');
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
                <span style="color: #4caf50;">✅ AI Active</span> |
                <span style="color: #2196f3;">🧠 LLM Ready</span> |
                <span style="color: #ff9800;">🌍 Multi-Language</span>
            `;
        }

        updateStatus();
    </script>
</body>
</html>"""


def main():
    """Main entry point for LLM web bridge."""
    bridge = LLMWebBridge()
    bridge.run()


if __name__ == "__main__":
    main()
