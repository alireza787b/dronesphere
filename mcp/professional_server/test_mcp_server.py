#!/usr/bin/env python3
"""
Minimal Working HTTP MCP Server
This WILL work with n8n - guaranteed

Replace your main.py with this temporarily to test
"""

import asyncio
import json
import logging
from datetime import datetime
from aiohttp import web, ClientTimeout
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MinimalMCPServer:
    """Bulletproof minimal MCP server that actually works."""
    
    def __init__(self, port: int = 8003, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.app = web.Application()
        self.setup_routes()
        logger.info("Minimal MCP Server initialized")
    
    def setup_routes(self):
        """Setup basic routes that work."""
        
        async def health_check(request):
            """Health check endpoint."""
            return web.json_response({
                'status': 'healthy',
                'service': 'minimal-mcp-server',
                'version': '1.0.0',
                'port': self.port,
                'timestamp': datetime.now().isoformat()
            })
        
        async def list_tools(request):
            """List available tools."""
            tools = {
                'execute_drone_command': {
                    'description': 'Execute drone commands',
                    'method': 'POST',
                    'endpoint': '/api/drone/command'
                },
                'get_telemetry': {
                    'description': 'Get drone telemetry',
                    'method': 'GET', 
                    'endpoint': '/api/drone/telemetry'
                }
            }
            
            return web.json_response({
                'success': True,
                'tools': tools,
                'count': len(tools)
            })
        
        async def execute_command(request):
            """Execute drone command."""
            try:
                data = await request.json()
                command = data.get('command', '')
                drone_id = data.get('drone_id', 1)
                
                if not command:
                    return web.json_response({
                        'success': False,
                        'error': 'No command provided'
                    }, status=400)
                
                # Simulate command processing
                result = {
                    'success': True,
                    'message': f'Command processed: {command}',
                    'drone_id': drone_id,
                    'timestamp': datetime.now().isoformat(),
                    'processed_by': 'minimal-mcp-server'
                }
                
                logger.info(f"Processed command: {command} for drone {drone_id}")
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"Command error: {e}")
                return web.json_response({
                    'success': False,
                    'error': str(e)
                }, status=500)
        
        async def get_telemetry(request):
            """Get drone telemetry."""
            try:
                drone_id = int(request.query.get('drone_id', 1))
                
                # Simulate telemetry data
                telemetry = {
                    'drone_id': drone_id,
                    'timestamp': datetime.now().isoformat(),
                    'position': {
                        'latitude': 37.7749,
                        'longitude': -122.4194,
                        'altitude': 100.5,
                        'relative_altitude': 50.2
                    },
                    'battery': {
                        'remaining_percent': 85,
                        'voltage': 12.6
                    },
                    'flight_mode': 'GUIDED',
                    'armed': True,
                    'connected': True
                }
                
                return web.json_response({
                    'success': True,
                    'telemetry': telemetry
                })
                
            except Exception as e:
                logger.error(f"Telemetry error: {e}")
                return web.json_response({
                    'success': False,
                    'error': str(e)
                }, status=500)
        
        async def api_docs(request):
            """API documentation."""
            docs = {
                'service': 'Minimal MCP Server',
                'version': '1.0.0',
                'description': 'Working HTTP API for n8n integration',
                'endpoints': {
                    'GET /health': 'Health check',
                    'GET /api/tools': 'List tools',
                    'POST /api/drone/command': 'Execute drone command',
                    'GET /api/drone/telemetry': 'Get telemetry'
                },
                'examples': {
                    'command': {
                        'url': '/api/drone/command',
                        'method': 'POST',
                        'body': {'command': 'take off', 'drone_id': 1}
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
    
    async def run(self):
        """Run the server."""
        logger.info(f"🚀 Starting Minimal MCP Server on {self.host}:{self.port}")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"✅ Server running on http://{self.host}:{self.port}")
        logger.info(f"🔍 Test: curl http://localhost:{self.port}/health")
        
        try:
            # Keep running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Server stopped")
        finally:
            await runner.cleanup()


async def main():
    """Main function."""
    server = MinimalMCPServer()
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