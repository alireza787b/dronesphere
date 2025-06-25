#!/bin/bash
# DroneSphere Quick Setup Script for Ubuntu 20.04+
# ==============================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "\n${GREEN}==>${NC} $1"
}

print_info() {
    echo -e "${YELLOW}    $1${NC}"
}

print_error() {
    echo -e "${RED}Error: $1${NC}"
    exit 1
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check if running on Ubuntu
if ! grep -q "Ubuntu" /etc/os-release; then
    print_error "This script is designed for Ubuntu. Detected: $(cat /etc/os-release | grep PRETTY_NAME)"
fi

print_step "DroneSphere Quick Setup for Ubuntu"
echo "===================================="

# Update system
print_step "Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated"

# Install Python and essential tools
print_step "Installing Python and development tools..."
sudo apt install -y \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    build-essential git curl wget \
    libpq-dev \
    net-tools tmux htop
print_success "Python and tools installed"

# Install Docker
print_step "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_info "Docker installed. You'll need to log out and back in for group changes."
else
    print_info "Docker already installed"
fi

# Install Docker Compose
print_step "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt install -y docker-compose
    print_success "Docker Compose installed"
else
    print_info "Docker Compose already installed"
fi

# Install UV
print_step "Installing UV package manager..."
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    
    # Add to bashrc if not already there
    if ! grep -q "/.local/bin" ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
    print_success "UV installed"
else
    print_info "UV already installed"
fi

# Verify UV installation
if ! command -v uv &> /dev/null; then
    export PATH="$HOME/.local/bin:$PATH"
fi

# Clone repository (if not already in it)
if [ ! -f "pyproject.toml" ]; then
    print_step "Cloning DroneSphere repository..."
    read -p "Enter the repository URL [https://github.com/alireza787b/dronesphere.git]: " REPO_URL
    REPO_URL=${REPO_URL:-https://github.com/alireza787b/dronesphere.git}
    
    git clone "$REPO_URL" dronesphere
    cd dronesphere
else
    print_info "Already in DroneSphere directory"
fi

# Create virtual environment
print_step "Creating Python virtual environment..."
uv venv
print_success "Virtual environment created"

# Activate virtual environment
print_step "Installing Python dependencies..."
source .venv/bin/activate
uv pip install -e ".[dev]"
print_success "Dependencies installed"

# Setup pre-commit hooks
print_step "Setting up pre-commit hooks..."
pre-commit install
print_success "Pre-commit hooks installed"

# Create environment file
print_step "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    print_success "Created .env file from template"
    print_info "Please edit .env file to configure your environment"
else
    print_info ".env file already exists"
fi

# Create Docker network
print_step "Creating Docker network..."
if ! docker network ls | grep -q "dronesphere-network"; then
    docker network create dronesphere-network
    print_success "Docker network created"
else
    print_info "Docker network already exists"
fi

# Start Docker services
print_step "Starting Docker services..."
read -p "Start Docker services now? (y/n) [y]: " START_DOCKER
START_DOCKER=${START_DOCKER:-y}

if [ "$START_DOCKER" = "y" ]; then
    docker-compose -f deploy/docker/docker-compose.yaml up -d
    print_success "Docker services started"
    
    # Wait for services
    print_info "Waiting for services to initialize..."
    sleep 10
    
    # Show service status
    docker-compose -f deploy/docker/docker-compose.yaml ps
else
    print_info "Skipping Docker services. Run 'make docker-up' to start them later."
fi

# Test the setup
print_step "Testing the setup..."
if python scripts/test_environment.py; then
    print_success "Environment test passed!"
else
    print_error "Environment test failed. Check the error messages above."
fi

# Run domain model tests
print_step "Testing domain models..."
if python scripts/test_domain_models.py; then
    print_success "Domain model tests passed!"
else
    print_info "Domain model tests failed. This is expected if models aren't implemented yet."
fi

# Display summary
echo -e "\n${GREEN}==================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source .venv/bin/activate"
echo "2. Edit configuration: nano .env"
echo "3. Run development server: make run-dev"
echo "4. View API docs: http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  make help         - Show all available commands"
echo "  make test         - Run tests"
echo "  make docker-logs  - View Docker logs"
echo "  make quality      - Run code quality checks"
echo ""

# Check if need to logout for Docker
if groups | grep -q docker; then
    echo "Docker group is active. You're all set!"
else
    echo -e "${YELLOW}Note: You need to log out and back in for Docker group changes.${NC}"
fi

print_success "Happy coding with DroneSphere! 🚁"