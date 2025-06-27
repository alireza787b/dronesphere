# DroneSphere Master Plan & Architecture

## Project Overview

**Project Name**: DroneSphere
**Author**: Alireza Ghaderi (<p30planets@gmail.com>)
**Repository**: github.com/alireza787b/dronesphere
**Start Date**: 27 June 2025
**Goal**: AI-powered drone control system with natural language interface

## System Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     1. DRONE AGENT                          │
│  (Raspberry Pi / Companion Computer)                        │
│  - MAVSDK/PyMAVLink client                                 │
│  - WebSocket connection to server                          │
│  - Local command executor                                  │
│  - Telemetry streamer                                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ WebSocket/REST
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                     2. CONTROL SERVER                       │
│  (Cloud/Local Server)                                       │
│  - LLM Integration (Ollama/OpenAI/Anthropic)              │
│  - Command Processing Pipeline                              │
│  - Multi-drone Management                                   │
│  - API Gateway                                             │
│  - Optional: Netbird VPN                                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ REST/WebSocket
                              │
┌─────────────────────────────┴───────────────────────────────┐
│                     3. WEB FRONTEND                        │
│  (React Application)                                        │
│  - Natural Language Chat Interface                         │
│  - Drone Management Dashboard                               │
│  - Real-time Telemetry Display                            │
│  - Command History                                         │
└─────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
dronesphere/
├── docs/
│   ├── progress/                 # Progress reports
│   │   ├── 001-initial-setup.md
│   │   └── README.md            # Progress index
│   ├── architecture/            # Architecture decisions
│   ├── guides/                  # User guides
│   └── api/                     # API documentation
│
├── agent/                       # Drone-side agent
│   ├── pyproject.toml          # UV project file
│   ├── src/
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── main.py         # Entry point
│   │   │   ├── connection.py   # Server connection
│   │   │   ├── executor.py     # Command executor
│   │   │   └── telemetry.py    # Telemetry streamer
│   │   └── config/
│   │       └── settings.py
│   └── requirements.txt
│
├── server/                      # Control server
│   ├── pyproject.toml
│   ├── src/
│   │   ├── server/
│   │   │   ├── __init__.py
│   │   │   ├── main.py         # FastAPI app
│   │   │   ├── api/            # API routes
│   │   │   │   ├── chat.py
│   │   │   │   ├── drones.py
│   │   │   │   └── commands.py
│   │   │   ├── core/           # Core logic
│   │   │   │   ├── commands/   # Command system
│   │   │   │   ├── ai/         # AI pipeline
│   │   │   │   └── drones/     # Drone management
│   │   │   └── services/       # External services
│   │   │       ├── llm.py
│   │   │       └── storage.py
│   │   └── config/
│   └── requirements.txt
│
├── web/                         # Frontend application
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   ├── services/
│   │   └── hooks/
│   └── public/
│
├── shared/                      # Shared resources
│   ├── commands/               # Command definitions
│   │   ├── schema.json         # Command schema
│   │   ├── basic/              # Basic commands
│   │   │   ├── takeoff.yaml
│   │   │   ├── land.yaml
│   │   │   └── move.yaml
│   │   └── custom/             # User-defined commands
│   │
│   ├── prompts/                # AI prompts
│   │   ├── templates/          # Prompt templates
│   │   └── pipelines/          # Pipeline configs
│   │
│   └── configs/                # Configuration files
│       ├── drones.json         # Drone configurations
│       └── llm_providers.json  # LLM settings
│
├── scripts/                     # Utility scripts
│   ├── setup.sh                # Project setup
│   ├── demo.sh                 # Run demo
│   └── dev.sh                  # Development helpers
│
├── tests/                       # Test suite
│   ├── agent/
│   ├── server/
│   └── integration/
│
├── .github/                     # GitHub workflows
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
│
├── docker/                      # Docker configurations
│   ├── agent.Dockerfile
│   ├── server.Dockerfile
│   └── docker-compose.yml
│
├── pyproject.toml              # Root UV config
├── README.md                   # Project documentation
├── .gitignore
├── .pre-commit-config.yaml     # Pre-commit hooks
└── LICENSE
```

## Core Design Principles

### 1. Command Extensibility

**Command Definition Schema**:

```yaml
# shared/commands/basic/takeoff.yaml
apiVersion: v1
kind: DroneCommand
metadata:
  name: takeoff
  category: flight
  tags: ["basic", "vertical"]
  version: "1.0.0"

spec:
  description:
    brief: "Take off to specified altitude"
    detailed: "Arms the drone and takes off vertically to the specified altitude"
    examples:
      - text: "Take off to 20 meters"
        params: { altitude: 20 }
      - text: "برخیز به ارتفاع ۱۰ متر" # Persian
        params: { altitude: 10 }

  parameters:
    altitude:
      type: float
      required: true
      constraints:
        min: 1
        max: 120
        unit: meters

  implementation:
    handler: "basic_commands.TakeoffCommand"
    supported_backends: ["mavsdk", "pymavlink"]

  safety:
    pre_checks:
      - battery_min: 30
      - gps_fix: true
      - clear_above: true
```

### 2. AI Pipeline Architecture

```python
# Flexible pipeline system
pipeline:
  - stage: language_detection
    prompt: prompts/detect_language.yaml

  - stage: command_extraction
    prompt: prompts/extract_command.yaml
    llm_config:
      temperature: 0.1

  - stage: parameter_extraction
    prompt: prompts/extract_params.yaml

  - stage: safety_validation
    prompt: prompts/safety_check.yaml

  - stage: confirmation
    prompt: prompts/confirm_action.yaml
    condition: "high_risk_command"
```

### 3. Multi-Drone Configuration

```json
// shared/configs/drones.json
{
  "drones": [
    {
      "id": "drone_001",
      "name": "Alpha Drone",
      "type": "quadcopter",
      "connection": {
        "type": "network",
        "host": "192.168.1.100",
        "port": 5760
      },
      "capabilities": ["camera", "gps", "lidar"],
      "flight_params": {
        "max_altitude": 50,
        "max_speed": 15,
        "geofence": {
          "enabled": true,
          "radius": 500
        }
      }
    }
  ]
}
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Basic working demo with single drone

1. **Environment Setup**

   - Initialize repository structure
   - Set up UV for dependency management
   - Configure pre-commit hooks
   - Create Docker environments

2. **Basic Agent**

   - MAVSDK connection to Pixhawk
   - WebSocket client to server
   - Simple command executor
   - Telemetry streaming

3. **Minimal Server**

   - FastAPI setup
   - Basic command registry
   - Simple LLM integration (Ollama)
   - WebSocket handler

4. **Simple Frontend**
   - React setup with TypeScript
   - Basic chat interface
   - Telemetry display
   - Single drone connection

**Deliverables**:

- Working SITL demo
- Basic chat to control drone
- Progress report 001

### Phase 2: Command System (Week 3-4)

**Goal**: Extensible command framework

1. **Command Framework**

   - YAML-based command definitions
   - Dynamic command loading
   - Parameter validation
   - Multi-backend support prep

2. **Enhanced AI Pipeline**

   - Modular pipeline stages
   - Prompt template system
   - Multi-language support (English/Persian)
   - Safety checks

3. **Storage System**
   - JSON-based configuration
   - Command history
   - User preferences

**Deliverables**:

- 10+ basic commands
- Custom command support
- Progress report 002

### Phase 3: Production Features (Week 5-6)

**Goal**: Multi-drone, production-ready

1. **Multi-Drone Support**

   - Drone registry
   - Session management
   - Concurrent connections
   - Load balancing

2. **Advanced Features**

   - Command queuing
   - Batch operations
   - Emergency procedures
   - Offline mode

3. **Deployment**
   - Docker compose setup
   - CI/CD pipeline
   - Documentation
   - Testing suite

**Deliverables**:

- Multi-drone demo
- Docker deployment
- Progress report 003

## Technology Stack

### Backend

- **Language**: Python 3.11+
- **Package Manager**: UV
- **Framework**: FastAPI
- **Drone SDK**: MAVSDK (primary), PyMAVLink (future)
- **AI/LLM**: LangChain + Ollama/OpenAI/Anthropic
- **Database**: SQLite (dev), PostgreSQL (production)
- **Cache**: Redis (optional)
- **Testing**: Pytest + pytest-asyncio

### Frontend

- **Framework**: React 18+ with TypeScript
- **State**: Zustand or Redux Toolkit
- **UI**: Tailwind CSS + shadcn/ui
- **Charts**: Recharts
- **WebSocket**: socket.io-client

### DevOps

- **Containers**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (future)
- **VPN**: Netbird (optional)

## Development Workflow

1. **Branch Strategy**

   - `main`: Stable releases
   - `develop`: Integration branch
   - `feature/*`: New features
   - `fix/*`: Bug fixes

2. **Commit Convention**

   ```
   type(scope): description

   Types: feat, fix, docs, style, refactor, test, chore
   Example: feat(commands): add waypoint navigation command
   ```

3. **Testing Requirements**

   - Unit tests for all commands
   - Integration tests for API
   - E2E tests for critical paths
   - 80% coverage target

4. **Documentation**
   - Code comments for complex logic
   - API documentation (OpenAPI)
   - User guides
   - Progress reports

## Configuration Management

### Environment Variables

```bash
# .env.example
# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO

# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=your-key-here

# Drone Defaults
DEFAULT_DRONE_PORT=14540
SITL_HOST=localhost

# Security
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000
```

## Quick Start Commands

```bash
# Initial setup
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere
./scripts/setup.sh

# Run SITL + all services
./scripts/demo.sh

# Development mode
./scripts/dev.sh

# Run tests
uv run pytest

# Build Docker images
docker-compose build

# Deploy locally
docker-compose up
```

## Success Metrics

1. **Phase 1**: Basic chat control working in SITL
2. **Phase 2**: 10+ commands, multi-language support
3. **Phase 3**: Multi-drone control, production deployment

## Next Steps

1. Clean existing repository
2. Create folder structure
3. Initialize UV projects
4. Set up pre-commit hooks
5. Create first progress report
6. Implement basic agent

This plan provides:

- Clear three-tier architecture
- Extensible command system
- Flexible AI pipeline
- Simple starting point
- Clear growth path
- Complete documentation trail
