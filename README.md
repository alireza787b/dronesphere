# DroneSphere - AI-Powered Drone Control System

> Natural language drone control through conversational AI with enterprise-grade architecture

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal-orange)](docs/architecture/decisions/ADR-001-hexagonal-architecture.md)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 🎯 Project Vision

DroneSphere is an open-source platform that bridges natural language and drone control, allowing operators to command drones through conversational interfaces. Built with a focus on safety, extensibility, and educational use.

### Core Goals
- **Natural Language Control**: "Take off to 50 meters" → Drone executes
- **Multi-Language Support**: English and Persian (Farsi) initially
- **Safety First**: Multiple validation layers before command execution
- **Educational Focus**: Perfect for universities and research
- **Enterprise Ready**: Scalable architecture for commercial use
- **Plugin System**: Extend functionality without modifying core

## 📊 Current Development Status

### 🚀 Current Step: 2 of 25 - Development Environment Configuration (IN PROGRESS)

#### ✅ Completed in Step 1:
- Project structure following hexagonal architecture
- Python environment with Poetry dependency management
- Complete project file structure with all directories
- Development tools: Black, isort, flake8, mypy, pytest
- Pre-commit hooks configuration
- Comprehensive .gitignore
- Makefile with 20+ automation commands
- Environment configuration system (.env files)
- Architecture Decision Records (ADRs)
- Basic test structure

#### 🔧 In Progress (Step 2):
- Docker development environment setup
- PostgreSQL with PostGIS for geospatial data
- Redis for caching
- RabbitMQ for message queuing
- PX4 SITL simulator configuration
- MAVSDK server setup
- Development environment testing scripts

## 🏗️ Architecture Overview

### Hexagonal Architecture (Ports & Adapters)
```
┌─────────────────────────────────────────────────────────────┐
│                        APPLICATION CORE                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   Domain    │  │   Use Cases  │  │  Domain Services │   │
│  │   Models    │  │  (Commands)  │  │   (Business      │   │
│  │             │  │              │  │    Logic)        │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴────────────────────────────────┐
│                         ADAPTERS                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   REST   │  │WebSocket │  │  MAVSDK  │  │    AI    │    │
│  │   API    │  │   API    │  │ Adapter  │  │ Adapters │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└───────────────────────────────────────────────────────────────┘
```

## 📁 Complete Project Structure

```
dronesphere/
├── src/                           # All source code
│   ├── core/                      # Business logic (no external dependencies)
│   │   ├── domain/                # Core business entities and rules
│   │   │   ├── entities/          # Drone, Mission, Command objects
│   │   │   │   └── __init__.py
│   │   │   ├── value_objects/     # Position, Telemetry, CommandParams
│   │   │   │   └── __init__.py
│   │   │   ├── events/            # Domain events
│   │   │   │   └── __init__.py
│   │   │   ├── exceptions/        # Domain-specific exceptions
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── application/           # Use cases and orchestration
│   │   │   ├── commands/          # Command handlers
│   │   │   │   └── __init__.py
│   │   │   ├── queries/           # Query handlers
│   │   │   │   └── __init__.py
│   │   │   ├── services/          # Domain services
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   └── ports/                 # Interfaces for external systems
│   │       ├── input/             # How external systems call us
│   │       │   └── __init__.py
│   │       ├── output/            # How we call external systems
│   │       │   └── __init__.py
│   │       └── __init__.py
│   │
│   ├── adapters/                  # Implementations of ports
│   │   ├── input/                 # Incoming adapters
│   │   │   ├── api/               # REST and WebSocket APIs
│   │   │   │   ├── rest/          # FastAPI REST endpoints
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── websocket/     # Real-time WebSocket
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   ├── cli/               # Command-line interface
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   ├── output/                # Outgoing adapters
│   │   │   ├── drone/             # Drone control adapters
│   │   │   │   ├── mavsdk/        # MAVSDK implementation
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── simulator/     # Simulator adapters
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   ├── ai/                # AI/LLM adapters
│   │   │   │   ├── ollama/        # Local Ollama
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── openai/        # OpenAI API
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   ├── persistence/       # Database adapters
│   │   │   │   ├── postgresql/    # PostgreSQL adapter
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── redis/         # Redis adapter
│   │   │   │   │   └── __init__.py
│   │   │   │   └── __init__.py
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── shared/                    # Shared utilities
│   │   ├── constants/             # System-wide constants
│   │   │   └── __init__.py
│   │   ├── utils/                 # Utility functions
│   │   │   └── __init__.py
│   │   └── __init__.py
│   └── __init__.py
│
├── resources/                     # Configuration and static files
│   ├── commands/                  # Command definitions (YAML)
│   │   ├── core/                  # Core commands
│   │   └── plugins/               # Plugin commands
│   ├── prompts/                   # AI prompt templates
│   │   ├── intent_classification/ # Intent detection prompts
│   │   ├── parameter_extraction/  # Parameter extraction prompts
│   │   └── safety_validation/     # Safety check prompts
│   └── configs/                   # System configurations
│       ├── drone_profiles/        # Drone configuration profiles
│       └── safety_rules/          # Safety constraint definitions
│
├── plugins/                       # Plugin system
│   ├── examples/                  # Example plugins
│   └── __init__.py
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   │   ├── core/                  # Core logic tests
│   │   └── adapters/              # Adapter tests
│   ├── integration/               # Integration tests
│   ├── e2e/                       # End-to-end tests
│   ├── fixtures/                  # Test fixtures
│   └── conftest.py                # Pytest configuration
│
├── deploy/                        # Deployment configurations
│   ├── docker/                    # Docker files
│   │   ├── config/                # Docker config files
│   │   │   └── init-db.sql        # Database initialization
│   │   ├── docker-compose.yaml    # Main services
│   │   ├── simulator-compose.yaml # Simulator services
│   │   ├── Dockerfile.dev         # Development Dockerfile
│   │   └── .env.docker            # Docker environment vars
│   ├── kubernetes/                # K8s manifests
│   └── terraform/                 # Infrastructure as Code
│
├── scripts/                       # Utility scripts
│   ├── setup.sh                   # Initial setup script
│   └── test_environment.py        # Environment verification
│
├── docs/                          # Documentation
│   ├── architecture/              # Architecture documentation
│   │   └── decisions/             # ADRs
│   │       └── ADR-001-hexagonal-architecture.md
│   ├── api/                       # API documentation
│   ├── development/               # Developer guides
│   └── deployment/                # Deployment guides
│
├── web/                           # Frontend application
│   ├── src/                       # React source code
│   ├── public/                    # Static assets
│   └── package.json               # Node.js dependencies
│
├── .github/                       # GitHub specific files
│   ├── workflows/                 # GitHub Actions
│   └── ISSUE_TEMPLATE/            # Issue templates
│
├── pyproject.toml                 # Poetry configuration
├── poetry.lock                    # Locked dependencies
├── Makefile                       # Task automation
├── .env.example                   # Example environment variables
├── .env                           # Local environment variables (gitignored)
├── .gitignore                     # Git ignore rules
├── .pre-commit-config.yaml        # Pre-commit hooks
├── README.md                      # This file
└── LICENSE                        # MIT License
```

## 🚀 Complete Setup Guide for Fresh Ubuntu System

### System Requirements
- Ubuntu 20.04+ (or compatible Linux distribution)
- Python 3.10 or higher
- 8GB RAM minimum (16GB recommended for simulation)
- 20GB free disk space

### Step-by-Step Setup

#### 1. Update System and Install Prerequisites
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.10 and development tools
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# Install build essentials
sudo apt install -y build-essential git curl wget

# Install PostgreSQL client libraries (needed for asyncpg)
sudo apt install -y libpq-dev

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect

# Install Docker Compose
sudo apt install -y docker-compose
```

#### 2. Install Poetry
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH (add this to ~/.bashrc)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify Poetry installation
poetry --version
```

#### 3. Clone and Setup Project
```bash
# Clone the repository
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install all dependencies
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Copy environment variables
cp .env.example .env
```

#### 4. Configure Environment Variables
Edit `.env` file with:
```bash
# Application
APP_NAME=DroneSphere
APP_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Security
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Database
DATABASE_URL=postgresql+asyncpg://dronesphere:dronesphere_pass_dev@localhost:5432/dronesphere
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# RabbitMQ
RABBITMQ_URL=amqp://dronesphere:dronesphere_pass_dev@localhost:5672/dronesphere

# Drone Configuration
MAVSDK_SERVER_ADDRESS=localhost
MAVSDK_SERVER_PORT=50040
DEFAULT_DRONE_ID=1

# AI Configuration
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-openai-key-if-using
AI_PROVIDER=ollama  # ollama, openai, or anthropic

# Safety Configuration
MAX_ALTITUDE_METERS=120
MAX_DISTANCE_METERS=500
MIN_BATTERY_PERCENT=20
ENABLE_GEOFENCING=True
```

#### 5. Start Docker Services
```bash
# Create Docker network
docker network create dronesphere-network

# Start all services
make docker-up

# Wait for services to initialize
sleep 30

# Check service status
make docker-ps

# Test the environment
python scripts/test_environment.py
```

#### 6. Access Services
- **Database UI (Adminer)**: http://localhost:8080
  - System: PostgreSQL
  - Server: postgres
  - Username: dronesphere
  - Password: dronesphere_pass_dev
  - Database: dronesphere

- **RabbitMQ Management**: http://localhost:15672
  - Username: dronesphere
  - Password: dronesphere_pass_dev

#### 7. Verify Setup
```bash
# Run all tests
make test

# Check code quality
make lint

# Format code
make format

# See all available commands
make help
```

## 🛠️ Technology Stack Details

### Backend Technologies
- **Python 3.10+**: Modern Python with type hints
- **Poetry**: Dependency management and packaging
- **FastAPI**: High-performance async web framework
- **SQLAlchemy 2.0**: Async ORM with PostgreSQL
- **Redis**: In-memory caching and pub/sub
- **RabbitMQ**: Message broker for async tasks
- **MAVSDK**: High-level drone control SDK
- **Pydantic**: Data validation and settings
- **pytest**: Testing framework with async support

### AI/ML Stack
- **Ollama**: Local LLM inference
- **LangChain**: LLM application framework
- **OpenAI API**: Cloud-based GPT models
- **Anthropic API**: Claude integration
- **Transformers**: Hugging Face models

### Infrastructure
- **PostgreSQL 15**: Main database with PostGIS
- **Redis 7**: Caching and real-time features
- **RabbitMQ 3.12**: Message queuing
- **Docker**: Containerization
- **Docker Compose**: Local orchestration

### Development Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pre-commit**: Git hooks
- **pytest-cov**: Test coverage

## 🔧 Makefile Commands Reference

```bash
# Setup
make install          # Install all dependencies
make install-dev      # Install with dev dependencies

# Development
make run             # Run the application
make run-dev         # Run with hot reload
make shell           # Open Python shell with app context

# Testing
make test            # Run all tests
make test-unit       # Run unit tests only
make test-integration # Run integration tests
make test-cov        # Run tests with coverage
make test-watch      # Run tests in watch mode

# Code Quality
make format          # Format code with black and isort
make lint            # Run all linters
make type-check      # Run mypy type checking
make security-check  # Run security checks

# Docker
make docker-up       # Start all services
make docker-down     # Stop all services
make docker-logs     # View service logs
make docker-ps       # List running services
make docker-clean    # Remove containers and volumes

# Database
make db-upgrade      # Run database migrations
make db-downgrade    # Rollback migrations
make db-reset        # Reset database

# Documentation
make docs            # Generate documentation
make docs-serve      # Serve documentation locally

# Cleanup
make clean           # Remove build artifacts
make clean-all       # Remove everything including .venv
```

## 📋 Current Implementation Details

### What's Been Implemented

1. **Project Structure**
   - Complete hexagonal architecture setup
   - All directories created with `__init__.py` files
   - Separation of concerns (core, adapters, ports)

2. **Development Environment**
   - Poetry for dependency management
   - Virtual environment configuration
   - Environment variables with `.env` files
   - Git repository with comprehensive `.gitignore`

3. **Code Quality Tools**
   - Black for code formatting
   - isort for import sorting
   - flake8 for linting
   - mypy for type checking
   - Pre-commit hooks configured

4. **Testing Framework**
   - pytest setup with async support
   - Test directory structure
   - Fixtures configuration
   - Coverage reporting setup

5. **Documentation**
   - Architecture Decision Records (ADRs)
   - Comprehensive README
   - Code structure documentation

6. **Docker Configuration**
   - PostgreSQL with PostGIS
   - Redis for caching
   - RabbitMQ for messaging
   - Adminer for database UI
   - Docker Compose for orchestration
   - Network configuration

7. **Automation**
   - Makefile with 20+ commands
   - Setup scripts
   - Environment testing script

### What's Next (Step 3 onwards)

1. **Domain Models** (Step 3)
   - Implement Drone entity
   - Create Position and Telemetry value objects
   - Define Command base classes
   - Create domain events

2. **Basic Testing** (Step 4)
   - Unit tests for domain models
   - Integration test setup
   - Test fixtures for common scenarios

3. **CI/CD Pipeline** (Step 5)
   - GitHub Actions workflow
   - Automated testing on PR
   - Code quality checks
   - Docker image building

## 🐛 Known Issues and Solutions

### Docker on WSL Issues
- Docker Desktop integration with WSL can be problematic
- Solution: Use native Linux VM or ensure Docker Desktop WSL integration is enabled

### Poetry Virtual Environment
- Sometimes Poetry creates its own venv
- Solution: Use `poetry config virtualenvs.in-project true`

### Port Conflicts
- Services might conflict with existing ports
- Solution: Change ports in `docker-compose.yaml`

## 🔄 State Transfer for AI Continuation

### Current State Summary
- **Project**: DroneSphere - AI-powered drone control
- **Architecture**: Hexagonal (Ports & Adapters)
- **Current Step**: 2 of 25 (Development Environment)
- **Language**: Python 3.10+
- **Status**: Docker services configured but need testing on fresh Linux

### Completed Tasks
1. ✅ Complete project structure created
2. ✅ Poetry and dependencies configured
3. ✅ Development tools setup (formatters, linters)
4. ✅ Git repository initialized
5. ✅ Environment configuration
6. ✅ Docker services defined
7. ✅ Test framework prepared
8. ⏳ Docker services need testing on Linux

### Next Immediate Tasks
1. Test Docker services on fresh Ubuntu
2. Verify all services are running
3. Run environment test script
4. Begin implementing domain models (Step 3)

### Key Files to Check
- `/deploy/docker/docker-compose.yaml` - Service definitions
- `/scripts/test_environment.py` - Environment verification
- `/Makefile` - All available commands
- `/.env` - Environment configuration
- `/pyproject.toml` - Python dependencies

### Important Context
- Moving from WSL to Ubuntu VM due to Docker issues
- All code is ready, just needs Docker verification
- Database includes PostGIS for drone GPS data
- Using MAVSDK for drone control (will add in Step 7)

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

---

**For AI Assistants**: This project is at Step 2 of 25. The immediate task is to verify Docker services work on Ubuntu and then proceed to Step 3 (Domain Models Implementation). All configuration files are in the repository. The architecture is hexagonal with a focus on safety and extensibility.
