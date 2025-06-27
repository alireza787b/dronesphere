# DroneSphere 🚁

AI-powered natural language drone control system with multi-tier architecture.

## Overview

DroneSphere enables natural language control of drones through an extensible command system, flexible AI pipeline, and real-time communication infrastructure.

### Key Features

- 🗣️ Natural language drone control in multiple languages (English, Persian)
- 🚁 Multi-drone support with individual session management
- 🔌 Extensible command system with YAML definitions
- 🤖 Flexible AI pipeline with customizable prompts
- 🌐 Three-tier architecture (Agent, Server, Frontend)
- 📡 Real-time telemetry streaming
- 🛡️ Built-in safety checks and validations

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Drone Agent   │────▶│  Control Server │◀────│   Web Frontend  │
│  (Raspberry Pi) │     │  (Cloud/Local)  │     │     (React)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     MAVSDK/MAVLink          LLM + API              Chat Interface
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for SITL)
- UV (Python package manager)

### Installation

```bash
# Clone repository
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere

# Run setup script
./scripts/setup.sh

# Start SITL simulator
docker run --rm -it -p 14540:14540/udp jonasvautherin/px4-gazebo-headless:latest

# Run demo (in another terminal)
./scripts/demo.sh
```

### Development

```bash
# Start development environment
./scripts/dev.sh

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check --fix .
```

## Project Structure

```
dronesphere/
├── agent/          # Drone-side agent (Python)
├── server/         # Control server (FastAPI)
├── web/            # Frontend (React + TypeScript)
├── shared/         # Shared resources
│   ├── commands/   # Command definitions
│   ├── prompts/    # AI prompt templates
│   └── configs/    # Configuration files
├── docs/           # Documentation
├── scripts/        # Utility scripts
└── tests/          # Test suites
```

## Command System

Commands are defined in YAML for easy extension:

```yaml
# shared/commands/basic/takeoff.yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: takeoff
  category: flight
spec:
  description:
    brief: "Take off to altitude"
  parameters:
    altitude:
      type: float
      min: 1
      max: 50
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Author

**Alireza Ghaderi**
Email: <p30planets@gmail.com>
GitHub: [@alireza787b](https://github.com/alireza787b)

## Progress Tracking

See [docs/progress](docs/progress) for detailed development progress reports.
