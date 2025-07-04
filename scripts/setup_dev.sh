#!/bin/bash

# Development environment setup script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🛠️  DroneSphere Development Setup${NC}"
echo "=================================="

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}📦 Installing uv...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true
    else
        echo -e "${GREEN}✅ uv is already installed${NC}"
    fi
}

# Setup Python environment
setup_python() {
    echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
    cd "$PROJECT_DIR"
    
    # Create virtual environment
    uv venv
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
    
    # Install dependencies
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    uv pip install -e .[dev]
    
    echo -e "${GREEN}✅ Python environment setup complete${NC}"
}

# Setup pre-commit hooks
setup_precommit() {
    echo -e "${YELLOW}🔧 Setting up pre-commit hooks...${NC}"
    cd "$PROJECT_DIR"
    
    if command -v pre-commit &> /dev/null; then
        pre-commit install
        echo -e "${GREEN}✅ Pre-commit hooks installed${NC}"
    else
        echo -e "${YELLOW}⚠️  pre-commit not found, skipping hook setup${NC}"
    fi
}

# Create .env file
setup_env() {
    echo -e "${YELLOW}⚙️  Setting up environment configuration...${NC}"
    cd "$PROJECT_DIR"
    
    if [[ ! -f .env ]]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file from template${NC}"
        echo -e "${YELLOW}💡 Edit .env file to customize your settings${NC}"
    else
        echo -e "${YELLOW}⚠️  .env file already exists, skipping${NC}"
    fi
}

# Setup MAVLink routing and tools
setup_mavlink_tools() {
    echo -e "${YELLOW}🛜 Setting up MAVLink tools...${NC}"
    
    # Check if mavlink2rest exists
    if ! command -v mavlink2rest &> /dev/null; then
        echo -e "${RED}❌ mavlink2rest not found${NC}"
        echo -e "${YELLOW}📋 Please run the following commands to install mavlink2rest:${NC}"
        echo ""
        echo "  # Install Rust (if not already installed)"
        echo "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
        echo "  source ~/.cargo/env"
        echo ""
        echo "  # Install mavlink2rest"
        echo "  cargo install mavlink2rest"
        echo ""
        echo -e "${YELLOW}Or if you have the build script:${NC}"
        echo "  ./build_mavlink2rest.sh"
        echo ""
        echo -e "${YELLOW}⚠️  MAVLink routing setup incomplete. Please install mavlink2rest and re-run setup.${NC}"
        return 1
    else
        echo -e "${GREEN}✅ mavlink2rest is available${NC}"
    fi
    
    # Check if mavlinkanywhere/mavlink-router is available
    if command -v mavlink-router &> /dev/null; then
        echo -e "${GREEN}✅ mavlink-router is available${NC}"
    else
        echo -e "${YELLOW}⚠️  mavlink-router not found${NC}"
        echo -e "${YELLOW}📋 For production deployment, install mavlink-router:${NC}"
        echo ""
        echo "  # Install from mavlinkanywhere"
        echo "  # See: https://github.com/mavlink/mavlink-router"
        echo ""
    fi
}

# Verify installation
verify_setup() {
    echo -e "${YELLOW}🔍 Verifying installation...${NC}"
    cd "$PROJECT_DIR"
    
    # Activate virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        source .venv/Scripts/activate
    else
        source .venv/bin/activate
    fi
    
    # Run basic tests
    echo "  • Checking Python imports..."
    python -c "import dronesphere; print('✅ DroneSphere package imported successfully')"
    
    echo "  • Checking command registry..."
    python -c "from dronesphere.commands.registry import load_command_library; load_command_library(); print('✅ Command library loaded successfully')"
    
    echo "  • Running basic tests..."
    python -m pytest tests/unit/ -v --tb=short
    
    echo -e "${GREEN}✅ Installation verified successfully${NC}"
}

# Show next steps
show_next_steps() {
    echo ""
    echo -e "${BLUE}🎉 Development environment setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo -e "  1. ${YELLOW}Activate virtual environment:${NC}"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        echo "     source .venv/Scripts/activate"
    else
        echo "     source .venv/bin/activate"
    fi
    echo ""
    echo -e "  2. ${YELLOW}Start SITL environment:${NC}"
    echo "     ./scripts/run_sitl.sh"
    echo ""
    echo -e "  3. ${YELLOW}Start MAVLink routing (in another terminal):${NC}"
    echo "     mavlink2rest  # Uses default settings"
    echo ""
    echo -e "  4. ${YELLOW}Run the system:${NC}"
    echo "     python -m dronesphere"
    echo ""
    echo -e "  5. ${YELLOW}Test the API:${NC}"
    echo "     curl http://localhost:8001/health"
    echo ""
    echo -e "  6. ${YELLOW}View documentation:${NC}"
    echo "     http://localhost:8001/docs"
    echo ""
    echo -e "${BLUE}�� Production Notes:${NC}"
    echo -e "  • For real hardware: Use mavlink-router to route from serial to UDP"
    echo -e "  • Configure mavlinkanywhere as a service for reliability"
    echo -e "  • See docs/deployment.md for production setup"
    echo ""
    echo -e "${GREEN}Happy coding! 🚁${NC}"
}

# Main execution
main() {
    check_uv
    setup_python
    setup_precommit
    setup_env
    setup_mavlink_tools
    verify_setup
    show_next_steps
}

# Parse arguments
SKIP_TESTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --help)
            echo "DroneSphere Development Setup Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "    --skip-tests    Skip running tests during verification"
            echo "    --help          Show this help message"
            echo ""
            echo "This script will:"
            echo "  • Install uv (if not present)"
            echo "  • Create Python virtual environment"
            echo "  • Install project dependencies"
            echo "  • Setup pre-commit hooks"
            echo "  • Create .env configuration file"
            echo "  • Verify MAVLink tools installation"
            echo "  • Verify installation"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Run main function
main
