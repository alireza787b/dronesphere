# 🚁 DroneSphere - Natural Language Drone Control System

**Author**: Alireza Ghaderi  
**GitHub**: [@alireza787b](https://github.com/alireza787b)  
**LinkedIn**: [alireza787b](https://linkedin.com/in/alireza787b)  
**Email**: p30planets@gmail.com

## 📋 Project Status & Context

**Current Step**: 2 of 25 (Development Environment Complete)  
**Architecture**: Hexagonal (Ports & Adapters)  
**Language**: Python 3.12+ with full async/await  
**Goal**: Build a natural language drone control system using spaCy NLP

### ✅ Completed Steps:
1. **Step 1**: Project structure with hexagonal architecture
2. **Step 2**: Development environment with Docker services (PostgreSQL, Redis, RabbitMQ)

### 🎯 Next Step:
**Step 3**: Core Domain Models Implementation
- Drone entity with state management
- Position value object (lat, lon, altitude)
- Command patterns for drone control
- Domain events

## 🚀 Complete Setup Guide for Fresh Ubuntu System

### Prerequisites Installation (Ubuntu 22.04/24.04)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 (Ubuntu 24.04 has it by default)
# For Ubuntu 22.04, add deadsnakes PPA:
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3.12-distutils

# Install essential tools
sudo apt install -y \
    git \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-pip \
    postgresql-client \
    redis-tools

# Install Poetry (system-wide)
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify Poetry installation
poetry --version

# Install Docker
sudo apt install -y ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker
docker --version
docker compose version
```

### Project Setup

```bash
# Clone repository
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere

# Create Python 3.12 virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.x

# Install dependencies with Poetry
poetry install

# Copy environment file
cp .env.example .env

# Start Docker services
make docker-up

# Wait for services to be healthy (about 30 seconds)
sleep 30

# Verify all services
python scripts/test_environment.py
```

## 📁 Project Structure

```
dronesphere/
├── src/
│   ├── core/                  # Business logic (hexagonal center)
│   │   ├── domain/           # Entities, value objects, domain events
│   │   │   ├── entities/     # Drone, Mission, etc.
│   │   │   ├── value_objects/# Position, Command, etc.
│   │   │   ├── events/       # DroneMovedEvent, etc.
│   │   │   └── aggregates/   # Drone aggregate root
│   │   ├── application/      # Use cases / application services
│   │   │   ├── commands/     # Command handlers
│   │   │   ├── queries/      # Query handlers
│   │   │   └── services/     # NLP service, etc.
│   │   └── ports/           # Interfaces (ports)
│   │       ├── input/       # Driving ports
│   │       └── output/      # Driven ports
│   ├── adapters/            # External adapters
│   │   ├── input/          # API, CLI, WebSocket
│   │   │   ├── api/        # FastAPI routes
│   │   │   └── cli/        # Command line interface
│   │   └── output/         # Database, messaging, drone SDK
│   │       ├── persistence/# PostgreSQL repositories
│   │       ├── messaging/  # RabbitMQ publishers
│   │       ├── drone/      # MAVSDK integration
│   │       └── ai/         # spaCy NLP adapter
│   ├── shared/             # Shared kernel
│   └── config/             # Configuration
├── tests/                  # Test suite
├── deploy/                 # Deployment configs
│   └── docker/            # Docker configurations
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── Makefile              # Development commands
```

## 🛠 Development Environment

### Services (via Docker Compose)
- **PostgreSQL 16** with PostGIS: Spatial database (port 5432)
- **Redis 7.4**: Caching and real-time data (port 6379)
- **RabbitMQ 3.13**: Event-driven messaging (port 5672, UI: 15672)
- **Adminer**: Database UI (port 8080)

### Python Stack
- **Framework**: FastAPI with full async/await
- **ORM**: SQLAlchemy 2.0 with asyncpg
- **Validation**: Pydantic v2
- **Testing**: pytest with async support
- **NLP**: spaCy 3.7
- **Drone SDK**: MAVSDK-Python
- **Type Checking**: mypy with strict mode
- **Code Quality**: black, isort, flake8, bandit
- **Pre-commit**: Automated code quality checks

## 📚 Available Commands

```bash
# Docker Management
make docker-up          # Start all services
make docker-down        # Stop all services
make docker-logs        # View service logs
make docker-ps          # List running services
make docker-clean       # Remove volumes (WARNING: destroys data)

# Database
make db-shell          # PostgreSQL interactive shell
make db-migrations     # Run database migrations
make db-reset          # Reset database (WARNING: destroys data)

# Development
make run               # Run the application
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests
make test-coverage     # Generate coverage report
make format            # Format code (black + isort)
make lint              # Run all linters
make type-check        # Run mypy
make security-check    # Run bandit

# Dependencies
make deps-update       # Update dependencies
make deps-lock         # Lock dependencies
make deps-sync         # Sync with lock file

# Utilities
make clean             # Clean cache files
make help              # Show all commands
```

## 🔧 Troubleshooting

### Common Issues

1. **asyncpg not found**: Run `poetry install` inside virtual environment
2. **Docker permission denied**: Run `sudo usermod -aG docker $USER` and re-login
3. **Port already in use**: Check with `sudo lsof -i :PORT` and stop conflicting service
4. **Poetry not found**: Ensure `~/.local/bin` is in PATH

## 🏗 Implementation Roadmap

### Phase 1: Foundation (Steps 1-5) ✅ Currently Here
- [x] Step 1: Project Structure
- [x] Step 2: Development Environment
- [ ] Step 3: Core Domain Models
- [ ] Step 4: Natural Language Processing
- [ ] Step 5: Basic API

### Phase 2: Core Features (Steps 6-10)
- [ ] Step 6: Advanced NLP with spaCy
- [ ] Step 7: Real-time WebSocket
- [ ] Step 8: GraphQL API
- [ ] Step 9: MAVSDK Integration
- [ ] Step 10: Mission Planning

### Phase 3: Advanced Features (Steps 11-15)
- [ ] Step 11: Geospatial with PostGIS
- [ ] Step 12: Real-time Telemetry
- [ ] Step 13: Multi-drone Support
- [ ] Step 14: Safety Systems
- [ ] Step 15: Simulation Mode

### Phase 4: Production Ready (Steps 16-20)
- [ ] Step 16: Authentication/Authorization
- [ ] Step 17: Monitoring/Logging
- [ ] Step 18: Performance Optimization
- [ ] Step 19: Documentation
- [ ] Step 20: Testing Suite

### Phase 5: Deployment (Steps 21-25)
- [ ] Step 21: CI/CD Pipeline
- [ ] Step 22: Kubernetes Deployment
- [ ] Step 23: Security Hardening
- [ ] Step 24: Load Testing
- [ ] Step 25: Production Release

## 📝 For AI Assistants Continuing This Project

**IMPORTANT**: This project is at Step 2 of 25. The next task is implementing Step 3: Core Domain Models.

### Current State Summary:
1. **Architecture**: Hexagonal (Ports & Adapters) - all directories created
2. **Infrastructure**: Docker services running (PostgreSQL, Redis, RabbitMQ)
3. **Dependencies**: All installed via Poetry (FastAPI, asyncpg, spaCy, etc.)
4. **Development Tools**: Pre-commit hooks, testing framework, linters configured

### Next Implementation (Step 3):
Create in `src/core/domain/`:
1. **entities/drone.py**: Drone aggregate root with state management
2. **value_objects/position.py**: Position(lat, lon, altitude) value object
3. **value_objects/command.py**: Command value objects
4. **events/**: Domain events (DroneMovedEvent, CommandExecutedEvent)

### Key Design Decisions:
- Everything must be async/await
- Use type hints everywhere
- Follow Domain-Driven Design principles
- Write tests for everything
- Keep hexagonal architecture boundaries clean

### Example prompt for next session:
> "Continue implementing Step 3 of the DroneSphere project. The infrastructure is ready. Please implement the core domain models: Drone entity, Position value object, and Command patterns following hexagonal architecture and DDD principles."

## 🤝 Contributing

This is a personal learning project by Alireza Ghaderi. Feel free to fork and experiment!

## 📄 License

MIT License - see LICENSE file for details.