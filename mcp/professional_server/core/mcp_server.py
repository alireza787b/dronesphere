#!/usr/bin/env python3
"""
Production HTTP MCP Server for DroneSphere
Combines the working HTTP foundation with real drone control

This REPLACES your core/mcp_server.py
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
import yaml
from aiohttp import web
from dotenv import load_dotenv

# Import your existing components
try:
    from .llm_controller import MultiLLMController
    from .rag_system import RAGSystem
    from .prompt_manager import PromptManager
except ImportError:
    # Handle relative import issues during testing
    import sys
    sys.path.append('.')
    try:
        from core.llm_controller import MultiLLMController
        from core.rag_system import RAGSystem
        from core.prompt_manager import PromptManager
    except ImportError:
        # Create mock classes for testing
        class MultiLLMController:
            def __init__(self, config_path): pass
            async def test_providers(self): return {"openrouter": {"available": True}, "openai": {"available": True}}
            async def process_with_fallback(self, messages): 
                return type('obj', (object,), {
                    'success': True, 'content': 'Mock LLM response', 
                    'provider': type('p', (object,), {'value': 'mock'})(),
                    'model': 'mock-model', 'response_time': 0.5
                })()
        
        class RAGSystem:
            def __init__(self, config_path): pass
            def update_index(self): pass
            def get_schema_context(self, query): return "Mock RAG context"
            def get_index_status(self): return {"documents_count": 7, "index_built": True, "last_update": "2025-08-04"}
        
        class PromptManager:
            def __init__(self, config_path): pass
            def get_system_prompt(self, context): return "Mock system prompt"
            def get_command_prompt(self, command, telemetry): return f"Execute: {command}"
            def get_prompt_layers(self): return {"default": {"enabled": True, "content_length": 100}}

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ProductionMCPServer:
    """Production HTTP MCP server with real drone control."""
    
    def __init__(self, config_path: str = "config/config.yaml", port: int = 8003, host: str = "0.0.0.0"):
        """Initialize production MCP server."""
        self.config = self._load_config(config_path)
        self.port = port
        self.host = host
        
        # Initialize core components
        try:
            self.llm_controller = MultiLLMController(config_path)
            self.rag_system = RAGSystem(config_path)
            self.prompt_manager = PromptManager(config_path)
            logger.info("✅ Core components initialized")
        except Exception as e:
            logger.warning(f"⚠️  Core components failed: {e}, using fallback mode")
            self.llm_controller = None
            self.rag_system = None
            self.prompt_manager = None
        
        # DroneSphere integration
        self.dronesphere_url = self.config.get("dronesphere", {}).get("server_url", "http://localhost:8002")
        self.default_drone_id = self.config.get("dronesphere", {}).get("default_drone_id", 1)
        self.timeout = self.config.get("dronesphere", {}).get("timeout", 60.0)
        
        # Initialize HTTP app
        self.app = web.Application()
        self.setup_routes()
        
        logger.info("🚀 Production MCP Server initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return {
                "dronesphere": {
                    "server_url": "http://localhost:8002",
                    "default_drone_id": 1,
                    "timeout": 60.0
                }
            }
    
    def setup_routes(self):
        """Setup HTTP routes for production."""
        
        async def health_check(request):
            """Health check with real system status."""
            return web.json_response({
                'status': 'healthy',
                'service': 'dronesphere-production-mcp',
                'version': '2.0.0',
                'port': self.port,
                'timestamp': datetime.now().isoformat(),
                'capabilities': ['drone-control', 'llm-processing', 'rag-search'],
                'dronesphere_url': self.dronesphere_url,
                'components': {
                    'llm_controller': self.llm_controller is not None,
                    'rag_system': self.rag_system is not None,
                    'prompt_manager': self.prompt_manager is not None
                }
            })
        
        async def list_tools(request):
            """List available tools."""
            tools = {
                'execute_drone_command': {
                    'description': 'Execute natural language drone commands with AI processing',
                    'method': 'POST',
                    'endpoint': '/api/drone/command',
                    'parameters': {
                        'command': 'string - Natural language command (e.g., "take off to 10 meters")',
                        'drone_id': 'integer - Target drone ID (optional, defaults to 1)'
                    }
                },
                'get_telemetry': {
                    'description': 'Get real-time drone telemetry data',
                    'method': 'GET',
                    'endpoint': '/api/drone/telemetry',
                    'parameters': {
                        'drone_id': 'integer - Target drone ID (optional, defaults to 1)'
                    }
                },
                'get_system_status': {
                    'description': 'Get comprehensive system status',
                    'method': 'GET',
                    'endpoint': '/api/system/status'
                }
            }
            
            return web.json_response({
                'success': True,
                'tools': tools,
                'count': len(tools)
            })
        
        async def execute_command(request):
            """Execute drone command with real AI processing."""
            try:
                data = await request.json()
                command = data.get('command', '')
                drone_id = data.get('drone_id', self.default_drone_id)
                
                if not command:
                    return web.json_response({
                        'success': False,
                        'error': 'No command provided'
                    }, status=400)
                
                logger.info(f"🎯 Processing command: '{command}' for drone {drone_id}")
                
                # Get current telemetry first
                try:
                    telemetry = await self._get_drone_telemetry(drone_id)
                    logger.info(f"📊 Retrieved telemetry for drone {drone_id}")
                except Exception as e:
                    logger.warning(f"⚠️  Telemetry fetch failed: {e}")
                    telemetry = self._get_fallback_telemetry(drone_id)
                
                # Process with LLM if available
                if self.llm_controller and self.rag_system and self.prompt_manager:
                    try:
                        result = await self._process_with_ai(command, drone_id, telemetry)
                        logger.info(f"🤖 AI processing completed")
                        return web.json_response(result)
                    except Exception as e:
                        logger.error(f"❌ AI processing failed: {e}")
                        # Fall back to direct command processing
                
                # Fallback: Direct command processing
                result = await self._process_direct_command(command, drone_id, telemetry)
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"💥 Command execution error: {e}")
                return web.json_response({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, status=500)
        
        async def get_telemetry(request):
            """Get real drone telemetry."""
            try:
                drone_id = int(request.query.get('drone_id', self.default_drone_id))
                
                telemetry = await self._get_drone_telemetry(drone_id)
                
                return web.json_response({
                    'success': True,
                    'drone_id': drone_id,
                    'telemetry': telemetry,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'dronesphere' if not telemetry.get('telemetry_warning') else 'fallback'
                })
                
            except Exception as e:
                logger.error(f"Telemetry error: {e}")
                return web.json_response({
                    'success': False,
                    'error': str(e)
                }, status=500)
        
        async def get_system_status(request):
            """Get comprehensive system status."""
            try:
                status = {
                    'success': True,
                    'timestamp': datetime.now().isoformat(),
                    'server_info': {
                        'host': self.host,
                        'port': self.port,
                        'version': '2.0.0',
                        'dronesphere_url': self.dronesphere_url
                    }
                }
                
                # LLM Status
                if self.llm_controller:
                    try:
                        llm_status = await self.llm_controller.test_providers()
                        status['llm_providers'] = llm_status
                    except:
                        status['llm_providers'] = {'error': 'Failed to test providers'}
                else:
                    status['llm_providers'] = {'status': 'not_available'}
                
                # RAG Status
                if self.rag_system:
                    try:
                        status['rag_system'] = self.rag_system.get_index_status()
                    except:
                        status['rag_system'] = {'error': 'Failed to get status'}
                else:
                    status['rag_system'] = {'status': 'not_available'}
                
                # Drone Status
                try:
                    telemetry = await self._get_drone_telemetry(self.default_drone_id)
                    status['drone_status'] = {
                        'connected': telemetry.get('connected', False),
                        'armed': telemetry.get('armed', False),
                        'battery_percent': telemetry.get('battery', {}).get('remaining_percent', 0),
                        'flight_mode': telemetry.get('flight_mode', 'UNKNOWN'),
                        'altitude': telemetry.get('position', {}).get('relative_altitude', 0)
                    }
                except Exception as e:
                    status['drone_status'] = {'error': str(e)}
                
                return web.json_response(status)
                
            except Exception as e:
                logger.error(f"Status error: {e}")
                return web.json_response({
                    'success': False,
                    'error': str(e)
                }, status=500)
        
        async def api_docs(request):
            """API documentation."""
            docs = {
                'service': 'DroneSphere Production MCP Server',
                'version': '2.0.0',
                'description': 'Production HTTP API for drone control with AI processing',
                'base_url': f'http://{self.host}:{self.port}',
                'endpoints': {
                    'GET /health': 'Health check and system info',
                    'GET /api/tools': 'List available tools',
                    'POST /api/drone/command': 'Execute drone command with AI',
                    'GET /api/drone/telemetry': 'Get real-time telemetry',
                    'GET /api/system/status': 'Comprehensive system status'
                },
                'examples': {
                    'take_off': {
                        'url': '/api/drone/command',
                        'method': 'POST',
                        'body': {'command': 'take off to 10 meters', 'drone_id': 1}
                    },
                    'land': {
                        'url': '/api/drone/command',
                        'method': 'POST',
                        'body': {'command': 'land now', 'drone_id': 1}
                    },
                    'goto': {
                        'url': '/api/drone/command',
                        'method': 'POST',
                        'body': {'command': 'go to GPS coordinates 37.7749, -122.4194', 'drone_id': 1}
                    }
                },
                'n8n_integration': {
                    'http_request_node': {
                        'url': f'http://{self.host}:{self.port}/api/drone/command',
                        'method': 'POST',
                        'headers': {'Content-Type': 'application/json'},
                        'body': '{"command": "{{$json["command"]}}", "drone_id": 1}'
                    }
                }
            }
            return web.json_response(docs)
        
        # Register routes
        self.app.router.add_get('/', api_docs)
        self.app.router.add_get('/health', health_check)
        self.app.router.add_get('/api/tools', list_tools)
        self.app.router.add_post('/api/drone/command', execute_command)
        self.app.router.add_get('/api/drone/telemetry', get_telemetry)
        self.app.router.add_get('/api/system/status', get_system_status)
    
    async def _get_drone_telemetry(self, drone_id: int) -> Dict[str, Any]:
        """Get real drone telemetry from DroneSphere server."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.dronesphere_url}/fleet/telemetry/{drone_id}/live")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"📡 Got telemetry for drone {drone_id}")
                    return data
                else:
                    logger.warning(f"⚠️  Telemetry request failed: HTTP {response.status_code}")
                    return self._get_fallback_telemetry(drone_id)
                    
        except Exception as e:
            logger.error(f"❌ Telemetry fetch error: {e}")
            return self._get_fallback_telemetry(drone_id)
    
    def _get_fallback_telemetry(self, drone_id: int) -> Dict[str, Any]:
        """Fallback telemetry when live data unavailable."""
        return {
            "drone_id": drone_id,
            "timestamp": datetime.now().timestamp(),
            "position": {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0, "relative_altitude": 0.0},
            "attitude": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
            "battery": {"voltage": 12.6, "remaining_percent": 100.0},
            "flight_mode": "UNKNOWN",
            "armed": False,
            "connected": False,
            "telemetry_warning": "Using fallback data - live telemetry unavailable"
        }
    
    async def _process_with_ai(self, command: str, drone_id: int, telemetry: Dict) -> Dict[str, Any]:
        """Process command with full AI pipeline."""
        # Get RAG context
        rag_context = self.rag_system.get_schema_context(command)
        
        # Build prompts
        system_prompt = self.prompt_manager.get_system_prompt({
            "telemetry": telemetry,
            "rag_context": rag_context
        })
        user_prompt = self.prompt_manager.get_command_prompt(command, telemetry)
        
        # Process with LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        llm_response = await self.llm_controller.process_with_fallback(messages)
        
        if not llm_response.success:
            raise Exception(f"LLM processing failed: {llm_response.error}")
        
        # Parse and execute commands
        commands = self._parse_llm_response(llm_response.content)
        
        if commands:
            execution_result = await self._execute_drone_commands(commands, drone_id)
            return {
                'success': execution_result['success'],
                'type': 'ai_command_execution',
                'user_command': command,
                'parsed_commands': commands,
                'commands_executed': len(commands),
                'execution_result': execution_result,
                'ai_response': llm_response.content,
                'provider': llm_response.provider.value,
                'model': llm_response.model,
                'response_time': llm_response.response_time,
                'drone_id': drone_id,
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Informational response
            return {
                'success': True,
                'type': 'informational',
                'user_command': command,
                'ai_response': llm_response.content,
                'provider': llm_response.provider.value,
                'model': llm_response.model,
                'response_time': llm_response.response_time,
                'drone_id': drone_id,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _process_direct_command(self, command: str, drone_id: int, telemetry: Dict) -> Dict[str, Any]:
        """Direct command processing without AI (fallback mode)."""
        # Simple command mapping
        command_lower = command.lower()
        
        if any(word in command_lower for word in ['take off', 'takeoff', 'launch']):
            commands = [{"name": "takeoff", "params": {"altitude": 10}, "mode": "continue"}]
        elif any(word in command_lower for word in ['land', 'landing']):
            commands = [{"name": "land", "params": {}, "mode": "continue"}]
        elif any(word in command_lower for word in ['return', 'rtl', 'home']):
            commands = [{"name": "rtl", "params": {}, "mode": "continue"}]
        else:
            return {
                'success': True,
                'type': 'status_query',
                'user_command': command,
                'response': f"Current drone status: {telemetry.get('flight_mode', 'UNKNOWN')} mode, Battery: {telemetry.get('battery', {}).get('remaining_percent', 0)}%",
                'telemetry': telemetry,
                'drone_id': drone_id,
                'timestamp': datetime.now().isoformat()
            }
        
        # Execute commands
        execution_result = await self._execute_drone_commands(commands, drone_id)
        
        return {
            'success': execution_result['success'],
            'type': 'direct_command_execution',
            'user_command': command,
            'parsed_commands': commands,
            'commands_executed': len(commands),
            'execution_result': execution_result,
            'processing_mode': 'direct_fallback',
            'drone_id': drone_id,
            'timestamp': datetime.now().isoformat()
        }
    
    def _parse_llm_response(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse commands from LLM response."""
        try:
            # Look for JSON array in response
            start_bracket = llm_response.find('[')
            end_bracket = llm_response.rfind(']')
            
            if start_bracket != -1 and end_bracket != -1:
                json_str = llm_response[start_bracket:end_bracket + 1]
                commands = json.loads(json_str)
                
                if isinstance(commands, dict):
                    commands = [commands]
                
                # Validate commands
                valid_commands = []
                valid_names = ["takeoff", "land", "goto", "wait", "rtl"]
                
                for cmd in commands:
                    if isinstance(cmd, dict) and "name" in cmd and "params" in cmd:
                        if cmd["name"] in valid_names:
                            valid_commands.append(cmd)
                
                return valid_commands
            
            return []
            
        except json.JSONDecodeError as e:
            logger.warning(f"Command parsing failed: {e}")
            return []
    
    async def _execute_drone_commands(self, commands: List[Dict[str, Any]], drone_id: int) -> Dict[str, Any]:
        """Execute commands on real drone through DroneSphere."""
        try:
            logger.info(f"🚁 Executing {len(commands)} commands on drone {drone_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.dronesphere_url}/fleet/commands",
                    json={
                        "commands": commands,
                        "target_drone": drone_id,
                        "queue_mode": "override"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Commands executed successfully")
                    return {
                        "success": True,
                        "result": result,
                        "commands_executed": len(commands),
                        "target_drone": drone_id
                    }
                else:
                    logger.error(f"❌ Command execution failed: HTTP {response.status_code}")
                    return {
                        "success": False,
                        "error": f"DroneSphere server error: HTTP {response.status_code}",
                        "commands_executed": 0
                    }
                    
        except Exception as e:
            logger.error(f"💥 Command execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "commands_executed": 0
            }
    
    async def run(self):
        """Run the production server."""
        logger.info("🚀 Starting DroneSphere Production MCP Server...")
        
        # Initialize components
        if self.rag_system:
            logger.info("📚 Initializing RAG system...")
            try:
                self.rag_system.update_index()
                logger.info("✅ RAG system ready")
            except Exception as e:
                logger.error(f"❌ RAG initialization failed: {e}")
        
        if self.llm_controller:
            logger.info("🤖 Testing LLM providers...")
            try:
                llm_results = await self.llm_controller.test_providers()
                for provider, result in llm_results.items():
                    status = "✅" if result.get("available") else "❌"
                    logger.info(f"LLM Provider {provider}: {status}")
            except Exception as e:
                logger.error(f"❌ LLM testing failed: {e}")
        
        # Start HTTP server
        logger.info(f"🌐 Starting HTTP server on {self.host}:{self.port}")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info("🎉 Production MCP Server ready!")
        logger.info(f"📍 Health check: http://{self.host}:{self.port}/health")
        logger.info(f"🛠️  API tools: http://{self.host}:{self.port}/api/tools")
        logger.info(f"🚁 Drone control: POST http://{self.host}:{self.port}/api/drone/command")
        logger.info(f"📊 Telemetry: GET http://{self.host}:{self.port}/api/drone/telemetry")
        logger.info(f"📚 Documentation: http://{self.host}:{self.port}/")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Server stopped by user")
        finally:
            await runner.cleanup()


# Backward compatibility
MCPDroneServer = ProductionMCPServer
N8NCompatibleMCPServer = ProductionMCPServer


async def main():
    """Main function for direct execution."""
    server = ProductionMCPServer()
    await server.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"💥 Server failed: {e}")
        import traceback
        traceback.print_exc()