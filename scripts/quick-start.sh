#!/bin/bash
# scripts/quick-start.sh - Complete DroneSphere Startup
# ====================================================

set -e

echo "🚁 DroneSphere Quick Start"
echo "=========================="

# Function to run command in new terminal
run_in_terminal() {
    local title="$1"
    local command="$2"
    
    if command -v gnome-terminal >/dev/null; then
        gnome-terminal --title="$title" -- bash -c "$command; exec bash"
    elif command -v xterm >/dev/null; then
        xterm -title "$title" -e bash -c "$command; exec bash" &
    else
        echo "⚠️  Please run these commands in separate terminals:"
        echo "Terminal 1: $command"
        return 1
    fi
}

echo "🚀 Starting all services..."

# Start SITL
echo "1. Starting SITL..."
run_in_terminal "DroneSphere SITL" "./scripts/run_sitl.sh"
sleep 5

# Start Server  
echo "2. Starting Server..."
run_in_terminal "DroneSphere Server" "./scripts/start-server.sh"
sleep 3

# Start Agent
echo "3. Starting Agent..."
run_in_terminal "DroneSphere Agent" "./scripts/start-agent.sh"

echo ""
echo "✅ DroneSphere services starting in separate terminals"
echo ""
echo "🔍 Check status:"
echo "   curl localhost:8002/ping    # Server health"
echo "   curl localhost:8001/health  # Agent health"
echo ""
echo "🚁 Test mission:"
echo "   curl -X POST localhost:8002/drones/1/commands \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"sequence\": [{\"name\": \"takeoff\", \"params\": {\"altitude\": 5.0}}]}'"