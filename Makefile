# DroneSphere v2.0 Development Makefile
.PHONY: help dev test-health sitl agent server clean install-deps docker-clean

SHELL := /bin/bash

help: ## Show available commands
	@echo "🚁 DroneSphere v2.0 Development Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

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

test-sequence: ## Test command sequence (takeoff + land)
	@echo "🎯 Testing command sequence..."
	@curl -X POST http://localhost:8001/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10}},{"name":"land","params":{}}],"queue_mode":"override","target_drone":1}' \
		| python3 -m json.tool || echo "❌ Sequence failed"

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

test-server-sequence: ## Test sequence via server routing
	@echo "🎯 Testing server-routed sequence..."
	@curl -X POST http://localhost:8002/fleet/commands \
		-H "Content-Type: application/json" \
		-d '{"commands":[{"name":"takeoff","params":{"altitude":10}},{"name":"land","params":{}}],"queue_mode":"override","target_drone":1}' \
		| python3 -m json.tool || echo "❌ Server sequence failed"

test-commands: test-takeoff test-land test-sequence ## Test all command types

test-connection: test-health test-ping test-detailed ## Test all basic endpoints

test-server: test-server-health test-fleet-health test-fleet-registry test-server-takeoff ## Test server functionality

test-all: test-connection test-telemetry test-commands test-server ## Test everything (requires both agent and server running)

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
	@echo "🔧 Test agent: make test-connection"
	@echo "🔧 Test server: make test-server-health"
	@echo "🔧 Test all: make test-all"

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
