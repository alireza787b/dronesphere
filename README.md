# README.md
"""
# DroneSphere 🚁

**Scalable drone command and control system built for the future**

[![CI](https://github.com/yourusername/dronesphere/workflows/CI/badge.svg)](https://github.com/yourusername/dronesphere/actions)
[![Coverage](https://codecov.io/gh/yourusername/dronesphere/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/dronesphere)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue)](https://yourusername.github.io/dronesphere)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## 🎯 Phase 1 MVP

Single-drone system that can:
- ✅ Receive takeoff → wait → land sequences via REST API
- ✅ Execute commands in PX4 SITL environment
- ✅ Stream live telemetry
- ✅ Provide real-time command status and queue management
- 🔄 Scale to AI/LLM integration ready

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Server API     │    │      Agent      │
│                 │◄──►│   (FastAPI)      │◄──►│   (MAVSDK)      │
│ POST /command   │    │                  │    │                 │
│ GET  /status    │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ GET  /telemetry │    │ │ Command      │ │    │ │ PX4 SITL    │ │
└─────────────────┘    │ │ Validation   │ │    │ │ Connection  │ │
                       │ └──────────────┘ │    │ └─────────────┘ │
                       │ ┌──────────────┐ │    │ ┌─────────────┐ │
                       │ │ State Mgmt   │ │    │ │ Telemetry   │ │
                       │ └──────────────┘ │    │ │ Cache       │ │
                       └──────────────────┘    │ └─────────────┘ │
                                               └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git

### 1. Setup Environment

```bash
# Clone repository
git clone https://github.com/yourusername/dronesphere.git
cd dronesphere

# Create virtual environment with uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install dependencies
uv pip install -e .[dev]

# Setup pre-commit hooks
pre-commit install
```

### 2. Start SITL Environment

```bash
# Start PX4 SITL + mavlink-router
./scripts/run_sitl.sh

# Verify SITL is running
curl http://localhost:8080/mavlink/vehicles
```

### 3. Run System

```bash
# Terminal 1: Start Agent
python -m dronesphere.agent

# Terminal 2: Start Server  
uvicorn dronesphere.server.api:app --port 8000 --reload

# Terminal 3: Test MVP
curl -X POST localhost:8001/command/1 \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 5}},
      {"name": "wait", "params": {"seconds": 3}},
      {"name": "land"}
    ]
  }'
```

### 4. Monitor Execution

```bash
# Check command status
curl localhost:8001/status/1

# Watch telemetry
curl localhost:8001/telemetry/1

# View Swagger docs
open http://localhost:8001/docs
```

## 📊 API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/command/{drone_id}` | POST | Queue command sequence |
| `/status/{drone_id}` | GET | Current execution status |
| `/telemetry/{drone_id}` | GET | Live telemetry data |
| `/queue/{drone_id}` | GET | Command queue status |
| `/health` | GET | System health check |
| `/metrics` | GET | Prometheus metrics |

### Example Requests

```bash
# Takeoff sequence
curl -X POST localhost:8001/command/1 \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 10}}
    ]
  }'

# Response
{
  "command_id": "cmd_123",
  "status": "accepted",
  "estimated_duration": 30
}

# Check status
curl localhost:8001/status/1
{
  "drone_id": 1,
  "current_command": {
    "id": "cmd_123",
    "name": "takeoff",
    "status": "executing",
    "progress": 0.6,
    "started_at": "2025-01-15T10:30:00Z"
  },
  "queue_length": 0,
  "state": "armed"
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Unit tests only
pytest tests/unit -m unit

# Integration tests (requires SITL)
pytest tests/integration -m integration

# With coverage
pytest --cov=dronesphere --cov-report=html
```

## 📚 Development

### Project Structure

```
dronesphere/
├── dronesphere/           # Main package
│   ├── core/             # Core models and config
│   ├── backends/         # Drone backend implementations
│   ├── commands/         # Command implementations
│   ├── agent/            # Command execution engine
│   └── server/           # REST API
├── shared/               # YAML configurations
├── tests/                # Test suite
├── docker/               # Docker configurations
├── docs/                 # Documentation
└── scripts/              # Helper scripts
```

### Adding New Commands

1. Create YAML spec in `shared/commands/`:

```yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: circle
  version: 1.0.0
spec:
  description:
    brief: "Fly in circle pattern"
  parameters:
    radius:
      type: float
      default: 10.0
      constraints: {min: 5.0, max: 100.0}
  implementation:
    handler: "dronesphere.commands.circle.CircleCommand"
    timeout: 60
```

2. Implement command class:

```python
from dronesphere.commands.base import BaseCommand

class CircleCommand(BaseCommand):
    async def run(self, backend, **params):
        radius = params.get('radius', 10.0)
        # Implementation here
        return CommandResult(success=True)
```

### Code Quality

- **Formatting**: Black + Ruff
- **Type Checking**: mypy (strict mode)
- **Testing**: pytest with async support
- **Documentation**: MkDocs Material
- **Pre-commit**: Automated checks

## 🔮 Roadmap

### Phase 1 (Current) - MVP
- [x] Single drone support
- [x] Basic commands (takeoff, land, wait)
- [x] REST API
- [x] SITL integration
- [x] Real-time telemetry

### Phase 2 - Scale & Intelligence
- [ ] Multi-drone support
- [ ] LLM integration for natural language commands
- [ ] Mission planning AI
- [ ] Time-series telemetry database
- [ ] Real-time streaming dashboard

### Phase 3 - Production
- [ ] Authentication & RBAC
- [ ] Hardware drone support
- [ ] Fleet management
- [ ] Geofencing & safety systems
- [ ] Cloud deployment

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `pytest`
5. Run quality checks: `pre-commit run --all-files`
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open Pull Request

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## 🆘 Support

- 📖 [Documentation](https://yourusername.github.io/dronesphere)
- 🐛 [Issue Tracker](https://github.com/yourusername/dronesphere/issues)
- 💬 [Discussions](https://github.com/yourusername/dronesphere/discussions)

---

**Built with ❤️ for the future of autonomous systems**
"""

# =====================================================
# DIRECTORY STRUCTURE GUIDE:
# =====================================================
# 
# Please create the following directory structure and files:
#
# dronesphere/
# ├── pyproject.toml                    (content above)
# ├── LICENSE                           (content above)  
# ├── README.md                         (content above)
# ├── .gitignore                        (see next artifact)
# ├── .pre-commit-config.yaml          (see next artifact)
# ├── dronesphere/                      (Python package - see next artifacts)
# ├── shared/                           (YAML configs - see next artifacts)
# ├── tests/                            (Test suite - see next artifacts)
# ├── docker/                           (Docker configs - see next artifacts)
# ├── docs/                             (Documentation - see next artifacts)
# ├── scripts/                          (Helper scripts - see next artifacts)
# └── .github/workflows/                (CI/CD - see next artifacts)