"""
DroneSphere Professional MCP Server - Main Entry Point
Port 8003 - Standards-compliant MCP server with RAG and multi-LLM support
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.mcp_server import MCPDroneServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the DroneSphere Professional MCP Server."""
    try:
        logger.info("🚀 Starting DroneSphere Professional MCP Server v1.0.0")
        logger.info("📍 Port: 8003 (MCP Protocol)")
        logger.info("🤖 Multi-LLM Support: OpenRouter → GPT-4o → Ollama")
        logger.info("📚 RAG Integration: Command Schema Indexing")
        logger.info("💬 Customizable Prompts: YAML-based Configuration")
        
        # Create and run MCP server
        server = MCPDroneServer("config/config.yaml")
        await server.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 