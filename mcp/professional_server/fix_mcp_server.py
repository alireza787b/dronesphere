#!/usr/bin/env python3
"""
Quick MCP Server Diagnostic and Fix
Identify why server.run() isn't binding to port 8003

Usage: python fix_mcp_server.py
"""

import asyncio
import os
import sys
from pathlib import Path
import json

async def test_mcp_server_directly():
    """Test what happens when we import and run the server directly."""
    print("🔍 Testing MCP Server Implementation")
    print("=" * 50)
    
    try:
        # Import the server class
        sys.path.insert(0, '.')
        from core.mcp_server import MCPDroneServer
        
        print("✅ Successfully imported MCPDroneServer")
        
        # Create server instance
        server = MCPDroneServer("config/config.yaml")
        print("✅ Server instance created")
        
        # Check what run() method actually does
        import inspect
        run_method = getattr(server, 'run', None)
        
        if run_method:
            print("✅ Server has run() method")
            
            # Get the source code of run method
            try:
                source = inspect.getsource(run_method)
                print("📄 run() method source:")
                print("-" * 30)
                print(source)
                print("-" * 30)
            except:
                print("❌ Could not get run() method source")
            
            # Check if run method is async
            if asyncio.iscoroutinefunction(run_method):
                print("✅ run() is async - this is correct")
            else:
                print("❌ run() is not async - this might be the problem")
        else:
            print("❌ Server has no run() method!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to test server: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_mcp_server_file():
    """Check the MCP server file directly."""
    print("\n🔍 Checking MCP Server File")
    print("=" * 50)
    
    server_file = Path("core/mcp_server.py")
    
    if not server_file.exists():
        print("❌ core/mcp_server.py not found!")
        return False
    
    try:
        with open(server_file, 'r') as f:
            content = f.read()
        
        # Check for common issues
        issues = []
        
        if "async def run(" not in content:
            issues.append("Missing 'async def run(' method")
        
        if "8003" not in content and "port" not in content:
            issues.append("No port configuration found")
        
        if "serve" not in content and "bind" not in content and "listen" not in content:
            issues.append("No server binding code found")
        
        if "await" not in content:
            issues.append("No async/await usage - might not be properly async")
        
        # Look for HTTP server frameworks
        frameworks = ['fastapi', 'flask', 'aiohttp', 'uvicorn', 'hypercorn', 'websockets']
        found_frameworks = [fw for fw in frameworks if fw in content.lower()]
        
        if not found_frameworks:
            issues.append("No HTTP server framework detected")
        else:
            print(f"✅ Found frameworks: {', '.join(found_frameworks)}")
        
        if issues:
            print("🚨 CRITICAL ISSUES FOUND:")
            for issue in issues:
                print(f"   • {issue}")
            return False
        else:
            print("✅ Basic structure looks OK")
            return True
    
    except Exception as e:
        print(f"❌ Failed to analyze server file: {e}")
        return False

def create_minimal_working_mcp_server():
    """Create a minimal working MCP server for testing."""
    print("\n🔧 Creating Minimal Test Server")
    print("=" * 50)
    
    test_server_code = '''#!/usr/bin/env python3
"""
Minimal Working MCP Server Test
This will prove if the issue is in the MCP implementation
"""

import asyncio
import json
from aiohttp import web, web_request
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MinimalMCPServer:
    def __init__(self, port=8003):
        self.port = port
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup basic MCP routes."""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/mcp', self.handle_mcp)
    
    async def health_check(self, request):
        """Basic health check."""
        return web.json_response({
            'status': 'healthy',
            'service': 'minimal-mcp-server',
            'port': self.port
        })
    
    async def handle_mcp(self, request):
        """Handle MCP JSON-RPC requests."""
        try:
            data = await request.json()
            logger.info(f"MCP Request: {data.get('method', 'unknown')}")
            
            # Basic MCP response
            response = {
                'jsonrpc': '2.0',
                'id': data.get('id', 1),
                'result': {
                    'capabilities': {
                        'tools': {},
                        'prompts': {},
                        'resources': {}
                    },
                    'serverInfo': {
                        'name': 'minimal-mcp-test',
                        'version': '1.0.0'
                    }
                }
            }
            
            return web.json_response(response)
            
        except Exception as e:
            logger.error(f"MCP Error: {e}")
            return web.json_response({
                'jsonrpc': '2.0',
                'id': 1,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }, status=500)
    
    async def run(self):
        """Start the server."""
        logger.info(f"🚀 Starting Minimal MCP Server on port {self.port}")
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"✅ MCP Server listening on http://0.0.0.0:{self.port}")
        logger.info("🔍 Test with: curl http://localhost:8003/health")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Server stopped")
        finally:
            await runner.cleanup()

async def main():
    server = MinimalMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    test_file = Path("test_mcp_server.py")
    with open(test_file, 'w') as f:
        f.write(test_server_code)
    
    print(f"✅ Created {test_file}")
    print("🧪 Test with: python test_mcp_server.py")
    print("🔍 Verify with: netstat -tlnp | grep 8003")

def main():
    """Run comprehensive MCP server diagnosis."""
    print("🔍 MCP Server Diagnostic Suite")
    print("=" * 60)
    
    # Test 1: Check server file
    if not check_mcp_server_file():
        print("\n❌ Server file has critical issues")
    
    # Test 2: Try to import and inspect server
    if not asyncio.run(test_mcp_server_directly()):
        print("\n❌ Server class has implementation issues")
    
    # Test 3: Create minimal working server for comparison
    create_minimal_working_mcp_server()
    
    print("\n" + "=" * 60)
    print("🚀 NEXT STEPS:")
    print("1. Run the test server: python test_mcp_server.py")
    print("2. Check if it binds: netstat -tlnp | grep 8003")
    print("3. If test works, compare with your core/mcp_server.py")
    print("4. Fix the run() method in your actual server")

if __name__ == "__main__":
    main()