# docs/api.md
# ===================================

# API Reference

DroneSphere provides a RESTful API for drone command and control. All endpoints use JSON for request/response payloads.

## Base URL

```
http://localhost:8000
```

## Authentication

**Phase 1:** No authentication required (development/trusted network)
**Future:** JWT-based authentication with API keys

## Error Handling

All endpoints return consistent error responses:

```json
{
  "success": false,
  "message": "Error description",
  "errors": ["Detailed error 1", "Detailed error 2"]
}
```

### HTTP Status Codes

- `200` - Success
- `202` - Accepted (async operations)
- `400` - Bad Request (validation error)
- `404` - Not Found (drone/command not found)
- `409` - Conflict (invalid state)
- `500` - Internal Server Error
- `503` - Service Unavailable

## Endpoints

### Health & Status

#### GET /health

System health check.

**Response:**
```json
{
  "success": true,
  "message": "Healthy",
  "data": {
    "total_drones": 1,
    "connected_drones": [1],
    "timestamp": 1705312200.0
  }
}
```

#### GET /ready

Service readiness check.

**Response:**
```json
{
  "success": true,
  "message": "Ready",
  "data": {
    "drone_1_connected": true
  }
}
```

#### GET /metrics

Prometheus metrics endpoint.

**Response:** Prometheus text format

### Command Execution

#### POST /command/{drone_id}

Execute command sequence on specified drone.

**Parameters:**
- `drone_id` (path): Drone identifier

**Request Body:**
```json
{
  "sequence": [
    {
      "name": "takeoff",
      "params": {
        "altitude": 10.0
      }
    },
    {
      "name": "wait",
      "params": {
        "seconds": 3.0
      }
    },
    {
      "name": "land"
    }
  ],
  "metadata": {
    "mission_name": "Test Flight",
    "operator": "pilot@example.com"
  }
}
```

**Response (202):**
```json
{
  "success": true,
  "message": "Command sequence accepted",
  "command_id": "cmd_abc123",
  "estimated_duration": 60
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/command/1 \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 5}},
      {"name": "wait", "params": {"seconds": 2}},
      {"name": "land"}
    ]
  }'
```

### Status & Monitoring

#### GET /status/{drone_id}

Get current drone status and execution state.

**Parameters:**
- `drone_id` (path): Drone identifier

**Response:**
```json
{
  "drone_id": 1,
  "state": "flying",
  "current_command": {
    "id": "cmd_abc123-1",
    "command": {
      "name": "wait",
      "params": {"seconds": 3.0}
    },
    "status": "executing",
    "progress": 0.6,
    "started_at": "2025-01-15T10:30:00Z"
  },
  "queue_length": 1,
  "last_telemetry": "2025-01-15T10:30:05Z",
  "health_status": "ok"
}
```

**States:**
- `disconnected` - Drone not connected
- `connected` - Connected but disarmed
- `disarmed` - Connected and disarmed
- `armed` - Armed but not flying
- `takeoff` - Taking off
- `flying` - In flight
- `landing` - Landing
- `emergency` - Emergency state

**Command Status:**
- `pending` - Waiting in queue
- `executing` - Currently running
- `completed` - Successfully finished
- `failed` - Failed with error
- `cancelled` - Cancelled by user/system

#### GET /telemetry/{drone_id}

Get real-time telemetry data.

**Parameters:**
- `drone_id` (path): Drone identifier

**Response:**
```json
{
  "timestamp": "2025-01-15T10:30:05Z",
  "drone_id": 1,
  "state": "flying",
  "flight_mode": "auto_loiter",
  "armed": true,
  "position": {
    "latitude": 47.6062,
    "longitude": -122.3321,
    "altitude_msl": 56.0,
    "altitude_relative": 10.0,
    "north": 0.0,
    "east": 0.0,
    "down": -10.0
  },
  "attitude": {
    "roll": 0.1,
    "pitch": -0.05,
    "yaw": 1.57,
    "roll_rate": 0.0,
    "pitch_rate": 0.0,
    "yaw_rate": 0.0
  },
  "velocity": {
    "ground_speed": 0.2,
    "air_speed": 0.2,
    "north": 0.1,
    "east": 0.1,
    "down": 0.0
  },
  "battery": {
    "voltage": 12.6,
    "current": 5.2,
    "remaining_percent": 85.0,
    "remaining_time": 1200
  },
  "gps": {
    "fix_type": 3,
    "satellites_visible": 12,
    "hdop": 0.8,
    "vdop": 1.2
  },
  "health_all_ok": true,
  "calibration_ok": true,
  "connection_ok": true
}
```

#### GET /queue/{drone_id}

Get command queue status.

**Parameters:**
- `drone_id` (path): Drone identifier

**Response:**
```json
{
  "success": true,
  "message": "Queue status retrieved",
  "data": {
    "queue_length": 2,
    "current_execution": {
      "id": "cmd_abc123-0",
      "command": {"name": "takeoff", "params": {"altitude": 10}},
      "status": "executing",
      "progress": 0.8
    }
  }
}
```

#### GET /command/{command_id}/status

Get specific command execution status.

**Parameters:**
- `command_id` (path): Command execution identifier

**Response:**
```json
{
  "success": true,
  "message": "Command status retrieved",
  "data": {
    "id": "cmd_abc123-0",
    "command": {
      "name": "takeoff",
      "params": {"altitude": 10.0}
    },
    "status": "completed",
    "progress": 1.0,
    "started_at": "2025-01-15T10:30:00Z",
    "completed_at": "2025-01-15T10:30:15Z",
    "result": {
      "success": true,
      "message": "Takeoff to 10.0m completed successfully",
      "duration": 15.2,
      "data": {
        "target_altitude": 10.0,
        "actual_duration": 15.2
      }
    }
  }
}
```

### Emergency Operations

#### POST /emergency_stop/{drone_id}

Execute emergency stop for specified drone.

**Parameters:**
- `drone_id` (path): Drone identifier

**Response:**
```json
{
  "success": true,
  "message": "Emergency stop executed"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/emergency_stop/1
```

### System Information

#### GET /drones

List all configured drones.

**Response:**
```json
{
  "success": true,
  "message": "Drones listed",
  "data": {
    "drones": [
      {
        "id": 1,
        "connected": true,
        "state": "disarmed"
      }
    ]
  }
}
```

## Available Commands

### takeoff

Take off to specified altitude.

**Parameters:**
- `altitude` (float): Target altitude in meters (1.0 - 50.0)

**Example:**
```json
{
  "name": "takeoff",
  "params": {
    "altitude": 10.0
  }
}
```

### land

Land at current position.

**Parameters:** None

**Example:**
```json
{
  "name": "land"
}
```

### wait

Wait for specified duration.

**Parameters:**
- `seconds` (float): Duration in seconds (0.1 - 300.0)

**Example:**
```json
{
  "name": "wait",
  "params": {
    "seconds": 5.0
  }
}
```

## WebSocket API (Future)

Real-time telemetry and status updates via WebSocket.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/telemetry/1');

ws.onmessage = function(event) {
  const telemetry = JSON.parse(event.data);
  console.log('Telemetry:', telemetry);
};
```

## Client Libraries

### Python Client

```python
from dronesphere.server.client import DroneSphereClient

client = DroneSphereClient("http://localhost:8000")

# Execute mission
response = await client.takeoff_wait_land(
    drone_id=1,
    altitude=10.0,
    wait_time=3.0
)

# Monitor status
status = await client.get_drone_status(1)
telemetry = await client.get_telemetry(1)
```

### JavaScript/TypeScript (Future)

```typescript
import { DroneSphereClient } from '@dronesphere/client';

const client = new DroneSphereClient('http://localhost:8000');

// Execute command
const response = await client.executeCommand(1, [
  { name: 'takeoff', params: { altitude: 10 } },
  { name: 'wait', params: { seconds: 3 } },
  { name: 'land' }
]);

// Stream telemetry
client.streamTelemetry(1, (telemetry) => {
  console.log('Position:', telemetry.position);
});
```

## Rate Limiting

**Current Limits:**
- 100 requests per minute per IP
- 10 commands per minute per drone
- 1000 telemetry requests per minute

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312260
```

## OpenAPI Specification

Interactive API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

# ===================================

