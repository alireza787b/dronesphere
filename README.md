# 🚁 DroneSphere v3.0 - AI-Enhanced Drone Fleet Management

## Professional Autonomous Drone Control with Model Context Protocol (MCP) Integration

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![MAVSDK](https://img.shields.io/badge/MAVSDK-2.0+-orange.svg)](https://mavsdk.mavlink.io/)
[![MCP](https://img.shields.io/badge/MCP-1.2+-purple.svg)](https://modelcontextprotocol.io/)

### 🌟 Revolutionary Features

- **🤖 Model Context Protocol (MCP)**: Production-ready standardized AI integration
- **🌐 n8n Workflow Automation**: AI agents for autonomous drone operations
- **💬 Natural Language Control**: Multi-language support (English, Persian, Spanish, French, German)
- **🧭 Smart Navigation NEW!**: Unified navigation tool with automatic coordinate transformation
  - Body frame: "fly forward 10m"
  - Offset navigation: "go 5m north from current position"
  - Reference frames: current, home, GPS absolute
  - 4 coordinate systems in ONE tool call
- **🎯 Dual Coordinate Systems**: GPS absolute positioning + NED relative navigation
- **🛡️ AI-Enhanced Safety**: LLM-driven validation with traditional safety checks
- **📊 Real-time Telemetry**: Live monitoring with intelligent caching
- **🔄 Command Sequences**: Complex multi-step operations via natural language

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [MCP Server Integration](#-mcp-server-integration-new)
- [Architecture](#-architecture-overview)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Development Workflow](#-development-workflow)
- [Testing](#-testing-infrastructure)
- [API Documentation](#-api-documentation)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start




```bash
# 1. Clone and setup
git clone https://github.com/alireza787b/dronesphere.git
cd dronesphere
make install-deps

# 2. Configure API keys
cd mcp-server
cp .env.example .env  # Edit with your keys

# 3. Start development environment
make dev              # Core services (SITL docker, Agent, Server)
```

### For MCP Developers
```bash
make mcp-inspector    # Debug UI at http://Your_SERVER_IP:5173
```

### For n8n Users (Production MCP)

```bash
# Start MCP server for n8n
make mcp-n8n

# 3. Configure n8n with URL: http://Your_SERVER_IP:8003/sse
# 4. Import workflow from mcp-server/examples/n8n-workflow.json
```

### Test Natural Language Commands

```bash
# In n8n chat or MCP inspector:
"Get drone status"
"Takeoff to 10 meters"
"Go north 5 meters then wait 3 seconds then land"
"Emergency stop"
```

### Legacy LLM-Only Web Demo (Deprecated)

```bash
make llm-bridge  # Web UI at http://YOUR_IP:3001
```
⚠️ **Not for production** - Basic demo only, relies purely on LLM without MCP structure. Only used for quick SITL demo. Use `make mcp-n8n` for real deployments. Will be removed in v4.0.


---

## 🤖 MCP Server Integration (NEW!)

### Overview

DroneSphere v3.0 includes a production-ready **Model Context Protocol (MCP)** server enabling standardized AI integration:

- **n8n Workflows**: Automated drone control with AI agents
- **Claude Desktop**: Direct integration with Anthropic's Claude
- **MCP Inspector**: Development and debugging UI
- **Custom Clients**: Any MCP-compatible application

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    n8n      │────▶│  MCP Server │────▶│ DroneSphere │
│  (Docker)   │ SSE │  Port 8003  │ API │   Server    │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                        LLM API
                           │
                    ┌─────────────┐
                    │  OpenRouter │
                    │   GPT/Claude │
                    └─────────────┘
```

### MCP Tools Available

| Tool | Description | Example |
|------|-------------|---------|
| `smart_navigate` 🆕 | Unified navigation (all coordinate types) | "fly forward 10m", "go 5m north" |
| `execute_drone_command` | Natural language drone control | "takeoff to 15m then hover" |
| `get_drone_status` | Get current telemetry | "what's the battery level?" |
| `emergency_stop` | Emergency land | "emergency stop" |
| `health_check` | System diagnostics | Check all connections |
| `transform_body_to_ned` | Body → NED coordinates | For custom transformations |
| `transform_ned_to_global` | NED → GPS coordinates | For custom transformations |
| `transform_global_to_ned` | GPS → NED coordinates | For custom transformations |

### n8n Integration

1. **Import Example Workflow**:
   ```bash
   # Located at: mcp-server/examples/n8n-workflow.json
   ```

2. **Configure MCP Client Tool**:
   - Server URL: `http://YOU_SERVER_IP:8003/sse`
   - Docker alternative (in n8n is installed locally on docker): `http://172.17.0.1:8003/sse`

3. **Workflow Components**:
   - Chat Trigger → AI Agent → MCP Client → Drone Control
   - Supports Ollama, OpenAI, or any LangChain LLM

### Claude Desktop Integration

```bash
# View setup instructions
make mcp-claude

# Configuration options:
# 1. Using mcp-remote proxy (easier)
# 2. Using SSH tunnel (more secure)
```

---

## 🧭 Smart Navigation System (NEW!)

### Overview

DroneSphere v3.0 introduces `smart_navigate` - a unified MCP tool that automatically handles ALL coordinate transformations. AI agents can control drones naturally without understanding coordinate mathematics.

### Coordinate Modes (Auto-Detected)

```python
# 1. Body Frame (relative to drone heading)
smart_navigate(forward=10, maintain_altitude=True)    # "fly forward 10m"
smart_navigate(right=5, maintain_altitude=True)       # "move right 5m"

# 2. Offset from Reference
smart_navigate(offset_north=10, reference="current")  # "go 10m north"
smart_navigate(offset_north=20, reference="home")     # "go 20m north from home"

# 3. Absolute GPS
smart_navigate(latitude=47.398, longitude=8.546, altitude_msl=500)

# 4. NED from Origin
smart_navigate(north=50, east=30, down=-15)
```

### Natural Language Examples

| User Says | System Interprets As |
|-----------|---------------------|
| "fly 10 meters forward" | `smart_navigate(forward=10, maintain_altitude=True)` |
| "go 5 meters north" | `smart_navigate(offset_north=5, reference="current")` |
| "move right 3 meters" | `smart_navigate(right=3, maintain_altitude=True)` |
| "return home" / "go home" | `execute_drone_command("rtl")` - Uses PX4 native RTL |

### Documentation

- **Complete Guide**: `mcp-server/NAVIGATION_GUIDE.md` - Comprehensive coordinate system documentation
- **Quick Start**: `QUICKSTART_NAVIGATION.md` - Fast testing guide
- **Command Reference**: `COMMAND_REFERENCE.md` - All commands with examples
- **Implementation**: `IMPLEMENTATION_SUMMARY.md` - Technical details

### Benefits for AI Agents

✅ **ONE tool** instead of chaining multiple calls
✅ **Automatic** coordinate transformation
✅ **Natural language friendly** - maps directly to user intent
✅ **Context-aware** - fetches telemetry automatically
✅ **Robust** - comprehensive validation and error handling

---

## 🏗️ Architecture Overview

### System Components

```
┌──────────────────────────────────────────────────────────┐
│                    DroneSphere v3.0                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Agent     │  │   Server    │  │  MCP Server │     │
│  │  Port 8001  │  │  Port 8002  │  │  Port 8003  │     │
│  └─────┬───────┘  └──────┬──────┘  └──────┬──────┘     │
│        │                  │                 │            │
│        └──────────────────┼─────────────────┘            │
│                           │                              │
│                    ┌──────▼──────┐                       │
│                    │  PX4 SITL   │                       │
│                    │  UDP 14540  │                       │
│                    └─────────────┘                       │
└──────────────────────────────────────────────────────────┘
```

### Project Structure

```
dronesphere/
├── README.md              # This documentation
├── JOURNEY.md            # Development history
├── Makefile             # Development commands
│
├── agent/               # Drone control service
│   ├── main.py         # FastAPI server (port 8001)
│   ├── executor.py     # Command execution
│   └── agent-env/      # Virtual environment
│
├── server/              # Fleet management
│   ├── main.py         # FastAPI server (port 8002)
│   ├── api.py          # Fleet endpoints
│   └── server-env/     # Virtual environment
│
├── mcp-server/          # MCP/AI Integration (NEW!)
│   ├── server.py       # FastMCP server
│   ├── core/           # LLM & API handlers
│   │   ├── llm_handler.py
│   │   └── drone_api.py
│   ├── prompts/        # Configurable prompts
│   │   └── config.yaml
│   ├── examples/       # n8n workflows
│   ├── .env           # API keys (create from template)
│   └── mcp-server-env/ # Virtual environment
│
├── llm-bridge/          # Legacy web demo (deprecated)
│   └── web_bridge_demo/
│
└── shared/              # Common components
    ├── models.py       # Data models
    └── drones.yaml     # Fleet configuration
```

---

## 📦 Installation

### Prerequisites

- Python 3.11+
- Docker (for SITL simulation)
- Node.js (optional, for Claude Desktop integration)
- n8n (optional, for workflow automation)

### Quick Install

```bash
# 1. Clone repository
git clone https://github.com/yourusername/dronesphere.git
cd dronesphere

# 2. Install dependencies
make install-deps

# 3. Setup MCP server
make mcp-setup
```

---

## ⚙️ Configuration

### MCP Server Configuration

Create `.env` file in `mcp-server/` directory:

```env
# LLM Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here  # Get from https://openrouter.ai/keys
LLM_MODEL=openai/gpt-4o-mini-2024-07-18         # Or your preferred model
LLM_MAX_TOKENS=10000

# DroneSphere Configuration
DRONESPHERE_SERVER_URL=http://localhost:8002     # Or http://YOUR_SERVER_IP:8002 for remote
SITL_MODE=true                                   # Set to false for real drones
DEBUG_MODE=false                                 # Set to true for verbose logging

# MCP Configuration
MCP_PORT=8003                                    # Port for SSE/HTTP transport
```

### Available LLM Models

#### OpenRouter (Recommended)
- `openai/gpt-4o-mini-2024-07-18` - Fast and efficient
- `anthropic/claude-3-sonnet` - High quality responses
- `google/gemini-pro` - Good for complex tasks

#### OpenAI Direct
- `gpt-4` - Most capable but slower
- `gpt-3.5-turbo` - Fast and cost-effective

### Safety Configuration

Edit `mcp-server/prompts/config.yaml`:

```yaml
safety:
  sitl_mode:
    - "SIMULATION MODE: Safety limits relaxed"
    - "Battery warnings disabled in simulation"

  production_mode:
    - "Maximum altitude: 120 meters"
    - "Minimum battery: 20%"
    - "No operations in bad weather"
    - "Return to launch if battery < 15%"

custom_rules:
  # Add your custom rules here
  - "Always maintain 5m distance from obstacles"
  - "No flights over people"
```

---

## 🛠️ Development Workflow

### Essential Commands

```bash
# Development
make dev                # Start SITL + Agent + Server
make mcp-n8n           # Start MCP for n8n
make mcp-inspector     # Debug UI
make status            # Check all services

# Testing
make test-all          # Run complete test suite
make test-n8n          # Test n8n connectivity
make mcp-test-stdio    # Test STDIO mode
make mcp-test-sse      # Test SSE endpoint

# Cleanup
make clean             # Stop all services
make clean-all         # Clean + remove containers
```

### Development Modes

| Mode | Command | Description | URL |
|------|---------|-------------|-----|
| Core | `make dev` | Basic services | - |
| MCP Inspector | `make mcp-inspector` | Debug UI | http://localhost:5173 |
| n8n | `make mcp-n8n` | SSE server | http://localhost:8003/sse |
| Legacy Demo | `make dev-llm-bridge` | Web interface | http://localhost:3001 |

---

## 🧪 Testing Infrastructure

### Quick Test

```bash
# Test everything
make test-all

# Test specific components
make test-agent        # Agent endpoints
make test-server       # Server functionality
make test-commands     # Drone commands
make test-n8n         # n8n connectivity
```

### Natural Language Tests

```python
# Test in n8n or inspector:
"takeoff to 10 meters"                    # Simple command
"بلند شو به ۱۵ متر"                        # Persian
"go north 5m then wait 3s then land"      # Sequence
"what's the current battery level?"       # Status query
```

---

## 📚 API Documentation

### MCP Server Endpoints

| Transport | Endpoint | Purpose |
|-----------|----------|---------|
| SSE | `http://localhost:8003/sse` | n8n integration |
| STDIO | `python server.py stdio` | Claude Desktop |
| HTTP | `http://localhost:8003/mcp` | Custom clients |

### Core API Endpoints

| Service | Endpoint | Description |
|---------|----------|-------------|
| Agent | `GET /health` | Health check |
| Agent | `POST /command` | Execute drone command |
| Agent | `GET /telemetry` | Get telemetry data |
| Server | `GET /fleet/status` | Fleet status |
| Server | `POST /fleet/commands` | Send fleet commands |

---

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Port already in use | `make clean-all` then restart |
| MCP not connecting | Check `.env` API keys |
| n8n can't find server | Use Docker IP: `172.17.0.1:8003/sse` |
| Commands timeout | Check SITL is running: `make status` |

### Debug Mode

```bash
# Enable debug logging
cd mcp-server
DEBUG_MODE=true make mcp-n8n

# Check logs
tail -f /tmp/agent.log
tail -f /tmp/server.log
```

---

## 🚀 Roadmap

### Current Phase (v3.0) ✅
- [x] MCP server implementation
- [x] n8n integration
- [x] Multi-transport support
- [x] Production configuration

### Next Phase (v3.1)
- [ ] Custom command YAML definitions
- [ ] RAG for drone expertise
- [ ] Knowledge graph integration
- [ ] Advanced safety rules
- [ ] HTTPS/Caddy deployment

### Future (v4.0)
- [ ] Multi-drone coordination
- [ ] Visual recognition
- [ ] Autonomous mission planning
- [ ] Real hardware integration

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 👥 Team

- **Architecture**: Agent-Server separation with MCP integration
- **AI/LLM**: FastMCP with OpenRouter/OpenAI
- **Safety**: Multi-layer validation system
- **Testing**: Comprehensive test coverage

---

*DroneSphere v3.0 - Professional AI-Enhanced Drone Fleet Management*
*MCP Integration: Production Ready | n8n: Working | Claude: Documented*
*Last Updated: 2025-08-11*
```
