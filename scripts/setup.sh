#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚁 DroneSphere Setup Script${NC}"
echo "================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
if command_exists python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.11"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    else
        echo -e "${RED}✗ Python $PYTHON_VERSION found, but $REQUIRED_VERSION+ required${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

# Check Node.js
echo -e "\n${YELLOW}Checking Node.js...${NC}"
if command_exists node; then
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
else
    echo -e "${RED}✗ Node.js not found${NC}"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Install UV if not present
echo -e "\n${YELLOW}Checking UV package manager...${NC}"
if ! command_exists uv; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    echo -e "${GREEN}✓ UV installed${NC}"
else
    echo -e "${GREEN}✓ UV already installed${NC}"
fi

# Create Python virtual environments
echo -e "\n${YELLOW}Setting up Python environments...${NC}"

# Agent environment
echo "Setting up agent environment..."
cd agent
uv venv
uv pip install -r requirements.txt || echo "No requirements.txt yet"
cd ..

# Server environment
echo "Setting up server environment..."
cd server
uv venv
uv pip install -r requirements.txt || echo "No requirements.txt yet"
cd ..

# Install Node.js dependencies
echo -e "\n${YELLOW}Setting up frontend...${NC}"
cd web
if [ -f "package.json" ]; then
    npm install
else
    echo "No package.json found, skipping npm install"
fi
cd ..

# Install pre-commit hooks
echo -e "\n${YELLOW}Setting up pre-commit hooks...${NC}"
if command_exists pre-commit; then
    pre-commit install
    echo -e "${GREEN}✓ Pre-commit hooks installed${NC}"
else
    echo -e "${YELLOW}⚠ Pre-commit not found, installing...${NC}"
    pip install pre-commit
    pre-commit install
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p logs
mkdir -p shared/configs
mkdir -p shared/commands/{basic,custom}
mkdir -p shared/prompts/{templates,pipelines}

# Create example configuration files
echo -e "\n${YELLOW}Creating example configurations...${NC}"

# Example drone configuration
cat > shared/configs/drones.example.json << 'EOF'
{
  "drones": [
    {
      "id": "drone_001",
      "name": "SITL Drone",
      "type": "quadcopter",
      "connection": {
        "type": "network",
        "host": "localhost",
        "port": 14540
      },
      "capabilities": ["camera", "gps"],
      "flight_params": {
        "max_altitude": 50,
        "max_speed": 15
      }
    }
  ]
}
EOF

# Example LLM configuration
cat > shared/configs/llm_providers.example.json << 'EOF'
{
  "providers": [
    {
      "name": "ollama",
      "type": "local",
      "endpoint": "http://localhost:11434",
      "models": ["llama2", "mistral"],
      "default_model": "llama2"
    },
    {
      "name": "openai",
      "type": "api",
      "models": ["gpt-3.5-turbo", "gpt-4"],
      "api_key_env": "OPENAI_API_KEY" #pragma: allowlist secret
    }
  ],
  "default_provider": "ollama"
}
EOF

# Create .env.example
cat > .env.example << 'EOF'
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO

# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-key-here

# Drone Configuration
DEFAULT_DRONE_PORT=14540
SITL_HOST=localhost

# Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=http://localhost:3000
EOF

echo -e "${GREEN}✓ Example configurations created${NC}"

# Final instructions
echo -e "\n${GREEN}✅ Setup Complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Copy .env.example to .env and update values"
echo "2. Copy config examples in shared/configs/ and customize"
echo "3. Run './scripts/demo.sh' to start the demo"
echo "4. Visit http://localhost:3000 for the web interface"

echo -e "\n${YELLOW}For development:${NC}"
echo "- Run './scripts/dev.sh' to start in development mode"
echo "- Run 'uv run pytest' to run tests"
echo "- Check docs/progress/ for detailed implementation steps"
