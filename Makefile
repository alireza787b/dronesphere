# DroneSphere v2.0 Development Makefile - Complete Professional System
# Comprehensive drone command and control with LLM MCP integration
# Professional testing infrastructure with safe cleanup and robust operations

.PHONY: help dev clean install-deps docker-clean
.PHONY: sitl agent server status
.PHONY: test-health test-ping test-detailed test-telemetry test-agent
.PHONY: test-server-health test-fleet-health test-fleet-registry test-server-takeoff test-server test-fleet
.PHONY: test-takeoff test-land test-rtl test-wait test-commands
.PHONY: test-goto-gps test-goto-ned test-goto
.PHONY: test-robustness test-sequence test-navigation test-all
.PHONY: mcp-install mcp-config mcp mcp-web test-mcp-api test-llm test-mcp-web test-all-mcp
.PHONY: dev-mcp dev-web dev-llm status-full claude-config clean-mcp help-mcp help-llm help-all

SHELL := /bin/bash

# =============================================================================
# HELP COMMANDS - Professional Documentation
# =============================================================================

help: ## Show essential development commands
	@echo "🚁 DroneSphere v2.0 - Essential Commands"
	@echo "========================================"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make dev-llm         Start complete LLM system"
	@echo "  make status-full     Check all system components"
	@echo "  make test-all        Run complete test suite"
	@echo "  make clean           Stop all services safely"
	@echo ""
	@echo "📚 More Commands:"
	@echo "  make help-all        Show all available commands"
	@echo "  make help-testing    Show testing commands"
	@echo "  make help-mcp        Show MCP/LLM commands"

help-all: ## Show all available commands
	@echo "🚁 DroneSphere v2.0 - All Commands"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}'

help-testing: ## Show testing commands
	@echo "🧪 DroneSphere Testing Commands"
	@echo "==============================="
	@echo ""
	@echo "Individual Component Tests:"
	@echo "  test-agent           Test all agent endpoints"
	@echo "  test-server          Test all server functionality"
	@echo "  test-commands        Test all drone commands"
	@echo "  test-navigation      Test GPS and NED navigation"
	@echo ""
	@echo "Comprehensive Test Suites:"
	@echo "  test-all             Run complete system test"
	@echo "  test-all-mcp         Run all tests + MCP integration"
	@echo ""
	@echo "Individual Command Tests:"
	@echo "  test-takeoff         Test takeoff command"
	@echo "  test-land            Test landing command"
	@echo "  test-goto-gps        Test GPS navigation"
	@echo "  test-goto-ned        Test relative navigation"
	@echo "  test-sequence        Test multi-command sequences"

help-mcp: ## Show MCP/LLM commands
	@echo "🧠 DroneSphere MCP/LLM Commands"
	@echo "==============================="
	@echo ""
	@echo "LLM System Management:"
	@echo "  dev-llm              Start complete LLM system"
	@echo "  mcp-install          Install MCP dependencies"
	@echo "  test-llm             Test LLM integration"
	@echo "  test-mcp-api         Test API key configuration"
	@echo ""
	@echo "🌍 Multi-Language Support:"
	@echo "  English: 'take off to 15 meters'"
	@echo "  Persian: 'بلند شو به 15 متر'"
	@echo "  Spanish: 'despegar a 15 metros'"
	@echo "  Status:  'what is the drone status?'"

# =============================================================================
# ENVIRONMENT SETUP - Dependencies and Installation
# =============================================================================

install-deps: ## Install all dependencies in separate environments
	@echo "📦 Installing dependencies for all components..."
	@echo "Installing agent dependencies..."
	@cd agent && .venv/bin/pip install -r requirements.txt
	@echo "Installing server dependencies..."
	@cd server && .venv/bin/pip install -r requirements.txt
	@echo "✅ All dependencies installed successfully"

mcp-install: ## Install MCP dependencies with proper environment
	@echo "📦 Installing MCP dependencies..."
	@cd mcp && rm -rf mcp-env && uv venv mcp-env
	@cd mcp && mcp-env/bin/python -m pip install --upgrade pip
	@cd mcp && mcp-env/bin/pip install -r requirements.txt
	@echo "✅ MCP dependencies installed in mcp-env"

# =============================================================================
# DOCKER SERVICES - Smart Container Management
# =============================================================================

sitl: ## Start SITL simulation (smart - reuse existing container)
	@echo "🚁 Starting SITL simulation..."
	@if docker ps -a --filter "name=dronesphere-sitl" --format "{{.Names}}" | grep -q dronesphere-sitl; then \
		if docker ps --filter "name=dronesphere-sitl" --format "{{.Names}}" | grep -q dronesphere-sitl; then \
			echo "✅ SITL already running"; \
		else \
			echo "🔄 Starting existing SITL container..."; \
			docker start dronesphere-sitl; \
		fi; \
	else \
		echo "🆕 Creating new SITL container..."; \
		docker run -d --rm --name dronesphere-sitl jonasvautherin/px4-gazebo-headless:latest; \
	fi

# =============================================================================
# INDIVIDUAL SERVICES - Manual Control
# =============================================================================

agent: ## Start agent only
	@echo "🤖 Starting DroneSphere Agent..."
	@cd agent && .venv/bin/python3 main.py

server: ## Start server only
	@echo "🖥️  Starting DroneSphere Server..."
	@cd server && .venv/bin/python3 main.py

mcp: ## Start pure MCP server (for Claude Desktop/n8n)
	@echo "🤖 Starting Pure MCP Server (stdio protocol)..."
	@echo "🔗 Connects to Claude Desktop, n8n, and other MCP tools"
	@cd mcp && mcp-env/bin/python server.py

mcp-web: ## Start MCP web interface
	@echo "🌐 Starting MCP Web Interface..."
	@echo "📱 Web interface: http://localhost:3001"
	@cd mcp && mcp-env/bin/python web_bridge_demo/web_bridge.py

# =============================================================================
# CLEANUP COMMANDS - Safe and Reliable
# =============================================================================

clean: ## Stop all services safely (primary cleanup method)
	@echo "🧹 Stopping all DroneSphere services..."
	@lsof -ti:8001 | xargs -r kill -TERM 2>/dev/null || true
	@lsof -ti:8002 | xargs -r kill -TERM 2>/dev/null || true
	@lsof -ti:3001 | xargs -r kill -TERM 2>/dev/null || true
	@sleep 1
	@echo "✅ All services stopped safely"

clean-mcp: ## Stop MCP processes only
	@echo "🧹 Stopping MCP processes..."
	@lsof -ti:3001 | xargs -r kill -TERM 2>/dev/null || true
	@echo "✅ MCP processes stopped"

docker-clean: ## Stop and remove docker containers
	@echo "🧹 Cleaning up docker containers..."
	@docker stop dronesphere-sitl 2>/dev/null || true
	@docker rm dronesphere-sitl 2>/dev/null || true
	@echo "✅ Docker containers cleaned"

clean-all: clean docker-clean ## Clean everything (processes + containers)

# =============================================================================
# DEVELOPMENT ENVIRONMENTS - Complete System Startup
# =============================================================================

dev: clean sitl ## Start basic development environment
	@echo "🚀 Starting basic development environment..."
	@sleep 5
	@echo "🤖 Starting agent..."
	@cd agent && nohup .venv/bin/python3 main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup .venv/bin/python3 main.py > /tmp/server.log 2>&1 &
	@sleep 2
	@echo "✅ Basic development environment ready!"
	@echo "📋 Logs: tail -f /tmp/agent.log /tmp/server.log"

dev-llm: clean sitl ## Start complete LLM system (RECOMMENDED)
	@echo "🚀 Starting complete LLM development environment..."
	@sleep 5
	@echo "🤖 Starting agent..."
	@cd agent && nohup .venv/bin/python main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup .venv/bin/python main.py > /tmp/server.log 2>&1 &
	@sleep 3
	@echo "🧠 Starting LLM web interface..."
	@cd mcp && nohup mcp-env/bin/python web_bridge_demo/web_bridge.py > /tmp/mcp.log 2>&1 &
	@sleep 2
	@echo "✅ Complete LLM system ready!"
	@echo ""
	@echo "🌐 Web Interface: http://localhost:3001"
	@echo "🌍 Multi-language AI drone control active"
	@echo ""
	@echo "📋 Logs available:"
	@echo "  Agent:  tail -f /tmp/agent.log"
	@echo "  Server: tail -f /tmp/server.log"
	@echo "  MCP:    tail -f /tmp/mcp.log"
	@echo ""
	@echo "🎯 Ready for testing: make test-demo"

dev-mcp: clean sitl ## Start system for pure MCP connections
	@echo "🚀 Starting development environment for MCP connections..."
	@sleep 5
	@echo "🤖 Starting agent..."
	@cd agent && nohup .venv/bin/python main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup .venv/bin/python main.py > /tmp/server.log 2>&1 &
	@sleep 2
	@echo "✅ System ready for MCP connections!"
	@echo ""
	@echo "🎯 Next steps:"
	@echo "  For Claude Desktop: make claude-config"
	@echo "  For Web Browser:    make mcp-web"

# =============================================================================
# STATUS COMMANDS - System Monitoring
# =============================================================================

status: ## Show basic system status
	@echo "📊 DroneSphere Basic Status"
	@echo "==========================="
	@echo -n "SITL Container: "
	@docker ps --filter "name=dronesphere-sitl" --format "{{.Status}}" 2>/dev/null | head -1 || echo "❌ Not running"
	@echo -n "Agent (8001): "
	@lsof -i:8001 >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Stopped"
	@echo -n "Server (8002): "
	@lsof -i:8002 >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Stopped"

status-full: ## Show complete system status including LLM
	@echo "📊 DroneSphere Complete System Status"
	@echo "====================================="
	@echo -n "SITL Container: "
	@docker ps --filter "name=dronesphere-sitl" --format "{{.Status}}" 2>/dev/null | head -1 || echo "❌ Not running"
	@echo ""
	@echo "Core Services:"
	@echo -n "  Agent (8001):     "
	@lsof -i:8001 >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Stopped"
	@echo -n "  Server (8002):    "
	@lsof -i:8002 >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Stopped"
	@echo -n "  MCP Web (3001):   "
	@lsof -i:3001 >/dev/null 2>&1 && echo "✅ Running" || echo "❌ Stopped"
	@echo ""
	@echo "Health Checks:"
	@echo -n "  Agent API:        "
	@curl -s http://localhost:8001/health >/dev/null 2>&1 && echo "✅ Responding" || echo "❌ No response"
	@echo -n "  Server API:       "
	@curl -s http://localhost:8002/health >/dev/null 2>&1 && echo "✅ Responding" || echo "❌ No response"
	@echo -n "  MCP Interface:    "
	@curl -s http://localhost:3001/ >/dev/null 2>&1 && echo "✅ Responding" || echo "❌ No response"
	@echo ""
	@echo "LLM Integration:"
	@echo -n "  API Key:          "
	@cd mcp && mcp-env/bin/python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Configured' if (os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')) else '❌ Missing')" 2>/dev/null || echo "❌ Error"

# =============================================================================
# BASIC HEALTH TESTS - Component Testing
# =============================================================================

test-health: ## Test agent health endpoint
	@echo "🔍 Testing agent health endpoint..."
	@curl -s http://localhost:8001/health | python3 -m json.tool || echo "❌ Agent health check failed"

test-ping: ## Test agent ping endpoint
	@echo "🏓 Testing agent ping endpoint..."
	@curl -s http://localhost:8001/ping | python3 -m json.tool || echo "❌ Agent ping failed"

test-detailed: ## Test detailed health endpoint
	@echo "🔍 Testing detailed health endpoint..."
	@curl -s http://localhost:8001/health/detailed | python3 -m json.tool || echo "❌ Detailed health check failed"

test-telemetry: ## Test telemetry endpoint
	@echo "📡 Testing telemetry endpoint..."
	@curl -s http://localhost:8001/telemetry | python3 -m json.tool || echo "❌ Telemetry not available"

test-agent: test-health test-ping test-detailed test-telemetry ## Test all agent endpoints

# =============================================================================
# SERVER TESTS - Fleet Management Testing
# =============================================================================

test-server-health: ## Test server health endpoint
	@echo "🖥️  Testing server health endpoint..."
	@curl -s http://localhost:8002/health | python3 -m json.tool || echo "❌ Server health check failed"

test-fleet-health: ## Test fleet health endpoint
	@echo "👥 Testing fleet health endpoint..."
	@curl -s http://localhost:8002/fleet/health | python3 -m json.tool || echo "❌ Fleet health check failed"

test-fleet-registry: ## Test fleet registry endpoint
	@echo "📋 Testing fleet registry endpoint..."
	@curl -s http://localhost:8002/fleet/registry | python3 -m json.tool || echo "❌ Fleet registry failed"

test-server-takeoff: ## Test takeoff via server routing
	@echo "🚀 Testing server-routed takeoff command..."
	@curl -X POST http://localhost:8002/fleet/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10},"mode":"continue"}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Server takeoff command failed"

test-server: test-server-health test-fleet-health test-fleet-registry ## Test server functionality
test-fleet: test-server-takeoff ## Test fleet routing capabilities

# =============================================================================
# COMMAND TESTS - Individual Drone Commands
# =============================================================================

test-takeoff: ## Test takeoff command
	@echo "🚀 Testing takeoff command..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10},"mode":"continue"}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Takeoff command failed"

test-land: ## Test land command
	@echo "🛬 Testing land command..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"land","params":{},"mode":"continue"}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Land command failed"

test-rtl: ## Test RTL (Return to Launch) command
	@echo "🏠 Testing RTL command..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"rtl","params":{},"mode":"continue"}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ RTL command failed"

test-wait: ## Test wait command
	@echo "⏱️  Testing wait command..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"wait","params":{"duration":2,"message":"Testing wait functionality"}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Wait command failed"

test-commands: test-takeoff test-land test-rtl test-wait ## Test all basic drone commands

# =============================================================================
# NAVIGATION TESTS - GPS and NED Coordinate Systems
# =============================================================================

test-goto-gps: ## Test GPS coordinate navigation (Zurich example)
	@echo "🗺️  Testing GPS navigation: 47.398, 8.546, 503m MSL (15m above ground)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0,"speed":3}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ GPS navigation failed"

test-goto-ned: ## Test NED coordinate navigation (relative positioning)
	@echo "🧭 Testing NED navigation: N=50m, E=30m, D=-15m (15m above origin)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"north":50,"east":30,"down":-15}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ NED navigation failed"

test-goto: test-goto-gps test-goto-ned ## Test both GPS and NED navigation systems

# =============================================================================
# ROBUSTNESS TESTS - Safety and Error Handling
# =============================================================================

test-robustness: ## Test system robustness (invalid commands should fail gracefully)
	@echo "🛡️  Testing robustness: goto when on ground (should fail safely)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0}}],"target_drone":1}' \
		| python3 -m json.tool

# =============================================================================
# SEQUENCE TESTS - Multi-Command Operations
# =============================================================================

test-sequence: ## Test basic command sequence (takeoff + land)
	@echo "🎯 Testing basic sequence: takeoff → land..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10}},{"name":"land","params":{}}],"queue_mode":"override","target_drone":1}' \
		| python3 -m json.tool || echo "❌ Basic sequence failed"

test-navigation: ## Test complex navigation sequence
	@echo "🗺️  Testing navigation sequence: takeoff → GPS → wait → NED → land..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":15}},{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0}},{"name":"wait","params":{"duration":3}},{"name":"goto","params":{"north":20,"east":10,"down":-20}},{"name":"land","params":{}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Navigation sequence failed"

# =============================================================================
# MCP/LLM INTEGRATION TESTS - AI and Natural Language
# =============================================================================

test-mcp-api: ## Test MCP API key configuration
	@echo "🔑 Testing MCP API Configuration..."
	@echo "=================================="
	@cd mcp && test -f mcp-env/bin/python && mcp-env/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ OpenRouter API Key:', 'SET' if os.getenv('OPENROUTER_API_KEY') else '❌ NOT SET'); print('✅ OpenAI API Key:', 'SET' if os.getenv('OPENAI_API_KEY') else '❌ NOT SET')" 2>/dev/null || echo "❌ MCP environment not ready - run 'make mcp-install'"

test-llm: ## Test LLM integration and libraries
	@echo "🧪 Testing LLM Integration..."
	@echo "============================"
	@cd mcp && mcp-env/bin/python -c "import os; from dotenv import load_dotenv; load_dotenv(); key = os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY'); print('✅ API Key configured') if key else print('❌ No API key found'); print('✅ OpenAI library available') if __import__('openai') else print('❌ OpenAI library missing')" 2>/dev/null || echo "❌ LLM environment not ready"

test-mcp-web: ## Test MCP web interface integration
	@echo "🧪 Testing MCP Web Integration..."
	@echo "================================"
	@echo -n "Web interface accessible: "
	@curl -s http://localhost:3001/ >/dev/null 2>&1 && echo "✅ YES" || echo "❌ NO"
	@echo -n "Status endpoint working: "
	@curl -s http://localhost:3001/status/1 >/dev/null 2>&1 && echo "✅ YES" || echo "❌ NO"
	@echo ""
	@echo "🎯 Manual Test Instructions:"
	@echo "1. Open browser: http://localhost:3001"
	@echo "2. Try: 'take off to 15 meters'"
	@echo "3. Try: 'بلند شو به 15 متر' (Persian)"
	@echo "4. Try: 'what is the drone status?'"

test-demo: ## Test complete demo system readiness
	@echo "🎬 Testing Complete Demo System"
	@echo "==============================="
	@make status-full
	@echo ""
	@echo "🎯 Demo System Ready!"
	@echo "Web Interface: http://localhost:3001"
	@echo ""
	@echo "✅ Test these commands in browser:"
	@echo "  English: 'take off to 15 meters'"
	@echo "  Persian: 'بلند شو به 15 متر'"
	@echo "  Status:  'what is the drone status?'"
	@echo "  Land:    'land the drone'"
	@echo ""
	@echo "🔄 Advanced (if implemented):"
	@echo "  'wait 5 seconds'"
	@echo "  'return home'"
	@echo "  'go 50 meters north'"
	@echo "  'take off to 15m, wait 3s, then land'"

# =============================================================================
# COMPREHENSIVE TEST SUITES - Complete System Validation
# =============================================================================

test-all: test-agent test-server test-fleet test-commands test-goto test-sequence test-navigation ## Run complete system test suite

test-all-mcp: test-all test-mcp-api test-llm test-mcp-web ## Run all tests including MCP integration

# =============================================================================
# CLAUDE DESKTOP SETUP - Future MCP Integration
# =============================================================================

claude-config: ## Generate Claude Desktop MCP configuration
	@echo "🖥️  Generating Claude Desktop MCP configuration..."
	@echo "Current directory: $(shell pwd)"
	@mkdir -p mcp
	@cat > mcp/claude_desktop_config.json << 'EOF'
	{
	"mcpServers": {
		"dronesphere": {
		"command": "python",
		"args": ["$(shell pwd)/mcp/server.py"],
		"cwd": "$(shell pwd)/mcp",
		"env": {
			"PYTHONPATH": "$(shell pwd)"
		}
		}
	}
	}
	EOF
	@echo "✅ Configuration generated: mcp/claude_desktop_config.json"
	@echo ""
	@echo "📝 Setup Instructions:"
	@echo "1. Copy content to Claude Desktop config file:"
	@echo "   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
	@echo "   Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
	@echo "   Linux: ~/.config/Claude/claude_desktop_config.json"
	@echo ""
	@echo "2. Restart Claude Desktop"
	@echo "3. Try: 'Take off drone 1 to 15 meters'"

# =============================================================================
# DEVELOPMENT UTILITIES - Debugging and Monitoring
# =============================================================================

show-logs: ## Show live logs from all services
	@echo "📋 Live Logs from All Services"
	@echo "=============================="
	@echo "Press Ctrl+C to stop"
	@tail -f /tmp/agent.log /tmp/server.log /tmp/mcp.log 2>/dev/null || echo "No log files found - services may not be running"

show-processes: ## Show all DroneSphere-related processes
	@echo "🔍 DroneSphere Process Information"
	@echo "================================="
	@echo "Processes using our ports:"
	@lsof -i:8001,8002,3001 2>/dev/null || echo "No processes on our ports"
	@echo ""
	@echo "All Python processes in DroneSphere directory:"
	@ps aux | grep python | grep dronesphere | grep -v grep || echo "No DroneSphere Python processes found"

debug-ports: ## Debug port usage and conflicts
	@echo "🔧 Port Usage Debug Information"
	@echo "==============================="
	@echo "Port 8001 (Agent):"
	@lsof -i:8001 2>/dev/null || echo "  Port 8001 is free"
	@echo "Port 8002 (Server):"
	@lsof -i:8002 2>/dev/null || echo "  Port 8002 is free"
	@echo "Port 3001 (MCP):"
	@lsof -i:3001 2>/dev/null || echo "  Port 3001 is free"
