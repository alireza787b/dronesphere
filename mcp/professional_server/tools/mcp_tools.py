"""
MCP Tool Definitions for DroneSphere Professional MCP Server
Professional tool schemas and descriptions for MCP integration
"""

from typing import Dict, Any, List
from mcp.types import Tool


def get_mcp_tools() -> List[Tool]:
    """Get all MCP tool definitions."""
    return [
        execute_drone_command_tool(),
        get_drone_telemetry_tool(),
        get_command_schemas_tool(),
        get_system_status_tool()
    ]


def execute_drone_command_tool() -> Tool:
    """Execute natural language drone commands with intelligent processing."""
    return Tool(
        name="execute_drone_command",
        description="Execute natural language drone commands with intelligent processing, RAG context, and multi-LLM support. Supports commands like 'takeoff to 10 meters', 'go 5 meters north then land', 'what's my battery level?', etc.",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Natural language command to execute (e.g., 'takeoff to 10 meters', 'go north 5m then land', 'what's my battery level?')",
                    "minLength": 1
                },
                "drone_id": {
                    "type": "integer",
                    "description": "Target drone ID (default: 1)",
                    "default": 1,
                    "minimum": 1
                }
            },
            "required": ["command"]
        }
    )


def get_drone_telemetry_tool() -> Tool:
    """Get real-time drone telemetry data."""
    return Tool(
        name="get_drone_telemetry",
        description="Get real-time telemetry data from the specified drone including position, attitude, battery, and system status.",
        inputSchema={
            "type": "object",
            "properties": {
                "drone_id": {
                    "type": "integer",
                    "description": "Target drone ID (default: 1)",
                    "default": 1,
                    "minimum": 1
                }
            }
        }
    )


def get_command_schemas_tool() -> Tool:
    """Get available command schemas and their descriptions."""
    return Tool(
        name="get_command_schemas",
        description="Get available command schemas and their descriptions. Useful for understanding what commands are available and their parameters.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter schemas by category (e.g., 'basic', 'navigation', 'safety')",
                    "enum": ["basic", "navigation", "safety", "general"]
                }
            }
        }
    )


def get_system_status_tool() -> Tool:
    """Get comprehensive system status including LLM, RAG, and drone status."""
    return Tool(
        name="get_system_status",
        description="Get comprehensive system status including LLM provider status, RAG system status, prompt manager status, and current drone status.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )


def get_tool_schemas() -> Dict[str, Any]:
    """Get tool schemas in a format suitable for documentation."""
    tools = get_mcp_tools()
    
    schemas = {}
    for tool in tools:
        schemas[tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
            "examples": get_tool_examples(tool.name)
        }
    
    return schemas


def get_tool_examples(tool_name: str) -> List[Dict[str, Any]]:
    """Get example usage for each tool."""
    examples = {
        "execute_drone_command": [
            {
                "description": "Simple takeoff command",
                "input": {"command": "takeoff to 10 meters"}
            },
            {
                "description": "Complex sequence command",
                "input": {"command": "takeoff to 15m then go 5 meters north then wait 3 seconds then land"}
            },
            {
                "description": "Status query",
                "input": {"command": "what's my current battery level?"}
            },
            {
                "description": "Navigation command",
                "input": {"command": "go to GPS coordinates 37.7749, -122.4194 at 20m altitude"}
            },
            {
                "description": "Return to launch",
                "input": {"command": "return to launch"}
            },
            {
                "description": "Multi-language support (Persian)",
                "input": {"command": "بلند شو به 10 متر سپس شمال برو"}
            }
        ],
        "get_drone_telemetry": [
            {
                "description": "Get default drone telemetry",
                "input": {}
            },
            {
                "description": "Get specific drone telemetry",
                "input": {"drone_id": 1}
            }
        ],
        "get_command_schemas": [
            {
                "description": "Get all schemas",
                "input": {}
            },
            {
                "description": "Get basic command schemas",
                "input": {"category": "basic"}
            },
            {
                "description": "Get navigation schemas",
                "input": {"category": "navigation"}
            }
        ],
        "get_system_status": [
            {
                "description": "Get complete system status",
                "input": {}
            }
        ]
    }
    
    return examples.get(tool_name, [])


def get_tool_categories() -> Dict[str, List[str]]:
    """Get tools organized by category."""
    return {
        "Drone Control": [
            "execute_drone_command",
            "get_drone_telemetry"
        ],
        "System Information": [
            "get_command_schemas",
            "get_system_status"
        ]
    }


def get_tool_metadata() -> Dict[str, Any]:
    """Get comprehensive tool metadata."""
    return {
        "server_name": "dronesphere-professional-mcp",
        "version": "1.0.0",
        "description": "Professional MCP server for drone control with RAG and multi-LLM support",
        "total_tools": len(get_mcp_tools()),
        "categories": get_tool_categories(),
        "features": [
            "Natural language command processing",
            "Multi-LLM support with fallback",
            "RAG-powered command schema retrieval",
            "Customizable prompt management",
            "Real-time telemetry integration",
            "Multi-language support",
            "Intelligent command sequencing",
            "Safety assessment and validation"
        ],
        "supported_languages": [
            "English",
            "Persian",
            "Spanish", 
            "German",
            "French"
        ],
        "llm_providers": [
            "OpenRouter (Primary)",
            "OpenAI GPT-4o (Secondary)",
            "Ollama Local (Fallback)"
        ]
    } 