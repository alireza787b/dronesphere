# DroneSphere Agent

The drone-side agent that runs on the companion computer (e.g., Raspberry Pi) and manages communication between the flight controller and the control server.

## Features

- MAVSDK integration for PX4/ArduPilot control
- WebSocket connection to control server
- Real-time telemetry streaming
- Command execution with safety checks
- Automatic reconnection logic
- Structured logging

## Installation

```bash
cd agent
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration:

   ```bash
   cp config/agent.yaml.example config/agent.yaml
   ```

2. Edit `config/agent.yaml` with your settings

3. Or use environment variables:

   ```bash
   export AGENT_DRONE_ID=drone_001
   export AGENT_SERVER_URL=ws://localhost:8000/ws/agent
   ```

## Usage

### Basic Usage

```bash
python -m agent.main
```

### Development Mode

```bash
python -m agent.main --dev
```

### Custom Config File

```bash
python -m agent.main --config /path/to/config.yaml
```

## Testing Connection

Test the connection to SITL:

```bash
python ../scripts/test_connection.py
```

## Architecture

- `connection.py` - Handles MAVSDK drone connection
- `executor.py` - Executes commands from server
- `telemetry.py` - Streams telemetry to server
- `main.py` - Main entry point and orchestration

## Safety Features

- Maximum altitude limits
- Geofencing support
- Battery monitoring
- GPS fix requirements
- Command timeout handling
