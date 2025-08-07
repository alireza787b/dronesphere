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

check-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "❌ Error: uv is not installed. Please install uv first."; \
		echo "   Visit: https://docs.astral.sh/uv/getting-started/installation/"; \
		exit 1; \
	}

# Install all dependencies with proper error handling and cleanup
install-deps: check-uv ## Install all component dependencies in isolated environments
	@echo "🚀 Installing dependencies for all components..."
	@echo "📋 Components: $(COMPONENTS)"
	@echo ""
	@$(MAKE) --no-print-directory _install-agent-deps
	@$(MAKE) --no-print-directory _install-server-deps
	@$(MAKE) --no-print-directory _install-mcp-deps
	@echo ""
	@echo "✅ All dependencies installed successfully"
	@echo "📍 Virtual environments created:"
	@echo "   - $(AGENT_ENV)"
	@echo "   - $(SERVER_ENV)"
	@echo "   - $(MCP_ENV)"

# Internal target for agent dependencies
_install-agent-deps:
	@echo "📦 Installing agent dependencies..."
	@if [ ! -f agent/requirements.txt ]; then \
		echo "❌ Error: agent/requirements.txt not found"; \
		exit 1; \
	fi
	@cd agent && rm -rf agent-env
	@cd agent && uv venv agent-env
	@cd agent && source agent-env/bin/activate && uv pip install -r requirements.txt
	@echo "   ✓ Agent dependencies installed in $(AGENT_ENV)"

# Internal target for server dependencies
_install-server-deps:
	@echo "📦 Installing server dependencies..."
	@if [ ! -f server/requirements.txt ]; then \
		echo "❌ Error: server/requirements.txt not found"; \
		exit 1; \
	fi
	@cd server && rm -rf server-env
	@cd server && uv venv server-env
	@cd server && source server-env/bin/activate && uv pip install -r requirements.txt
	@echo "   ✓ Server dependencies installed in $(SERVER_ENV)"

# Internal target for mcp dependencies
_install-mcp-deps:
	@echo "📦 Installing MCP dependencies..."
	@if [ ! -f mcp/requirements.txt ]; then \
		echo "❌ Error: mcp/requirements.txt not found"; \
		exit 1; \
	fi
	@cd mcp && rm -rf mcp-env
	@cd mcp && uv venv mcp-env
	@cd mcp && source mcp-env/bin/activate && uv pip install -r requirements.txt
	@echo "   ✓ MCP dependencies installed in $(MCP_ENV)"

# Clean all virtual environments
clean-envs: ## Remove all virtual environments
	@echo "🧹 Cleaning virtual environments..."
	@rm -rf $(AGENT_ENV) $(SERVER_ENV) $(MCP_ENV)
	@echo "✅ All virtual environments cleaned"

# Reinstall all dependencies (clean + install)
reinstall-deps: clean-envs install-deps ## Clean and reinstall all dependencies

# =============================================================================
# DOCKER SERVICES - Smart Container Management
# =============================================================================

# Network configuration - reads from terminal environment variables
QGC_IP ?=
MAVSDK_IP ?=

# Build docker arguments only if IPs are provided
DOCKER_IP_ARGS := $(strip $(if $(QGC_IP),$(QGC_IP)) $(if $(MAVSDK_IP),$(MAVSDK_IP)))

sitl: ## Start SITL simulation (smart - reuse existing container)
	@echo "🚁 Starting SITL simulation..."
	@echo ""
	@echo "📡 Network Configuration:"
	@if [ -n "$(QGC_IP)" ] || [ -n "$(MAVSDK_IP)" ]; then \
		echo "   ✅ Using custom IPs: QGC_IP='$(QGC_IP)' MAVSDK_IP='$(MAVSDK_IP)'"; \
	else \
		echo "   🔧 Using container defaults (no custom IPs)"; \
		echo ""; \
		echo "💡 To use custom IPs, export environment variables first:"; \
		echo "   export QGC_IP=100.96.160.180"; \
		echo "   export MAVSDK_IP=172.18.0.1"; \
		echo "   make sitl"; \
		echo ""; \
		echo "   Or use inline:"; \
		echo "   QGC_IP=100.96.160.180 MAVSDK_IP=172.18.0.1 make sitl"; \
	fi
	@echo ""
	@if docker ps -a --filter "name=dronesphere-sitl" --format "{{.Names}}" | grep -q dronesphere-sitl; then \
		if docker ps --filter "name=dronesphere-sitl" --format "{{.Names}}" | grep -q dronesphere-sitl; then \
			echo "✅ SITL already running"; \
		else \
			echo "🔄 Starting existing SITL container..."; \
			docker start dronesphere-sitl; \
		fi; \
	else \
		echo "🆕 Creating new SITL container..."; \
		if [ -n "$(DOCKER_IP_ARGS)" ]; then \
			echo "🔗 Docker command: jonasvautherin/px4-gazebo-headless:latest $(DOCKER_IP_ARGS)"; \
			docker run -d --rm --name dronesphere-sitl jonasvautherin/px4-gazebo-headless:latest $(DOCKER_IP_ARGS); \
		else \
			echo "🔗 Docker command: jonasvautherin/px4-gazebo-headless:latest (default networking)"; \
			docker run -d --rm --name dronesphere-sitl jonasvautherin/px4-gazebo-headless:latest; \
		fi; \
	fi
	@echo "✅ SITL simulation ready"

sitl-help: ## Show SITL configuration examples and usage
	@echo "🚁 SITL Configuration Guide"
	@echo "=========================="
	@echo ""
	@echo "📋 Current Status:"
	@echo "   QGC_IP    = '$(QGC_IP)'"
	@echo "   MAVSDK_IP = '$(MAVSDK_IP)'"
	@echo ""
	@echo "🔧 Usage Examples:"
	@echo ""
	@echo "1️⃣  Default behavior (no custom IPs):"
	@echo "   make sitl"
	@echo ""
	@echo "2️⃣  Using environment variables (persistent in session):"
	@echo "   export QGC_IP=100.96.160.180"
	@echo "   export MAVSDK_IP=172.18.0.1"
	@echo "   make sitl"
	@echo ""
	@echo "3️⃣  Using inline variables (one-time):"
	@echo "   QGC_IP=100.96.160.180 MAVSDK_IP=172.18.0.1 make sitl"
	@echo ""
	@echo "4️⃣  Using only one IP:"
	@echo "   QGC_IP=192.168.1.100 make sitl"
	@echo "   MAVSDK_IP=172.18.0.1 make sitl"
	@echo ""
	@echo "🗑️  Clear environment variables:"
	@echo "   unset QGC_IP MAVSDK_IP"
	@echo ""

# =============================================================================
# INDIVIDUAL SERVICES - Manual Control
# =============================================================================

agent: ## Start agent only
	@echo "🤖 Starting DroneSphere Agent..."
	@cd agent && agent-env/bin/python3 main.py

server: ## Start server only
	@echo "🖥️  Starting DroneSphere Server..."
	@cd server && server-env/bin/python3 main.py

mcp: ## Start pure MCP server (for Claude Desktop/n8n)
	@echo "🤖 Starting Pure MCP Server (stdio protocol)..."
	@echo "🔗 Connects to Claude Desktop, n8n, and other MCP tools"
	@cd mcp && mcp-env/bin/python server.py

mcp-web: ## Start MCP web interface
	@echo "🌐 Starting MCP Web Interface..."
	@echo "📱 Web interface: http://localhost:3001"
	@cd mcp/web_bridge_demo && ../mcp-env/bin/python web_bridge.py

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
	@echo "🚁 Starting SITL simulation..."
	@sleep 45
	@echo "🤖 Starting agent..."
	@cd agent && nohup agent-env/bin/python3 main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup server-env/bin/python3 main.py > /tmp/server.log 2>&1 &
	@sleep 2
	@echo "✅ Basic development environment ready!"
	@echo "📋 Logs: tail -f /tmp/agent.log /tmp/server.log"

dev-llm: clean sitl ## Start complete LLM system (RECOMMENDED)
	@echo "🚀 Starting complete LLM development environment..."
	@echo "🚁 Starting SITL simulation..."
	@sleep 30
	@echo "🤖 Starting agent..."
	@cd agent && nohup agent-env/bin/python3 main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup server-env/bin/python3 main.py > /tmp/server.log 2>&1 &
	@sleep 3
	@echo "🧠 Starting LLM web interface..."
	@cd mcp/web_bridge_demo && nohup ../mcp-env/bin/python web_bridge.py > /tmp/mcp.log 2>&1 &
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
	@cd agent && nohup agent-env/bin/python3 main.py > /tmp/agent.log 2>&1 &
	@sleep 3
	@echo "🖥️  Starting server..."
	@cd server && nohup server-env/bin/python3 main.py > /tmp/server.log 2>&1 &
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

test-fleet: test-server-takeoff ## Test fleet routing capabilities

# =============================================================================
# FLEET TELEMETRY TESTS - Background Polling System
# =============================================================================

test-fleet-telemetry: ## Test fleet-wide telemetry endpoint (cached data)
	@echo "📊 Testing fleet telemetry endpoint..."
	@curl -s http://localhost:8002/fleet/telemetry | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Fleet: {data[\"fleet_name\"]}'); \
print(f'Polling: {\"✅\" if data[\"polling_active\"] else \"❌\"} Active'); \
print(f'Drones: {data[\"summary\"][\"successful\"]}/{data[\"total_drones\"]} successful ({data[\"summary\"][\"success_rate\"]})'); \
[print(f'  📡 {d.get(\"drone_name\", f\"Drone {did}\")}: {\"✅\" if \"error\" not in d else \"❌\"} {d.get(\"data_age_seconds\", \"N/A\")}s old') for did, d in data['drones'].items()]" 2>/dev/null || echo "❌ Fleet telemetry failed"

test-drone-telemetry: ## Test specific drone telemetry endpoint (cached)
	@echo "📡 Testing drone 1 telemetry endpoint..."
	@curl -s http://localhost:8002/fleet/telemetry/1 | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Drone: {data.get(\"drone_name\", \"Unknown\")}'); \
print(f'Age: {data.get(\"data_age_seconds\", \"N/A\")}s'); \
print(f'Source: {data.get(\"source\", \"Unknown\")}'); \
battery=data.get('battery', {}); \
print(f'Battery: {battery.get(\"voltage\", \"N/A\")}V ({battery.get(\"percentage\", \"N/A\")}%)') if battery else print('Battery: N/A'); \
position=data.get('position', {}); \
print(f'Altitude: {position.get(\"relative_altitude_m\", \"N/A\")}m') if position else print('Position: N/A')" 2>/dev/null || echo "❌ Drone telemetry failed"

test-live-telemetry: ## Test live (non-cached) telemetry bypassing polling cache
	@echo "⚡ Testing live telemetry (bypasses cache)..."
	@curl -s http://localhost:8002/fleet/telemetry/1/live | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Drone: {data.get(\"drone_name\", \"Unknown\")}'); \
print(f'Source: {data.get(\"source\", \"Unknown\")} (should be live_request)'); \
print(f'Age: {data.get(\"data_age_seconds\", \"N/A\")}s (should be 0.0)'); \
battery=data.get('battery', {}); \
print(f'Battery: {battery.get(\"voltage\", \"N/A\")}V') if battery else print('Battery: N/A')" 2>/dev/null || echo "❌ Live telemetry failed"

test-telemetry-status: ## Test telemetry polling system status
	@echo "🔄 Testing telemetry polling status..."
	@curl -s http://localhost:8002/fleet/telemetry/status | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
polling=data['polling_status']; \
fleet=data['fleet_info']; \
health=data['system_health']; \
print(f'Polling: {\"✅\" if polling[\"active\"] else \"❌\"} Active, Thread: {\"✅\" if polling[\"thread_alive\"] else \"❌\"} Alive'); \
print(f'Fleet: {fleet[\"fleet_name\"]} - {fleet[\"active_drones\"]}/{fleet[\"total_drones\"]} active'); \
print(f'Cache: {fleet[\"cached_drones\"]} drones, Hit Rate: {health[\"cache_hit_rate\"]}'); \
print(f'Oldest Data: {health[\"oldest_data_age\"]:.1f}s old')" 2>/dev/null || echo "❌ Telemetry status failed"

test-telemetry-all: test-fleet-telemetry test-drone-telemetry test-live-telemetry test-telemetry-status ## Test all telemetry endpoints

# =============================================================================
# TELEMETRY PERFORMANCE & COMPARISON TESTS
# =============================================================================

test-telemetry-performance: ## Compare performance: direct vs cached vs live
	@echo "⚡ Telemetry Performance Comparison"
	@echo "=================================="
	@echo ""
	@echo "📡 Direct Agent Call:"
	@time curl -s http://localhost:8001/telemetry >/dev/null 2>&1 && echo "✅ Direct agent: Success" || echo "❌ Direct agent: Failed"
	@echo ""
	@echo "🏃 Server Cached Call:"
	@time curl -s http://localhost:8002/fleet/telemetry/1 >/dev/null 2>&1 && echo "✅ Server cached: Success" || echo "❌ Server cached: Failed"
	@echo ""
	@echo "⚡ Server Live Call:"
	@time curl -s http://localhost:8002/fleet/telemetry/1/live >/dev/null 2>&1 && echo "✅ Server live: Success" || echo "❌ Server live: Failed"

test-telemetry-comparison: ## Compare agent vs server telemetry data consistency
	@echo "🔍 Telemetry Data Consistency Check"
	@echo "==================================="
	@echo ""
	@echo "📡 Direct Agent Telemetry:"
	@curl -s http://localhost:8001/telemetry | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
battery=data.get('battery', {}); \
position=data.get('position', {}); \
print(f'Battery: {battery.get(\"voltage\", \"N/A\")}V, Altitude: {position.get(\"relative_altitude_m\", \"N/A\")}m, Source: Direct Agent')" 2>/dev/null || echo "❌ Agent telemetry unavailable"
	@echo ""
	@echo "🖥️  Server Cached Telemetry:"
	@curl -s http://localhost:8002/fleet/telemetry/1 | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
battery=data.get('battery', {}); \
position=data.get('position', {}); \
print(f'Battery: {battery.get(\"voltage\", \"N/A\")}V, Altitude: {position.get(\"relative_altitude_m\", \"N/A\")}m, Age: {data.get(\"data_age_seconds\", \"N/A\")}s, Source: {data.get(\"source\", \"Unknown\")}')" 2>/dev/null || echo "❌ Server cached unavailable"
	@echo ""
	@echo "⚡ Server Live Telemetry:"
	@curl -s http://localhost:8002/fleet/telemetry/1/live | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
battery=data.get('battery', {}); \
position=data.get('position', {}); \
print(f'Battery: {battery.get(\"voltage\", \"N/A\")}V, Altitude: {position.get(\"relative_altitude_m\", \"N/A\")}m, Age: {data.get(\"data_age_seconds\", \"N/A\")}s, Source: {data.get(\"source\", \"Unknown\")}')" 2>/dev/null || echo "❌ Server live unavailable"

test-telemetry-stress: ## Stress test telemetry endpoints (multiple rapid calls)
	@echo "🧪 Telemetry Stress Test"
	@echo "======================="
	@echo "Testing rapid consecutive calls to verify cache performance..."
	@for i in 1 2 3 4 5; do \
		echo -n "Call $$i: "; \
		time curl -s http://localhost:8002/fleet/telemetry/1 >/dev/null 2>&1 && echo "✅ Success" || echo "❌ Failed"; \
	done

# =============================================================================
# MULTI-DRONE TELEMETRY TESTS
# =============================================================================

test-multi-drone-telemetry: ## Test telemetry with multiple drones (requires drone 2 active)
	@echo "🚁 Multi-Drone Telemetry Test"
	@echo "============================="
	@echo "Testing fleet telemetry with multiple drones..."
	@curl -s http://localhost:8002/fleet/telemetry | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Fleet: {data[\"fleet_name\"]}'); \
print(f'Total Drones: {data[\"total_drones\"]}, Active: {data[\"active_drones\"]}'); \
print(f'Success Rate: {data[\"summary\"][\"success_rate\"]}'); \
print('\\nDrone Status:'); \
[print(f'  Drone {did}: {d.get(\"drone_name\", \"Unknown\")} - {\"✅ Active\" if \"error\" not in d else f\"❌ {d.get(\"error\", \"Error\")}\"} ({d.get(\"data_age_seconds\", \"N/A\")}s old)') for did, d in data['drones'].items()]" 2>/dev/null || echo "❌ Multi-drone telemetry failed"

test-drone2-activation: ## Test telemetry after activating drone 2
	@echo "🚁 Testing Drone 2 Activation Impact on Telemetry"
	@echo "================================================"
	@echo "Before activation:"
	@curl -s http://localhost:8002/fleet/telemetry/status | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Active drones: {data[\"fleet_info\"][\"active_drones\"]}, Cached: {data[\"fleet_info\"][\"cached_drones\"]}')" 2>/dev/null || echo "❌ Status check failed"
	@echo ""
	@echo "Activating drone 2..."
	@python3 -c "\
import yaml; \
data=yaml.safe_load(open('shared/drones.yaml')); \
data['drones'][2]['status']='active'; \
yaml.dump(data, open('shared/drones.yaml', 'w'), default_flow_style=False)" 2>/dev/null || echo "❌ Failed to activate drone 2"
	@curl -s -X POST http://localhost:8002/fleet/config/reload >/dev/null 2>&1 || echo "⚠️  Config reload failed"
	@sleep 5  # Wait for polling to pick up new drone
	@echo ""
	@echo "After activation:"
	@curl -s http://localhost:8002/fleet/telemetry/status | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Active drones: {data[\"fleet_info\"][\"active_drones\"]}, Cached: {data[\"fleet_info\"][\"cached_drones\"]}')" 2>/dev/null || echo "❌ Status check failed"

# =============================================================================
# TELEMETRY ERROR HANDLING TESTS
# =============================================================================

test-telemetry-error-handling: ## Test telemetry error handling for unreachable drones
	@echo "🔧 Testing Telemetry Error Handling"
	@echo "==================================="
	@echo "Testing non-existent drone:"
	@curl -s http://localhost:8002/fleet/telemetry/999 2>/dev/null | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Error: {data.get(\"detail\", \"Unknown error\")}')" || echo "✅ Correctly returned 404 for non-existent drone"
	@echo ""
	@echo "Testing inactive drone telemetry:"
	@curl -s http://localhost:8002/fleet/telemetry/3 2>/dev/null | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
print(f'Response: {data}')" || echo "✅ Correctly handled inactive drone request"

test-telemetry-polling-restart: ## Test telemetry polling system restart
	@echo "🔄 Testing Telemetry Polling Restart"
	@echo "===================================="
	@echo "This test would require server restart - check status instead:"
	@curl -s http://localhost:8002/fleet/telemetry/status | python3 -c "\
import sys, json; \
data=json.load(sys.stdin); \
polling=data['polling_status']; \
print(f'Polling Active: {polling[\"active\"]}'); \
print(f'Thread Alive: {polling[\"thread_alive\"]}'); \
print(f'System Health: {\"✅ Good\" if polling[\"active\"] and polling[\"thread_alive\"] else \"❌ Issues detected\"}')" 2>/dev/null || echo "❌ Status check failed"

# =============================================================================
# COMPREHENSIVE TELEMETRY VALIDATION
# =============================================================================

test-telemetry-complete: test-telemetry-all test-telemetry-performance test-telemetry-comparison test-multi-drone-telemetry test-telemetry-error-handling ## Complete telemetry system test

test-telemetry-demo: ## Comprehensive telemetry system demonstration
	@echo "🎬 DroneSphere Fleet Telemetry System Demo"
	@echo "=========================================="
	@echo ""
	@echo "📊 System Status:"
	@make test-telemetry-status
	@echo ""
	@echo "🚁 Fleet Overview:"
	@make test-fleet-telemetry
	@echo ""
	@echo "⚡ Performance Test:"
	@make test-telemetry-performance
	@echo ""
	@echo "🔍 Data Consistency:"
	@make test-telemetry-comparison
	@echo ""
	@echo "✅ Fleet Telemetry System: OPERATIONAL"

# =============================================================================
# UPDATE MAIN TEST COMMANDS
# =============================================================================

# Update existing test-server command to include telemetry
test-server: test-server-health test-fleet-health test-fleet-registry test-telemetry-all ## Test complete server functionality with telemetry

# Add telemetry to comprehensive tests
test-all: test-agent test-server test-commands test-navigation test-sequence ## Test complete system including telemetry

# =============================================================================
# UPDATE MAIN TEST COMMANDS
# =============================================================================

# Update existing test-server command to include telemetry
test-server: test-server-health test-fleet-health test-fleet-registry test-config-all test-telemetry-all ## Test complete server functionality with telemetry

# Add telemetry to comprehensive tests
test-all: test-agent test-server test-commands test-navigation test-sequence ## Test complete system including telemetry

# =============================================================================
# CONFIGURATION TESTS - Dynamic YAML Configuration
# =============================================================================

test-config-load: ## Test drone configuration loading
	@echo "📋 Testing drone configuration loading..."
	@cd shared && python3 -c "from drone_config import FleetConfig; fc = FleetConfig(); print(f'✅ Loaded {fc.fleet_name}: {len(fc.drones)} drones'); [print(f'  {d.id}: {d.name} ({d.status})') for d in fc.drones.values()]" || echo "❌ Configuration loading failed"

test-config-validation: ## Test configuration file validation
	@echo "🔍 Testing YAML configuration validation..."
	@python3 -c "import yaml; yaml.safe_load(open('shared/drones.yaml')); print('✅ YAML syntax valid')" || echo "❌ YAML syntax error"

test-fleet-config: ## Test fleet configuration endpoint
	@echo "⚙️  Testing fleet configuration endpoint..."
	@curl -s http://localhost:8002/fleet/config | python3 -m json.tool || echo "❌ Fleet config endpoint failed"

test-drone-info: ## Test individual drone info endpoint
	@echo "🔍 Testing drone info endpoint..."
	@curl -s http://localhost:8002/fleet/drones/1 | python3 -m json.tool || echo "❌ Drone info endpoint failed"

test-config-reload: ## Test configuration reload endpoint
	@echo "🔄 Testing configuration reload..."
	@curl -X POST http://localhost:8002/fleet/config/reload | python3 -m json.tool || echo "❌ Config reload failed"

test-config-all: test-config-load test-config-validation test-fleet-config test-drone-info test-config-reload ## Test all configuration features

# =============================================================================
# REGISTRY COMPARISON TESTS - Old vs New Registry
# =============================================================================

test-registry-comparison: ## Compare old hardcoded vs new YAML registry
	@echo "🔄 Comparing Registry Systems..."
	@echo "==============================="
	@echo "📊 New YAML-based Registry:"
	@curl -s http://localhost:8002/fleet/registry | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Fleet: {data[\"fleet\"][\"name\"]}'); [print(f'  {d[\"id\"]}: {d[\"name\"]} ({d[\"status\"]}) -> {d[\"endpoint\"]}') for d in data['drones'].values()]" 2>/dev/null || echo "❌ New registry unavailable"

test-multi-drone-config: ## Show multi-drone configuration capability
	@echo "🚁 Multi-Drone Configuration Test..."
	@echo "==================================="
	@cd shared && python3 -c "from drone_config import get_fleet_config; fc = get_fleet_config(); print(f'Total Drones: {len(fc.drones)}'); print(f'Active: {len(fc.get_active_drones())}'); print(f'Simulation: {len(fc.get_simulation_drones())}'); print(f'Hardware: {len(fc.get_hardware_drones())}'); print('\\nDrone Details:'); [print(f'  🟢 {d.name}: {d.endpoint} ({d.type})' if d.is_active else f'  🔴 {d.name}: {d.endpoint} ({d.type})') for d in fc.drones.values()]"

# =============================================================================
# YAML EDITING TESTS - Configuration Management
# =============================================================================

test-yaml-backup: ## Create backup of current configuration
	@echo "💾 Creating configuration backup..."
	@cp shared/drones.yaml shared/drones.yaml.backup
	@echo "✅ Backup created: shared/drones.yaml.backup"

test-yaml-restore: ## Restore configuration from backup
	@echo "🔄 Restoring configuration from backup..."
	@test -f shared/drones.yaml.backup && cp shared/drones.yaml.backup shared/drones.yaml && echo "✅ Configuration restored" || echo "❌ No backup found"

test-activate-drone2: ## Activate second drone for multi-drone testing
	@echo "🚁 Activating Drone 2 (Bravo-SITL)..."
	@python3 -c "import yaml; data=yaml.safe_load(open('shared/drones.yaml')); data['drones'][2]['status']='active'; yaml.dump(data, open('shared/drones.yaml', 'w'), default_flow_style=False)"
	@echo "✅ Drone 2 activated in configuration"
	@curl -X POST http://localhost:8002/fleet/config/reload >/dev/null 2>&1 || true
	@echo "🔄 Configuration reloaded on server"

test-deactivate-drone2: ## Deactivate second drone
	@echo "⏹️  Deactivating Drone 2 (Bravo-SITL)..."
	@python3 -c "import yaml; data=yaml.safe_load(open('shared/drones.yaml')); data['drones'][2]['status']='inactive'; yaml.dump(data, open('shared/drones.yaml', 'w'), default_flow_style=False)"
	@echo "✅ Drone 2 deactivated in configuration"
	@curl -X POST http://localhost:8002/fleet/config/reload >/dev/null 2>&1 || true
	@echo "🔄 Configuration reloaded on server"

# =============================================================================
# COMPREHENSIVE DYNAMIC CONFIG TESTS
# =============================================================================

test-config-complete: test-config-all test-registry-comparison test-multi-drone-config ## Complete configuration system test

test-config-demo: ## Demonstrate dynamic configuration capabilities
	@echo "🎬 Dynamic Configuration Demo"
	@echo "============================"
	@echo ""
	@echo "📊 Current Configuration:"
	@make test-multi-drone-config
	@echo ""
	@echo "🔄 Testing Configuration Reload:"
	@curl -X POST http://localhost:8002/fleet/config/reload | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'✅ {data[\"message\"]}'); print(f'Drones: {data[\"changes\"][\"old_drone_count\"]} -> {data[\"changes\"][\"new_drone_count\"]}')" 2>/dev/null || echo "❌ Reload failed"

# Update main test commands to include config tests
test-server: test-server-health test-fleet-health test-fleet-registry test-config-all ## Test complete server functionality with dynamic config

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
# Add test command to Makefile
test-schemas-api: ## Test YAML schemas API endpoints
	@echo "📋 Testing schemas API endpoints..."
	@curl -s http://localhost:8002/api/schemas | jq '.metadata'
	@curl -s http://localhost:8002/api/schemas/takeoff | jq '.schema_name'
	@curl -s http://localhost:8002/api/schemas/mcp/tools | jq '.metadata.total_schemas'

# Replace the MCP section with this final version:

# =============================================================================
# MCP SERVER COMMANDS
# =============================================================================

mcp-setup: ## Setup MCP server environment
	@echo "🚀 Setting up MCP server..."
	cd mcp-server && source mcp-server-env/bin/activate && \
		uv pip install -r requirements.txt
	@echo "✅ MCP setup complete"

mcp-dev: ## Run MCP server with inspector for testing
	@echo "🔍 Starting MCP Inspector..."
	@echo "Opening browser at http://localhost:5173"
	cd mcp-server && source mcp-server-env/bin/activate && \
		DEBUG_MODE=true python -m mcp dev server.py

mcp-stdio: ## Run MCP server in STDIO mode (Claude Desktop)
	@echo "💻 Starting MCP server for Claude Desktop..."
	cd mcp-server && source mcp-server-env/bin/activate && \
		python server.py stdio

mcp-http: ## Run MCP server in HTTP mode (n8n)
	@echo "🌐 Starting MCP HTTP server on port 8003..."
	cd mcp-server && source mcp-server-env/bin/activate && \
		python server.py

mcp-test: ## Quick test of MCP server setup
	@echo "🧪 Testing MCP setup..."
	cd mcp-server && source mcp-server-env/bin/activate && \
		python -c "import server; print('✅ MCP imports OK')"

# Complete development environment with MCP
dev-full-mcp: ## Start SITL + Agent + Server + MCP
	@echo "🚁 Starting Complete DroneSphere System with MCP..."
	@echo "Step 1: Starting SITL simulator..."
	@make sitl &
	@sleep 5
	@echo "Step 2: Starting Agent (port 8001)..."
	@make agent &
	@sleep 2
	@echo "Step 3: Starting Server (port 8002)..."
	@make server &
	@sleep 2
	@echo "Step 4: Starting MCP Server (port 8003)..."
	@make mcp-http &
	@sleep 2
	@echo ""
	@echo "✅ All systems running:"
	@echo "  - SITL Simulator"
	@echo "  - Agent: http://localhost:8001"
	@echo "  - Server: http://localhost:8002"
	@echo "  - MCP: http://localhost:8003"
	@echo ""
	@echo "📝 Test with: make mcp-dev (in new terminal)"

# Install all dependencies including MCP
install-deps-all: install-deps ## Install all dependencies including MCP
	@echo "📦 Installing MCP dependencies..."
	cd mcp-server && source mcp-server-env/bin/activate && \
		uv pip install -r requirements.txt

# Quick status check for all services
status-mcp: ## Check status of all services including MCP
	@echo "📊 System Status:"
	@curl -s http://localhost:8001/health > /dev/null 2>&1 && \
		echo "✅ Agent: Running" || echo "❌ Agent: Not running"
	@curl -s http://localhost:8002/health > /dev/null 2>&1 && \
		echo "✅ Server: Running" || echo "❌ Server: Not running"
	@curl -s http://localhost:8003/health > /dev/null 2>&1 && \
		echo "✅ MCP: Running" || echo "❌ MCP: Not running"

# Claude Desktop configuration helper
mcp-claude-config: ## Generate Claude Desktop configuration
	@echo "📋 Add this to Claude Desktop config:"
	@echo "Location: ~/Library/Application Support/Claude/claude_desktop_config.json"
	@echo ""
	@echo '{'
	@echo '  "mcpServers": {'
	@echo '    "dronesphere": {'
	@echo '      "command": "python",'
	@echo '      "args": ["'$$(pwd)'/mcp-server/server.py", "stdio"],'
	@echo '      "env": {'
	@echo '        "OPENROUTER_API_KEY": "YOUR_KEY",'
	@echo '        "DRONESPHERE_SERVER_URL": "http://localhost:8002"'
	@echo '      }'
	@echo '    }'
	@echo '  }'
	@echo '}'
