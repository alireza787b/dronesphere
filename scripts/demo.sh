#!/bin/bash
# scripts/demo.sh
# Run complete DroneSphere demo

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚁 DroneSphere Demo${NC}"
echo "===================="

# Check SITL using a Python script with MAVSDK
echo -e "${YELLOW}Checking SITL connection using MAVSDK...${NC}"
if ! ~/dronesphere/.venv/bin/python ~/dronesphere/scripts/check_sitl.py; then
    echo -e "${YELLOW}⚠️  SITL not detected or not sending MAVLink data.${NC}"
    echo "Run: docker run --rm -it jonasvautherin/px4-gazebo-headless:latest"
    exit 1
fi

# Start services
echo -e "${GREEN}Starting services...${NC}"

# Server
echo "1. Starting server..."
python start_server.py &
SERVER_PID=$!

sleep 5

# Agent
echo "2. Starting agent..."
cd agent && python run_agent.py --dev &
AGENT_PID=$!
cd ..

echo -e "\n${GREEN}✅ Demo running!${NC}"
echo "Server: http://localhost:8001/docs"
echo "Press Ctrl+C to stop"

trap "kill $SERVER_PID $AGENT_PID 2>/dev/null" EXIT
wait
