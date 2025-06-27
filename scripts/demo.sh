#!/bin/bash
# scripts/demo.sh
# Start all DroneSphere services for demo

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚁 Starting DroneSphere Demo...${NC}"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set default ports if not specified
WEB_PORT=${WEB_PORT:-3010}
SERVER_PORT=${SERVER_PORT:-8000}

# Check if SITL is running
if ! nc -z localhost 14540 2>/dev/null; then
    echo -e "${YELLOW}⚠️  SITL not detected on port 14540${NC}"
    echo "To start SITL, run:"
    echo "docker run --rm -it -p 14540:14540/udp jonasvautherin/px4-gazebo-headless:latest"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping all services...${NC}"
    kill $SERVER_PID $AGENT_PID $WEB_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

# Start server
echo -e "${GREEN}Starting server on port $SERVER_PORT...${NC}"
cd server
source .venv/bin/activate 2>/dev/null || true
python -m uvicorn server.main:app --host 0.0.0.0 --port $SERVER_PORT &
SERVER_PID=$!
cd ..

# Wait for server to start
sleep 3

# Start agent
echo -e "${GREEN}Starting agent...${NC}"
cd agent
source .venv/bin/activate 2>/dev/null || true
python -m agent.main &
AGENT_PID=$!
cd ..

# Start frontend
echo -e "${GREEN}Starting web interface on port $WEB_PORT...${NC}"
cd web
if [ -f "package.json" ]; then
    PORT=$WEB_PORT npm run dev &
    WEB_PID=$!
else
    echo -e "${YELLOW}Web frontend not initialized yet${NC}"
    WEB_PID=0
fi
cd ..

echo -e "\n${GREEN}✅ All services started!${NC}"
echo -e "   Server API: http://localhost:$SERVER_PORT"
echo -e "   API Docs:   http://localhost:$SERVER_PORT/docs"
echo -e "   Web UI:     http://localhost:$WEB_PORT"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Wait for all processes
wait
