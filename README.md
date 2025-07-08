# 🚁 DroneSphere - Distributed Drone Control System

## Architecture

DroneSphere consists of two main components:

### Agent (On-Drone)
- **Port**: 8001
- **Purpose**: Direct hardware control and command execution
- **Location**: Drone companion computer (Raspberry Pi, etc.)
- **Capabilities**: Single drone operations, real-time telemetry, command execution

### Server (Cloud Coordination)  
- **Port**: 8002
- **Purpose**: Multi-drone coordination and fleet management
- **Location**: Cloud infrastructure or ground control station
- **Capabilities**: Fleet coordination, telemetry caching, command routing

## Quick Start

### Start Agent (On Drone)
```bash
# For development (SITL)
python -m dronesphere.agent

# For production
AGENT_HOST=0.0.0.0 AGENT_PORT=8001 python -m dronesphere.agent
```

### Start Server (Cloud/GCS)
```bash
# Start coordination server
python -m dronesphere.server

# Or with custom configuration
SERVER_HOST=0.0.0.0 SERVER_PORT=8002 python -m dronesphere.server
```

## API Reference

### Agent API (8001)
- `GET /ping` - Connection check
- `GET /health` - Agent health status
- `GET /status` - Current flight status
- `GET /telemetry` - Real-time telemetry
- `POST /commands` - Execute command sequence
- `POST /emergency_stop` - Emergency stop

### Server API (8002)
- `GET /ping` - Server connection check
- `GET /health` - Fleet health overview
- `GET /drones` - List all drones
- `GET /drones/{id}/status` - Specific drone status
- `GET /telemetry` - Cached telemetry (all drones)
- `POST /drones/{id}/commands` - Command specific drone
- `POST /commands/broadcast` - Command multiple drones

## Configuration

See `.env` for detailed configuration options.

### Drone Configuration (shared/drones.yaml)
```yaml
drones:
  - id: 1
    name: "Primary Drone"
    agent:
      host: "192.168.1.100"
      port: 8001
    hardware:
      protocol: "udp"
      address: "127.0.0.1"
      port: 14540
```

## Development

### Testing Command Flow
```bash
# Test via server (recommended)
curl -X POST http://localhost:8002/drones/1/commands \
  -H "Content-Type: application/json" \
  -d '{"sequence":[{"name":"takeoff","params":{"altitude":3}}]}'

# Test direct to agent
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"sequence":[{"name":"land","params":{}}]}'
```

### Architecture Benefits
- ✅ **Scalable**: Add drones by deploying more agents
- ✅ **Resilient**: Agent continues operating if server disconnects  
- ✅ **Efficient**: Telemetry caching reduces network load
- ✅ **Flexible**: Direct agent access for peer-to-peer operations
- ✅ **Production-Ready**: Clean separation of concerns