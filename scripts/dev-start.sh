#!/bin/bash
# DroneSphere Development Mode
# ===========================

set -e

echo "🚁 DroneSphere Development Setup"
echo "================================="

# Function to run in terminal
run_in_terminal() {
    local title="$1"
    local command="$2"
    
    if command -v gnome-terminal >/dev/null; then
        gnome-terminal --title="$title" -- bash -c "cd $(pwd); $command; exec bash"
    elif command -v xterm >/dev/null; then
        xterm -title "$title" -e bash -c "cd $(pwd); $command; exec bash" &
    else
        echo "⚠️  No terminal found. Run manually in separate terminals:"
        echo "   $command"
        return 1
    fi
}

echo "🚀 Starting all services..."

# Start SITL
echo "1. Starting SITL..."
run_in_terminal "SITL" "./scripts/run_sitl.sh"
sleep 3

# Start Server
echo "2. Starting Server..."  
run_in_terminal "Server" "./scripts/start-server.sh"
sleep 2

# Start Agent
echo "3. Starting Agent..."
run_in_terminal "Agent" "./scripts/start-agent.sh"

echo ""
echo "✅ Development environment started!"
echo ""
echo "🔍 Check services:"
echo "   curl localhost:8002/ping"
echo "   curl localhost:8001/health"
echo ""
echo "🧪 Test mission:"
echo "   ./scripts/test-mission.sh"
