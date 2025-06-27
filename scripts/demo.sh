#!/bin/bash
echo "🚁 Starting DroneSphere Demo..."

# Check if SITL is running
if ! nc -z localhost 14540; then
    echo "⚠️  SITL not detected. Please run:"
    echo "docker run --rm -it -p 14540:14540/udp jonasvautherin/px4-gazebo-headless:latest"
    exit 1
fi

# Start server
echo "Starting server..."
cd server && uv run python -m server.main &
SERVER_PID=$!

# Start agent
echo "Starting agent..."
cd ../agent && uv run python -m agent.main &
AGENT_PID=$!

# Start frontend
echo "Starting frontend..."
cd ../web && npm run dev &
WEB_PID=$!

echo "✅ All services started!"
echo "   Server: http://localhost:8000"
echo "   Web UI: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "kill $SERVER_PID $AGENT_PID $WEB_PID 2>/dev/null" EXIT
wait
