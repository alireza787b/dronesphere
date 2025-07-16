# DroneSphere v2.0 Development Makefile
.PHONY: help dev clean install-deps docker-clean
.PHONY: sitl agent server status
.PHONY: test-health test-ping test-detailed test-telemetry
.PHONY: test-takeoff test-land test-rtl test-wait
.PHONY: test-goto-gps test-goto-ned test-goto
.PHONY: test-robustness test-sequence test-navigation test-all

SHELL := /bin/bash

help: ## Show available commands
	@echo "🚁 DroneSphere v2.0 Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# =============================================================================
# DEVELOPMENT ENVIRONMENT
# =============================================================================

install-deps: ## Install all dependencies in separate environments
	@echo "📦 Installing agent dependencies..."
	@cd agent && .venv/bin/pip install -r requirements.txt
	@echo "📦 Installing server dependencies..."
	@cd server && .venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

sitl: ## Start SITL simulation (PX4 Gazebo headless)
	@echo "🚁 Starting SITL simulation..."
	@docker run -d --rm --name dronesphere-sitl \
		jonasvautherin/px4-gazebo-headless:latest
	@echo "✅ SITL running"

agent: ## Start agent only
	@echo "🤖 Starting DroneSphere Agent..."
	@cd agent && .venv/bin/python3 main.py

server: ## Start server only
	@echo "🖥️  Starting DroneSphere Server..."
	@cd server && .venv/bin/python3 main.py

status: ## Show status of all components
	@echo "📊 DroneSphere Status Check"
	@echo "=========================="
	@echo -n "SITL Container: "
	@docker ps --filter "name=dronesphere-sitl" --format "{{.Status}}" 2>/dev/null | head -1 || echo "Not running"
	@echo -n "Agent Process: "
	@pgrep -f "python.*agent" >/dev/null && echo "Running" || echo "Not running"
	@echo -n "Server Process: "
	@pgrep -f "python.*server" >/dev/null && echo "Running" || echo "Not running"
	@echo -n "Agent Health: "
	@curl -s http://localhost:8001/health >/dev/null 2>&1 && echo "OK" || echo "Unreachable"
	@echo -n "Server Health: "
	@curl -s http://localhost:8002/health >/dev/null 2>&1 && echo "OK" || echo "Unreachable"

dev: clean-all sitl ## Start full development environment (SITL + Agent + Server)
	@echo "🚀 Starting development environment..."
	@sleep 5
	@echo "🤖 Starting agent in background..."
	@cd agent && .venv/bin/python3 main.py &
	@sleep 3
	@echo "🖥️  Starting server in background..."
	@cd server && .venv/bin/python3 main.py &
	@sleep 2
	@echo "✅ Development environment ready!"

# =============================================================================
# BASIC HEALTH TESTS
# =============================================================================

test-health: ## Test agent health endpoint
	@echo "🔍 Testing agent health..."
	@curl -s http://localhost:8001/health | python3 -m json.tool || echo "❌ Agent not responding"

test-ping: ## Test agent ping endpoint
	@echo "🏓 Testing agent ping..."
	@curl -s http://localhost:8001/ping | python3 -m json.tool || echo "❌ Agent not responding"

test-detailed: ## Test detailed health endpoint
	@echo "🔍 Testing detailed health..."
	@curl -s http://localhost:8001/health/detailed | python3 -m json.tool || echo "❌ Agent not responding"

test-telemetry: ## Test telemetry endpoint
	@echo "📡 Testing telemetry..."
	@curl -s http://localhost:8001/telemetry | python3 -m json.tool || echo "❌ Telemetry not available"

test-agent: test-health test-ping test-detailed test-telemetry ## Test all agent endpoints

# =============================================================================
# SERVER TESTS
# =============================================================================

test-server-health: ## Test server health endpoint
	@echo "🖥️  Testing server health..."
	@curl -s http://localhost:8002/health | python3 -m json.tool || echo "❌ Server not responding"

test-fleet-health: ## Test fleet health endpoint
	@echo "👥 Testing fleet health..."
	@curl -s http://localhost:8002/fleet/health | python3 -m json.tool || echo "❌ Fleet health failed"

test-fleet-registry: ## Test fleet registry endpoint
	@echo "📋 Testing fleet registry..."
	@curl -s http://localhost:8002/fleet/registry | python3 -m json.tool || echo "❌ Registry failed"

test-server-takeoff: ## Test takeoff via server routing
	@echo "🚀 Testing server-routed takeoff..."
	@curl -X POST http://localhost:8002/fleet/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10},"mode":"continue"}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Server takeoff failed"

test-server: test-server-health test-fleet-health test-fleet-registry ## Test server functionality
test-fleet: test-server-takeoff ## Test fleet routing

# =============================================================================
# COMMAND TESTS
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

test-rtl: ## Test RTL command
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
		| python3 -m json.tool || echo "❌ wait command failed"

# =============================================================================
# NAVIGATION TESTS (Zurich coordinates: Ground level ~488m MSL)
# =============================================================================

test-goto-gps: ## Test goto with GPS coordinates (MSL altitude)
	@echo "🗺️  Testing goto GPS: 47.398, 8.546, 503m MSL (15m above ground)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0,"speed":3}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ goto GPS command failed"

test-goto-ned: ## Test goto with NED coordinates (relative to origin)
	@echo "🧭 Testing goto NED: N=50m, E=30m, D=-15m (15m above origin)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"north":50,"east":30,"down":-15}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ goto NED command failed"

test-goto: test-goto-gps test-goto-ned ## Test both GPS and NED navigation

# =============================================================================
# ROBUSTNESS TESTS
# =============================================================================

test-robustness: ## Test command robustness (goto when on ground should fail)
	@echo "🛡️  Testing robustness: goto when on ground (should fail)..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0}}],"target_drone":1}' \
		| python3 -m json.tool

# =============================================================================
# SEQUENCE TESTS
# =============================================================================

test-sequence: ## Test basic sequence (takeoff + land)
	@echo "🎯 Testing basic sequence: takeoff → land..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10}},{"name":"land","params":{}}],"queue_mode":"override","target_drone":1}' \
		| python3 -m json.tool || echo "❌ Basic sequence failed"

test-navigation: ## Test full navigation sequence
	@echo "🗺️  Testing navigation sequence: takeoff → goto(GPS) → wait → goto(NED) → land..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":15}},{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503.0}},{"name":"wait","params":{"duration":3}},{"name":"goto","params":{"north":20,"east":10,"down":-20}},{"name":"land","params":{}}],"target_drone":1}' \
		| python3 -m json.tool || echo "❌ Navigation sequence failed"

# =============================================================================
# COMPREHENSIVE TESTS
# =============================================================================

test-commands: test-takeoff test-land test-rtl test-wait ## Test all basic commands
test-all: test-agent test-server test-fleet test-commands test-goto test-sequence test-navigation ## Run all tests

# =============================================================================
# CLEANUP
# =============================================================================

clean: ## Stop all services
	@echo "🧹 Cleaning up processes..."
	@pkill -f "python.*agent" 2>/dev/null || true
	@pkill -f "python.*server" 2>/dev/null || true
	@echo "✅ Process cleanup complete"

docker-clean: ## Stop and remove all docker containers
	@echo "🧹 Cleaning up docker containers..."
	@docker stop dronesphere-sitl 2>/dev/null || true
	@docker system prune -f
	@echo "✅ Docker cleanup complete"

clean-all: clean docker-clean ## Clean everything (processes + docker)
