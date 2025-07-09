# 🚁 DroneSphere - Autonomous Drone Command & Control System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

> **Professional autonomous drone command and control system with clean architecture for scalable multi-drone operations.**

DroneSphere provides a robust, production-ready platform for autonomous drone operations with clear separation between hardware interface and coordination logic. Built with modern Python best practices and designed for real-world deployment scenarios.

## 🎯 Current Status: Phase 1 Complete ✅

**Production-Ready Foundation** - Autonomous missions, professional tooling, deployment-ready architecture

### ✅ Implemented Features
- **Autonomous Mission Execution**: Complete takeoff → navigation → landing workflows
- **Real-time Telemetry**: Position tracking, health monitoring, status reporting
- **Professional Architecture**: Clean separation of agent (hardware) and server (coordination)
- **Command System**: Extensible YAML-based command definitions with validation
- **Quality Tooling**: Code formatting, linting, testing, pre-commit hooks
- **Production Deployment**: Separate environments optimized for different hardware

### 🚀 Quick Demo

```bash
# Start the complete system (3 terminals)
./scripts/run_sitl.sh      # Terminal 1: SITL simulator
./scripts/start-server.sh  # Terminal 2: Coordination server  
./scripts/start-agent.sh   # Terminal 3: Drone agent

# Execute autonomous mission
curl -X POST localhost:8002/drones/1/commands \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 10.0}},
      {"name": "goto", "params": {"latitude": -35.36, "longitude": 149.16, "altitude": 10.0}},
      {"name": "wait", "params": {"duration": 5.0}},
      {"name": "land", "params": {}}
    ]
  }'
```

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DroneSphere System                       │
├─────────────────┬───────────────────────┬─────────────────────┤
│   Coordination  │                       │   Hardware Interface │
│     Server      │    Shared Components  │       Agent         │
│                 │                       │                     │
│  ┌──────────┐   │  ┌─────────────────┐  │   ┌──────────────┐  │
│  │Fleet Mgmt│   │  │Core Utilities   │  │   │MAVSDK Backend│  │
│  │Telemetry │   │  │Command Registry │  │   │Command Exec │  │
│  │API Server│   │  │Models & Config  │  │   │Hardware I/O  │  │
│  │          │   │  │Logging System   │  │   │Heartbeat     │  │
│  └──────────┘   │  └─────────────────┘  │   └──────────────┘  │
│                 │                       │                     │
│ Port: 8002      │   YAML Commands       │    Port: 8001       │
│ Full-featured   │   Shared Configs      │    Lightweight      │
└─────────────────┴───────────────────────┴─────────────────────┘
```

### Component Separation

**🖥️ Server** (`dronesphere/server/`)
- **Purpose**: Multi-drone coordination, mission planning, telemetry aggregation
- **Deployment**: Powerful coordination hardware (cloud, ground station)
- **Dependencies**: Full feature set (monitoring, analytics, fleet management)

**📱 Agent** (`dronesphere/agent/`)  
- **Purpose**: Direct hardware interface, command execution, real-time control
- **Deployment**: Drone hardware (Raspberry Pi, companion computers)
- **Dependencies**: Minimal footprint (essential flight operations only)

**🔗 Shared** (`dronesphere/core/`, `shared/`)
- **Purpose**: Common utilities, command definitions, configuration
- **Deployment**: Included with both agent and server
- **Contents**: Models, logging, command registry, YAML definitions

## ⚡ Quick Start

### Prerequisites
- **Python 3.10+**
- **UV** (recommended) or pip
- **Docker** (for SITL simulation)
- **Linux/macOS** (tested on Ubuntu 20.04+)

### 1. Clone and Setup
```bash
git clone https://github.com/alireza787/dronesphere.git
cd dronesphere

# Automated setup (creates both environments)
./scripts/setup-environments.sh
```

### 2. Development Mode (Local Testing)
```bash
# Terminal 1: Start SITL simulator
./scripts/run_sitl.sh

# Terminal 2: Start coordination server
./scripts/start-server.sh

# Terminal 3: Start drone agent
./scripts/start-agent.sh

# Terminal 4: Test the system
./scripts/test-mission.sh
```

### 3. Verify Installation
```bash
# Check all components
./scripts/validate-setup.sh

# Check service health
curl localhost:8002/ping    # Server health
curl localhost:8001/health  # Agent health
```

## 📖 Detailed Setup

### Development Environment

```bash
# 1. Install UV (recommended package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# 2. Clone repository
git clone https://github.com/alireza787/dronesphere.git
cd dronesphere

# 3. Create separate environments
cd dronesphere/agent
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e ../..
deactivate

cd ../server  
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e ../..
deactivate

cd ../..

# 4. Setup development tools
cd dronesphere/server && source .venv/bin/activate && cd ../..
pre-commit install
deactivate

# 5. Verify setup
./scripts/validate-setup.sh
```

### Production Deployment

#### Agent Deployment (Drone Hardware)
```bash
# On development machine
tar -czf dronesphere-agent.tar.gz dronesphere/agent/ dronesphere/core/ dronesphere/commands/ dronesphere/backends/ shared/

# On drone hardware (Raspberry Pi, etc.)
scp dronesphere-agent.tar.gz drone-pi:/tmp/
ssh drone-pi
cd /opt && sudo tar -xzf /tmp/dronesphere-agent.tar.gz
cd dronesphere

# Setup agent environment
cd agent && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ..
cd .. && ./scripts/start-agent.sh
```

#### Server Deployment (Coordination Hardware)
```bash
# On development machine  
tar -czf dronesphere-server.tar.gz dronesphere/server/ dronesphere/core/ dronesphere/commands/ dronesphere/backends/ shared/

# On coordination hardware
scp dronesphere-server.tar.gz coord-server:/tmp/
ssh coord-server
cd /opt && sudo tar -xzf /tmp/dronesphere-server.tar.gz
cd dronesphere

# Setup server environment
cd server && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ..
cd .. && ./scripts/start-server.sh
```

## 🔧 Development Workflow

### Code Quality
```bash
# Format code automatically
./scripts/format-code.sh

# Run linting checks
./scripts/check-quality.sh

# Run tests
./scripts/run-tests.sh                    # Unit tests only
./scripts/run-tests.sh integration       # Integration tests
./scripts/run-tests.sh all              # All tests
```

### Pre-commit Hooks
```bash
# Automatically run on every commit
git add . && git commit -m "Your changes"

# Run manually on all files
pre-commit run --all-files

# Update hook versions
pre-commit autoupdate
```

### Testing Strategy
```bash
# Unit tests (fast, no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v -m integration

# SITL integration tests (requires SITL)
pytest tests/integration/sitl/ -v -m sitl
```

## 🚀 Usage Examples

### Basic Mission Execution
```bash
# Health check
curl localhost:8001/health
curl localhost:8002/ping

# Simple takeoff and land
curl -X POST localhost:8002/drones/1/commands \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 5.0}},
      {"name": "wait", "params": {"duration": 3.0}},
      {"name": "land", "params": {}}
    ]
  }'
```

### Advanced Navigation
```bash
# Complex mission with waypoints
curl -X POST localhost:8002/drones/1/commands \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 15.0}},
      {"name": "goto", "params": {
        "latitude": -35.363261, 
        "longitude": 149.165230, 
        "altitude": 15.0
      }},
      {"name": "circle", "params": {
        "radius": 10.0, 
        "velocity": 3.0, 
        "duration": 30.0
      }},
      {"name": "rtl", "params": {}}
    ],
    "metadata": {
      "mission_name": "patrol_area_alpha",
      "priority": "normal"
    }
  }'
```

### Real-time Monitoring
```bash
# Get drone status
curl localhost:8001/status

# Get telemetry data
curl localhost:8001/telemetry

# Monitor mission progress
curl localhost:8002/drones/1/status

# Get fleet overview
curl localhost:8002/fleet/status
```

## 📡 API Reference

### Agent API (Port 8001)
```
GET  /health           # Agent health status
GET  /status           # Drone status and state
GET  /telemetry        # Real-time telemetry data
POST /commands         # Execute command sequence
GET  /commands/{id}    # Get command execution status
```

### Server API (Port 8002)
```
GET  /ping                    # Server health check
GET  /fleet/status           # All drones status
POST /drones/{id}/commands   # Send commands to specific drone
GET  /drones/{id}/status     # Get drone status
GET  /drones/{id}/telemetry  # Get drone telemetry
GET  /missions              # List all missions
POST /missions              # Create new mission
```

### Command Types
- **takeoff**: `{"name": "takeoff", "params": {"altitude": 10.0}}`
- **land**: `{"name": "land", "params": {}}`
- **goto**: `{"name": "goto", "params": {"latitude": -35.36, "longitude": 149.16, "altitude": 10.0}}`
- **wait**: `{"name": "wait", "params": {"duration": 5.0}}`
- **rtl**: `{"name": "rtl", "params": {}}`
- **circle**: `{"name": "circle", "params": {"radius": 10.0, "velocity": 3.0, "duration": 30.0}}`

## 🔄 Current Progress & Roadmap

### ✅ Phase 1: Foundation (Complete)
- [x] Core architecture with agent/server separation
- [x] MAVSDK backend integration for PX4/ArduPilot
- [x] Command registry system with YAML definitions
- [x] Real-time telemetry and status monitoring
- [x] Professional development workflow (formatting, linting, testing)
- [x] Production deployment structure
- [x] Autonomous mission execution (takeoff, navigation, landing)
- [x] SITL integration for testing
- [x] Comprehensive documentation and setup guides

### 🚧 Phase 2: Advanced Features (Planned)
- [ ] **Multi-drone Coordination**: Fleet management and synchronized operations
- [ ] **Advanced Path Planning**: Obstacle avoidance and optimized routes
- [ ] **Mission Planning UI**: Web-based interface for mission design
- [ ] **Real-time Monitoring Dashboard**: Live telemetry visualization
- [ ] **Hardware-in-the-Loop Testing**: Integration with real flight controllers
- [ ] **Advanced Safety Features**: Geofencing, emergency protocols
- [ ] **Performance Analytics**: Mission analysis and optimization

### 🔮 Phase 3: Enterprise Features (Future)
- [ ] **Cloud Integration**: AWS/Azure deployment and scaling
- [ ] **AI/ML Integration**: Intelligent mission optimization
- [ ] **Advanced Security**: Authentication, encryption, audit logging
- [ ] **Integration APIs**: Third-party system connectivity
- [ ] **Advanced Telemetry**: Custom sensor integration
- [ ] **Compliance Tools**: Aviation authority reporting

## 🏗️ Project Structure

```
dronesphere/
├── 📱 agent/                    # Drone hardware interface
│   ├── .venv/                  # Lightweight Python environment
│   ├── requirements.txt        # Minimal dependencies for drone hardware
│   ├── api.py                  # Agent REST API endpoints
│   ├── main.py                 # Agent application entry point
│   ├── config.py               # Agent-specific configuration
│   ├── heartbeat.py           # Server communication heartbeat
│   ├── instance.py            # Agent instance management
│   └── executor/              # Command execution engine
│       ├── connection.py      # Drone hardware connection
│       └── runner.py          # Command execution logic
├── 🖥️ server/                  # Coordination server
│   ├── .venv/                 # Full-featured Python environment
│   ├── requirements.txt       # Complete server dependencies
│   ├── api.py                 # Server REST API endpoints
│   ├── main.py                # Server application entry point
│   ├── config.py              # Server-specific configuration
│   ├── client.py              # Agent communication client
│   └── coordinator/           # Multi-drone coordination
│       ├── fleet.py          # Fleet management logic
│       └── telemetry.py      # Telemetry aggregation
├── 🔗 core/                    # Shared utilities
│   ├── config.py              # Global configuration management
│   ├── logging.py             # Structured logging setup
│   ├── models.py              # Pydantic data models
│   ├── errors.py              # Custom exception classes
│   └── utils.py               # Common utility functions
├── 🎮 commands/                # Command system
│   ├── base.py                # Base command interface
│   ├── registry.py            # Command registry and loader
│   ├── basic/                 # Basic flight commands
│   │   ├── takeoff.py        # Takeoff command implementation
│   │   ├── land.py           # Landing command implementation
│   │   └── rtl.py            # Return-to-launch implementation
│   ├── navigation/            # Navigation commands
│   │   ├── goto.py           # Point-to-point navigation
│   │   └── circle.py         # Circular pattern flight
│   └── utility/               # Utility commands
│       └── wait.py           # Wait/delay command
├── 🔌 backends/               # Hardware interface backends
│   ├── base.py               # Backend interface definition
│   ├── mavsdk.py             # MAVSDK backend (primary)
│   ├── pymavlink.py          # PyMAVLink backend (alternative)
│   └── mavlink2rest.py       # REST API backend (optional)
├── 📄 shared/                 # Shared configurations
│   ├── commands/             # YAML command definitions
│   │   ├── basic/           # Basic command YAML specs
│   │   ├── navigation/      # Navigation command YAML specs
│   │   └── utility/         # Utility command YAML specs
│   ├── config/              # Environment configurations
│   └── drones.yaml          # Drone fleet configuration
├── 🧪 tests/                  # Test suite
│   ├── unit/                # Unit tests (fast, isolated)
│   ├── integration/         # Integration tests (services required)
│   └── conftest.py          # Pytest configuration and fixtures
├── 🛠️ scripts/               # Development and deployment tools
│   ├── run_sitl.sh          # Start SITL simulator
│   ├── start-server.sh      # Start coordination server
│   ├── start-agent.sh       # Start drone agent
│   ├── test-mission.sh      # Execute test mission
│   ├── format-code.sh       # Code formatting
│   ├── run-tests.sh         # Test execution
│   ├── check-quality.sh     # Quality validation
│   └── validate-setup.sh    # Setup verification
├── 📚 docs/                   # Documentation
│   ├── api.md               # API reference documentation
│   ├── architecture.md     # System architecture details
│   ├── deployment.md        # Production deployment guide
│   └── development.md       # Development workflow guide
├── 🐳 docker/                 # Docker configurations
│   ├── sitl/               # SITL container setup
│   └── docker-compose.yml  # Complete development environment
├── ⚙️ .pre-commit-config.yaml # Code quality automation
├── 🧪 pytest.ini             # Test configuration
├── 📦 pyproject.toml          # Project metadata and dependencies
└── 📖 README.md               # This file
```

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup
```bash
# Fork and clone
git clone https://github.com/yourusername/dronesphere.git
cd dronesphere

# Setup development environment
./scripts/setup-environments.sh

# Install pre-commit hooks
cd dronesphere/server && source .venv/bin/activate && cd ../..
pre-commit install
```

### Code Standards
- **Python 3.10+** required
- **Black** for code formatting (88 character line length)
- **Ruff** for linting and import sorting
- **Type hints** encouraged for new code
- **Docstrings** required for public functions and classes
- **Tests** required for new features

### Pull Request Process
1. **Create feature branch**: `git checkout -b feature/your-feature-name`
2. **Write tests** for new functionality
3. **Run quality checks**: `./scripts/check-quality.sh`
4. **Update documentation** if needed
5. **Submit pull request** with clear description

### Code Review Checklist
- [ ] All tests pass (`./scripts/run-tests.sh all`)
- [ ] Code follows style guidelines (`./scripts/format-code.sh`)
- [ ] New features have tests
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

### Key License Points
- ✅ **Commercial use** permitted
- ✅ **Modification** and **distribution** allowed
- ✅ **Private use** allowed
- ⚠️ **Warranty disclaimer** - use at your own risk
- 📝 **Attribution** required in distributions

## 🙏 Acknowledgments

### Technologies Used
- **[MAVSDK-Python](https://github.com/mavlink/MAVSDK-Python)** - Primary drone communication library
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern async web framework
- **[PX4](https://px4.io/)** - Advanced flight control software
- **[ArduPilot](https://ardupilot.org/)** - Comprehensive vehicle control system
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Data validation and parsing
- **[Structlog](https://www.structlog.org/)** - Structured logging

### Inspiration
- **[DroneKit](https://github.com/dronekit/dronekit-python)** - Pioneer in Python drone APIs
- **[QGroundControl](https://qgroundcontrol.com/)** - Professional ground control software
- **[PX4 Development Team](https://px4.io/community/)** - Advanced autopilot development

### Community
- **[MAVLink Community](https://mavlink.io/)** - Drone communication protocol
- **[PX4 Community](https://discuss.px4.io/)** - Flight stack development
- **[ArduPilot Community](https://discuss.ardupilot.org/)** - Open source vehicle control

## 📞 Support & Contact

### Getting Help
- **📖 Documentation**: Start with this README and `docs/` directory
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/alireza787/dronesphere/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/alireza787/dronesphere/discussions)
- **❓ Questions**: [GitHub Discussions Q&A](https://github.com/alireza787/dronesphere/discussions/categories/q-a)

### Project Maintainer
- **GitHub**: [@alireza787](https://github.com/alireza787)
- **Repository**: [alireza787/dronesphere](https://github.com/alireza787/dronesphere)

### Development Status
- **Current Version**: Phase 1 Complete
- **Stability**: Production Ready Foundation
- **Next Release**: Phase 2 Multi-drone Features
- **Update Frequency**: Active development

---

<div align="center">

**Built with ❤️ for the drone development community**

⭐ **Star this repository** if you find it useful!

[🚀 Get Started](#quick-start) | [📖 Documentation](docs/) | [🤝 Contributing](#contributing) | [🐛 Issues](https://github.com/alireza787/dronesphere/issues)

</div>