#!/bin/bash
# agent/scripts/start-drone-agent.sh
# ===================================
# Production drone agent startup with auto-discovery and registration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$AGENT_DIR/.env"
DRONE_CONFIG_FILE="$AGENT_DIR/drone-config.json"

echo -e "${BLUE}🚁 DroneSphere Agent Startup${NC}"
echo "=================================="

# Check if running as root (needed for hardware access)
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}⚠️  Running as root - ensure this is intended${NC}"
fi

# Load existing configuration if available
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo -e "${GREEN}✅ Loaded existing configuration${NC}"
else
    echo -e "${YELLOW}⚠️  No configuration found, starting setup...${NC}"
fi

# Function to get user input with default
get_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "${!var_name}" ]; then
        echo -e "${GREEN}Using existing $var_name: ${!var_name}${NC}"
        return
    fi
    
    read -p "$prompt [$default]: " input
    if [ -z "$input" ]; then
        export $var_name="$default"
    else
        export $var_name="$input"
    fi
}

# Get drone configuration
echo -e "\n${BLUE}🔧 Drone Configuration${NC}"
get_input "Drone ID" "1" "DRONE_ID"
get_input "Drone Name" "Drone-$DRONE_ID" "DRONE_NAME"
get_input "Server URL" "http://192.168.1.100:8001" "SERVER_URL"
get_input "MAVLink Connection" "udp://:14540" "MAVLINK_CONNECTION"

# Auto-detect hardware vs SITL
echo -e "\n${BLUE}🔍 Detecting environment...${NC}"
if [ -e "/dev/ttyAMA0" ] || [ -e "/dev/ttyUSB0" ]; then
    DEPLOYMENT_MODE="hardware"
    echo -e "${GREEN}✅ Hardware detected (Raspberry Pi)${NC}"
    
    # Check for MAVLink router
    if ! command -v mavlink-routerd &> /dev/null; then
        echo -e "${YELLOW}⚠️  MAVLink router not found. Installing...${NC}"
        ./install-mavlink-router.sh
    fi
    
    # Set up MAVLink routing for hardware
    MAVLINK_CONNECTION="serial:///dev/ttyAMA0:57600"
    
else
    DEPLOYMENT_MODE="sitl"
    echo -e "${BLUE}🔧 SITL mode detected${NC}"
    
    # Check if SITL is running
    if ! nc -z localhost 14540; then
        echo -e "${RED}❌ SITL not detected on port 14540${NC}"
        echo "Please start SITL first: ./scripts/run_sitl.sh"
        exit 1
    fi
    echo -e "${GREEN}✅ SITL detected on port 14540${NC}"
fi

# Create configuration file
echo -e "\n${BLUE}📝 Creating configuration...${NC}"
cat > "$CONFIG_FILE" << EOF
# DroneSphere Agent Configuration
# Generated on $(date)

# Drone Identity
DRONE_ID=$DRONE_ID
DRONE_NAME=$DRONE_NAME
DEPLOYMENT_MODE=$DEPLOYMENT_MODE

# Server Connection
SERVER_URL=$SERVER_URL
REGISTRATION_ENDPOINT=$SERVER_URL/api/v1/drones/register
HEARTBEAT_ENDPOINT=$SERVER_URL/api/v1/drones/$DRONE_ID/heartbeat

# MAVLink Connection
MAVLINK_CONNECTION=$MAVLINK_CONNECTION
TELEMETRY_UPDATE_INTERVAL=0.25

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Agent Settings
AGENT_PORT=8002
COMMAND_TIMEOUT=300
EOF

echo -e "${GREEN}✅ Configuration saved to $CONFIG_FILE${NC}"

# Create drone metadata
echo -e "\n${BLUE}📋 Creating drone metadata...${NC}"
cat > "$DRONE_CONFIG_FILE" << EOF
{
    "id": $DRONE_ID,
    "name": "$DRONE_NAME",
    "type": "${DEPLOYMENT_MODE}_drone",
    "deployment_mode": "$DEPLOYMENT_MODE",
    "connection": {
        "protocol": "$(echo $MAVLINK_CONNECTION | cut -d: -f1)",
        "address": "$(echo $MAVLINK_CONNECTION | cut -d/ -f3 | cut -d: -f1)",
        "port": "$(echo $MAVLINK_CONNECTION | cut -d: -f3)"
    },
    "capabilities": ["takeoff", "land", "goto", "rtl", "hold"],
    "limits": {
        "max_altitude": 50.0,
        "max_speed": 15.0,
        "max_range": 1000.0
    },
    "hardware": {
        "platform": "$(uname -m)",
        "os": "$(uname -s)",
        "deployment_time": "$(date -Iseconds)"
    }
}
EOF

echo -e "${GREEN}✅ Drone metadata saved to $DRONE_CONFIG_FILE${NC}"

# Register with server
echo -e "\n${BLUE}🌐 Registering with server...${NC}"
register_drone() {
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt/$max_attempts..."
        
        response=$(curl -s -w "%{http_code}" \
            -X POST "$SERVER_URL/api/v1/drones/register" \
            -H "Content-Type: application/json" \
            -d @"$DRONE_CONFIG_FILE" \
            -o /tmp/registration_response.json)
        
        if [ "$response" = "200" ] || [ "$response" = "201" ]; then
            echo -e "${GREEN}✅ Successfully registered with server${NC}"
            cat /tmp/registration_response.json | jq '.' 2>/dev/null || cat /tmp/registration_response.json
            return 0
        else
            echo -e "${YELLOW}⚠️  Registration failed (HTTP $response), retrying in 5s...${NC}"
            sleep 5
            ((attempt++))
        fi
    done
    
    echo -e "${RED}❌ Failed to register after $max_attempts attempts${NC}"
    echo "Server may be unavailable. Agent will start anyway and retry later."
    return 1
}

register_drone

# Setup Python environment
echo -e "\n${BLUE}🐍 Setting up Python environment...${NC}"
cd "$AGENT_DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
uv pip install -e . -e ../shared/

# Health check
echo -e "\n${BLUE}🏥 Running health checks...${NC}"

# Check MAVLink connection
echo "Testing MAVLink connection..."
timeout 10 python -c "
import asyncio
from dronesphere_agent.backends.mavsdk import MavsdkBackend

async def test_connection():
    backend = MavsdkBackend($DRONE_ID, '$MAVLINK_CONNECTION')
    try:
        await backend.connect()
        print('✅ MAVLink connection successful')
        await backend.disconnect()
    except Exception as e:
        print(f'❌ MAVLink connection failed: {e}')
        exit(1)

asyncio.run(test_connection())
" || {
    echo -e "${RED}❌ MAVLink connection test failed${NC}"
    echo "Check your connection string and hardware"
    exit 1
}

# Start the agent
echo -e "\n${BLUE}🚀 Starting DroneSphere Agent...${NC}"
echo "Drone ID: $DRONE_ID"
echo "Server: $SERVER_URL" 
echo "MAVLink: $MAVLINK_CONNECTION"
echo -e "\nPress Ctrl+C to stop\n"

# Setup signal handling for graceful shutdown
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down agent gracefully...${NC}"
    # Send offline status to server
    curl -s -X POST "$SERVER_URL/api/v1/drones/$DRONE_ID/offline" || true
    echo -e "${GREEN}✅ Agent stopped${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start the agent with automatic restart on failure
while true; do
    echo -e "${GREEN}🚁 Starting DroneSphere Agent (Drone $DRONE_ID)...${NC}"
    
    python -m dronesphere_agent \
        --drone-id "$DRONE_ID" \
        --server-url "$SERVER_URL" \
        --mavlink-connection "$MAVLINK_CONNECTION" || {
        
        echo -e "${RED}❌ Agent crashed, restarting in 10 seconds...${NC}"
        sleep 10
    }
done