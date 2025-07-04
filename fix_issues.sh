#!/bin/bash
# fix_issues.sh - Auto-fix script for DroneSphere configuration issues

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 DroneSphere Auto-Fix Script${NC}"
echo "=================================="

# Get project root directory
PROJECT_ROOT="$(pwd)"

echo -e "${YELLOW}📁 Project root: $PROJECT_ROOT${NC}"

# Function to replace text in files
replace_in_file() {
    local file="$1"
    local search="$2"
    local replace="$3"
    
    if [[ -f "$file" ]]; then
        if grep -q "$search" "$file" 2>/dev/null; then
            sed -i.bak "s|$search|$replace|g" "$file"
            echo "  ✅ Updated: $file"
        fi
    fi
}

# Function to replace text recursively in directory
replace_in_dir() {
    local dir="$1"
    local search="$2"
    local replace="$3"
    local extensions="$4"
    
    if [[ -d "$dir" ]]; then
        echo -e "${YELLOW}📝 Updating files in $dir${NC}"
        find "$dir" -type f \( $extensions \) -exec grep -l "$search" {} \; 2>/dev/null | while read -r file; do
            replace_in_file "$file" "$search" "$replace"
        done
    fi
}

echo -e "${YELLOW}🔄 Issue 1: Changing port 8000 → 8001${NC}"

# Change port 8000 to 8001 in all relevant files
replace_in_file ".env.example" "SERVER_PORT=8000" "SERVER_PORT=8001"
replace_in_file "pyproject.toml" "8000" "8001"

# Update Python files
replace_in_dir "dronesphere" "port.*8000" "port=8001" "-name '*.py'"
replace_in_dir "dronesphere" "localhost:8000" "localhost:8001" "-name '*.py'"
replace_in_dir "dronesphere" ":8000" ":8001" "-name '*.py'"

# Update test files
replace_in_dir "tests" "8000" "8001" "-name '*.py'"

# Update documentation
replace_in_dir "docs" "8000" "8001" "-name '*.md'"

# Update Docker and scripts
replace_in_dir "docker" "8000" "8001" "-name '*.yml' -o -name '*.yaml' -o -name '*.conf'"
replace_in_dir "scripts" "8000" "8001" "-name '*.sh'"

# Update docker-compose files
replace_in_file "docker-compose.yml" "8000:8000" "8001:8001"
replace_in_file "docker-compose.prod.yml" "8000:8000" "8001:8001"

# Update Makefile and GitHub workflows
replace_in_file "Makefile" "8000" "8001"
replace_in_dir ".github" "8000" "8001" "-name '*.yml' -o -name '*.yaml'"

echo -e "${GREEN}✅ Port changed from 8000 to 8001${NC}"

echo -e "${YELLOW}🔄 Issue 2: Fixing Docker image for PX4 Gazebo${NC}"

# Update Docker image reference
replace_in_file "docker-compose.yml" "px4io/px4-gazebo-headless:1.15.4" "jonasvautherin/px4-gazebo-headless:latest"
replace_in_file "docker/sitl/Dockerfile" "FROM px4io/px4-gazebo-headless:1.15.4" "FROM jonasvautherin/px4-gazebo-headless:latest"
replace_in_dir "tests" "px4io/px4-gazebo-headless:1.15.4" "jonasvautherin/px4-gazebo-headless:latest" "-name '*.yml' -o -name '*.yaml'"

echo -e "${GREEN}✅ Updated Docker image to jonasvautherin/px4-gazebo-headless:latest${NC}"

echo -e "${YELLOW}🔄 Issue 3: Removing mavlink2rest and configuring mavlink-router${NC}"

# Create new docker-compose.yml without mavlink2rest
cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  # PX4 SITL simulation
  sitl:
    image: jonasvautherin/px4-gazebo-headless:latest
    container_name: dronesphere-sitl
    ports:
      - "14540:14540/udp"  # MAVLink SITL
      - "14550:14550/udp"  # MAVLink GCS
    environment:
      - PX4_SIM_MODEL=iris
      - PX4_SIM_WORLD=empty
    networks:
      - dronesphere
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nc", "-u", "-z", "localhost", "14540"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  # MAVLink Router for connection management
  mavlink-router:
    image: alpine:latest
    container_name: dronesphere-mavrouter
    depends_on:
      - sitl
    ports:
      - "14569:14569/udp"  # Additional MAVLink port
    command: >
      sh -c "
        apk add --no-cache socat &&
        echo 'Starting MAVLink router...' &&
        socat UDP4-RECV:14550,bind,fork UDP4-SENDTO:host.docker.internal:14569
      "
    networks:
      - dronesphere
    restart: unless-stopped

networks:
  dronesphere:
    driver: bridge
COMPOSE_EOF

echo -e "${GREEN}✅ Updated docker-compose.yml with proper MAVLink routing${NC}"

# Update backend configuration to remove mavlink2rest references
echo -e "${YELLOW}📝 Updating backend configuration${NC}"

# Update Python configuration files
find dronesphere -name "*.py" -type f -exec grep -l "mavlink2rest" {} \; 2>/dev/null | while read -r file; do
    echo "  🔧 Updating $file to remove mavlink2rest references"
    sed -i.bak 's/mavlink2rest/mavsdk/g' "$file"
    sed -i.bak '/mavlink2rest/d' "$file"
done

# Update .env.example
cat > .env.example << 'ENV_EOF'
# Environment Configuration Example
# Copy to .env and customize for your setup

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Agent Configuration
AGENT_HOST=localhost
AGENT_PORT=8002
DRONE_CONNECTION_STRING=udp://:14540
TELEMETRY_UPDATE_INTERVAL=0.25
COMMAND_TIMEOUT=300

# Server Configuration  
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
API_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Backend Configuration
DEFAULT_BACKEND=mavsdk
TELEMETRY_BACKEND=mavsdk

# Paths
SHARED_CONFIG_PATH=./shared
COMMAND_LIBRARY_PATH=./shared/commands

# Development
DEBUG=false
RELOAD=false

# Metrics & Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=10
ENV_EOF

echo -e "${GREEN}✅ Updated .env.example with corrected configuration${NC}"

# Remove .bak files created by sed
echo -e "${YELLOW}🧹 Cleaning up backup files${NC}"
find . -name "*.bak" -type f -delete 2>/dev/null || true

echo -e "${YELLOW}🔄 Issue 4: Reviewing other potential problems${NC}"

# Fix README port references
if [[ -f "README.md" ]]; then
    sed -i.bak 's/localhost:8000/localhost:8001/g' README.md
    sed -i.bak 's/:8000/:8001/g' README.md
    rm -f README.md.bak
    echo "  ✅ Updated README.md"
fi

# Update test configurations
if [[ -f "tests/conftest.py" ]]; then
    sed -i.bak 's/8000/8001/g' tests/conftest.py
    rm -f tests/conftest.py.bak
    echo "  ✅ Updated test configuration"
fi

echo -e "${GREEN}✅ Additional issues reviewed and fixed${NC}"

echo ""
echo -e "${GREEN}🎉 All issues have been automatically fixed!${NC}"
echo ""
echo -e "${BLUE}📋 Summary of changes:${NC}"
echo "  • Changed default server port: 8000 → 8001"
echo "  • Updated Docker image: px4io/px4-gazebo-headless → jonasvautherin/px4-gazebo-headless"
echo "  • Removed mavlink2rest dependency"
echo "  • Configured simple MAVLink routing using socat"
echo "  • Updated all configuration files and documentation"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Run: cp .env.example .env"
echo "2. Run: ./scripts/setup_dev.sh"
echo "3. Run: ./scripts/run_sitl.sh"
echo "4. In another terminal: python -m dronesphere.agent"
echo "5. In another terminal: uvicorn dronesphere.server.api:app --port 8001 --reload"
echo ""
echo -e "${GREEN}Ready for testing! 🚀${NC}"
