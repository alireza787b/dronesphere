#!/bin/bash

# DroneSphere SITL startup script - Direct Docker version

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SITL_WORLD=${SITL_WORLD:-empty}
SITL_MODEL=${SITL_MODEL:-iris}
CONTAINER_NAME="dronesphere-sitl"

echo -e "${GREEN}🚁 Starting DroneSphere SITL Environment${NC}"
echo "=================================================="
echo "Model: $SITL_MODEL"
echo "World: $SITL_WORLD"
echo "=================================================="

# Clean up function
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Stop and remove existing container
echo -e "${YELLOW}🛑 Stopping existing SITL container...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# Start SITL container
echo -e "${YELLOW}🚀 Starting SITL container...${NC}"
docker run -d \
  --name $CONTAINER_NAME \
  -e PX4_SIM_MODEL=$SITL_MODEL \
  -e PX4_SIM_WORLD=$SITL_WORLD \
  jonasvautherin/px4-gazebo-headless:latest

echo -e "${YELLOW}⏳ Waiting for SITL to initialize (this takes ~45 seconds)...${NC}"

# Wait for SITL to be ready with progress indicators
for i in {1..45}; do
    if nc -u -z localhost 14540 2>/dev/null; then
        echo -e "\n${GREEN}✅ SITL is ready on UDP 14540! (took ${i}s)${NC}"
        break
    fi
    
    # Show progress every 5 seconds
    if [ $((i % 5)) -eq 0 ]; then
        echo -n "."
    fi
    
    sleep 1
    
    # If we've waited the full time
    if [ $i -eq 45 ]; then
        echo -e "\n${RED}❌ SITL didn't respond within 45s${NC}"
        echo "Container logs:"
        docker logs $CONTAINER_NAME
        exit 1
    fi
done

echo ""
echo -e "${GREEN}🎉 SITL environment is ready!${NC}"
echo ""
echo "Services available:"
echo "  • PX4 SITL: udp://localhost:14540 (Primary MAVLink)"
echo "  • Ground Control: udp://localhost:14550"
echo ""
echo "Test connection:"
echo "  nc -u localhost 14540"
echo ""
echo "Container status:"
docker ps | grep $CONTAINER_NAME
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop SITL${NC}"

# Keep running until interrupted
while true; do
    # Check if container is still running
    if ! docker ps | grep -q $CONTAINER_NAME; then
        echo -e "\n${RED}❌ SITL container stopped unexpectedly${NC}"
        exit 1
    fi
    sleep 5
done
