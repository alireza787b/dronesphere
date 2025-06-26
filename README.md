# DroneSphere - AI-Powered Drone Control System

> Natural language drone control through conversational AI with enterprise-grade architecture

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![Package Manager](https://img.shields.io/badge/package_manager-uv-orange)](https://github.com/astral-sh/uv)
[![Architecture](https://img.shields.io/badge/architecture-hexagonal-green)](docs/architecture/decisions/ADR-001-hexagonal-architecture.md)
[![License](https://img.shields.io/badge/license-MIT-purple)](LICENSE)

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

### 🚀 Current Step: 4 of 25 - Natural Language Processing (READY TO START)

#### ✅ Completed Steps:
1. **Step 1**: Project structure with hexagonal architecture
2. **Step 2**: Development environment with Docker services
3. **Step 3**: Core domain models (entities, value objects, events)
   - Migrated from Poetry to UV for faster dependency management
   - Implemented 3-component architecture

#### 🔧 Next Step (Step 4):
- Implement NLP service using spaCy
- Create natural language to command parser
- Integrate intent classification
- Build parameter extraction system

## 🏗️ Architecture Overview

### Three-Component System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     1. FRONTEND (Future)                      │
│                   React/Next.js Web App                       │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST/WebSocket
┌───────────────────────────┴─────────────────────────────────┐
│                     2. SERVER (Current Focus)                 │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   FastAPI   │  │     NLP      │  │  Domain Logic    │   │
│  │   REST/WS   │  │   Service    │  │  & Use Cases     │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Database   │  │    Redis     │  │   RabbitMQ       │   │
│  │ PostgreSQL  │  │   Cache      │  │  Message Queue   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │ Commands/Telemetry
┌───────────────────────────┴─────────────────────────────────┐
│              3. DRONE CONTROLLER (Raspberry Pi)               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   MAVSDK    │  │   Command    │  │    Safety        │   │
│  │  Adapter    │  │   Receiver   │  │    System        │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │ MAVLink
                     ┌──────┴──────┐
                     │   Pixhawk   │
                     │  Autopilot  │
                     └─────────────┘
```

## 📁 Project Structure

```
dronesphere/
├── server/                        # Main server application
│   ├── src/
│   │   ├── core/                  # Business logic (no external dependencies)
│   │   │   ├── domain/            # Entities, value objects, events
│   │   │   ├── application/       # Use cases and services
│   │   │   └── ports/             # Interface definitions
│   │   ├── adapters/              # Interface implementations
│   │   │   ├── input/             # REST API, WebSocket, CLI
│   │   │   └── output/            # Database, AI, external services
│   │   └── shared/                # Shared utilities
│   ├── tests/                     # Test suite
│   ├── scripts/                   # Utility scripts
│   └── pyproject.toml             # UV/Python configuration
│
├── drone_controller/              # Raspberry Pi drone controller
│   ├── src/
│   │   ├── mavsdk_adapter/       # MAVSDK integration
│   │   ├── command_receiver/      # Receives commands from server
│   │   ├── telemetry/            # Sends telemetry to server
│   │   └── safety/               # Local safety checks
│   ├── tests/
│   ├── requirements.txt          # Simple requirements for Pi
│   └── main.py                   # Entry point
│
├── frontend/                      # React/Next.js web app (future)
│   ├── src/
│   ├── public/
│   └── package.json
│
├── shared/                        # Shared contracts/types
│   └── proto/                     # Protocol definitions
│
├── deploy/                        # Deployment configurations
│   ├── docker/                    # Docker files
│   │   ├── docker-compose.yaml    # Development services
│   │   └── Dockerfile             # Production image
│   └── kubernetes/                # K8s manifests (future)
│
├── docs/                          # Documentation
│   ├── architecture/              # Architecture documentation
│   ├── api/                       # API documentation
│   └── setup/                     # Setup guides
│
├── .github/                       # GitHub configuration
├── Makefile                       # Task automation
├── README.md                      # This file
└── LICENSE                        # MIT License
```

## 🚀 Quick Start Guide for Ubuntu

### Prerequisites
- Ubuntu 20.04+ (or compatible Linux)
- Python 3.10 or higher
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### 1. Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10 and development tools
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip

# Install build essentials
sudo apt install -y build-essential git curl wget net-tools tmux

# Install PostgreSQL client libraries (for asyncpg)
sudo apt install -y libpq-dev

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for docker group

# Install Docker Compose
sudo apt install -y docker-compose
```

### 2. Install UV (Ultra-fast Python Package Manager)
```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc for persistence)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
uv --version
```

### 3. Clone and Setup Project
```bash
# Clone repository
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere

# Create virtual environment with UV
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
uv pip install -e ".[dev]"

# Setup pre-commit hooks
pre-commit install

# Copy environment configuration
cp .env.example .env
```

### 4. Start Docker Services
```bash
# Create network
docker network create dronesphere-network

# Start all services
docker-compose -f deploy/docker/docker-compose.yaml up -d

# Check service status
docker-compose -f deploy/docker/docker-compose.yaml ps

# View logs if needed
docker-compose -f deploy/docker/docker-compose.yaml logs -f
```

### 5. Verify Installation
```bash
# Run domain model tests
python scripts/test_domain_models.py

# Run all tests
pytest

# Check code quality
flake8 src/
mypy src/

# Test database connection
python scripts/test_environment.py
```

## 🛠️ Development with UV

### Common UV Commands
```bash
# Install dependencies
uv pip install -e ".[dev]"

# Add new dependency
uv pip install package-name

# Update dependencies
uv pip install --upgrade package-name

# Install from requirements file
uv pip install -r requirements.txt

# Show installed packages
uv pip list

# Create new virtual environment
uv venv

# Run Python scripts
uv run python script.py
```

### Makefile Commands
```bash
# Development
make run              # Run the server
make run-dev          # Run with hot reload
make test             # Run all tests
make test-watch       # Run tests in watch mode

# Code Quality
make format           # Format code with black/isort
make lint             # Run linters
make type-check       # Run mypy
make quality          # Run all quality checks

# Docker
make docker-up        # Start services
make docker-down      # Stop services
make docker-logs      # View logs
make docker-clean     # Clean up

# Database
make db-migrate       # Run migrations
make db-reset         # Reset database

# Documentation
make docs             # Generate docs
make docs-serve       # Serve docs locally

# Drone Controller (Raspberry Pi)
make pi-setup         # Setup Pi environment
make pi-deploy        # Deploy to Pi
make pi-logs          # View Pi logs
```

## 📋 Environment Configuration

Create `.env` file with:
```bash
# Application
APP_NAME=DroneSphere
APP_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG

# Server API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Security
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:8090

# Database
DATABASE_URL=postgresql+asyncpg://dronesphere:dronesphere_pass_dev@localhost:5432/dronesphere
DATABASE_POOL_SIZE=5

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://dronesphere:dronesphere_pass_dev@localhost:5672/

# NLP Configuration
SPACY_MODEL=en_core_web_sm
NLP_CONFIDENCE_THRESHOLD=0.8

# AI/LLM Configuration
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-key-if-using
AI_PROVIDER=ollama

# Drone Configuration
MAVSDK_SERVER_ADDRESS=localhost
MAVSDK_SERVER_PORT=50040
MAX_ALTITUDE_METERS=120
MAX_DISTANCE_METERS=500
MIN_BATTERY_PERCENT=20

# Drone Controller Connection (WebSocket)
DRONE_CONTROLLER_WS_URL=ws://localhost:8001/ws
DRONE_CONTROLLER_API_KEY=your-drone-controller-key
```

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_drone_entity.py

# Run tests in watch mode
ptw

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Test Structure
```
tests/
├── unit/                 # Fast, isolated tests
│   ├── core/            # Domain logic tests
│   └── adapters/        # Adapter tests
├── integration/         # Tests with real dependencies
├── e2e/                 # End-to-end tests
└── fixtures/            # Shared test data
```

## 🚁 Drone Controller Setup (Raspberry Pi)

### Prerequisites for Pi
- Raspberry Pi 4 (4GB+ RAM recommended)
- Ubuntu Server 20.04 for Raspberry Pi
- Python 3.10+
- Internet connection

### Setup on Raspberry Pi
```bash
# On the Raspberry Pi
cd /home/pi
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere/drone_controller

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your server details

# Run the controller
python main.py
```

### Deploy from Development Machine
```bash
# Configure Pi connection in .env
PI_HOST=192.168.1.100
PI_USER=pi
PI_PATH=/home/pi/dronesphere

# Deploy to Pi
make pi-deploy

# View Pi logs
make pi-logs

# Restart Pi service
make pi-restart
```

## 📊 Service Endpoints

### Development Services
- **FastAPI Server**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Database Admin**: http://localhost:8090
  - System: PostgreSQL
  - Server: postgres
  - Username: dronesphere
  - Password: dronesphere_pass_dev
- **RabbitMQ Management**: http://localhost:15672
  - Username: dronesphere
  - Password: dronesphere_pass_dev
- **Redis Commander**: http://localhost:8081

## 🔧 Troubleshooting

### UV Issues
```bash
# If UV not found
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# If permission denied
chmod +x ~/.local/bin/uv

# Clear UV cache if needed
uv cache clean
```

### Docker Issues
```bash
# If services won't start
docker-compose down -v
docker system prune -a
docker-compose up -d

# Check logs
docker-compose logs service-name

# Restart specific service
docker-compose restart postgres
```

### Database Issues
```bash
# Reset database
make db-reset

# Manual connection
psql -h localhost -U dronesphere -d dronesphere

# Check migrations
alembic history
alembic current
```

## 🔄 Development Workflow

1. **Start Services**
   ```bash
   make docker-up
   ```

2. **Activate Environment**
   ```bash
   source .venv/bin/activate
   ```

3. **Run Tests**
   ```bash
   make test
   ```

4. **Start Development Server**
   ```bash
   make run-dev
   ```

5. **Make Changes**
   - Write code
   - Add tests
   - Run `make quality` before commit

6. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: description"
   git push
   ```

## 📝 Next Steps

### Step 4: Natural Language Processing (Current)
- [ ] Install spaCy models
- [ ] Implement NLP adapter
- [ ] Create intent classifier
- [ ] Build parameter extractor
- [ ] Add command parser
- [ ] Write comprehensive tests

### Step 5: Application Services
- [ ] Implement use cases
- [ ] Create command handlers
- [ ] Add validation layer
- [ ] Build query services

### Step 6: API Implementation
- [ ] FastAPI endpoints
- [ ] WebSocket handlers
- [ ] Authentication
- [ ] API documentation

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

**For AI Assistants**: This project uses UV instead of Poetry, has a 3-component architecture (server, drone_controller, frontend), and is currently at Step 4 (NLP implementation). The domain models are complete and tested. Focus on the server component for now.