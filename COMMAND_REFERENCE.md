# 🎮 DroneSphere Command Reference

## Complete Command Specifications for All Interfaces

**Version:** 3.0
**Updated:** September 30, 2025
**For:** API Users, AI Agents, MCP Tools, Developers

---

## 📋 **TABLE OF CONTENTS**

1. [Command Overview](#command-overview)
2. [Takeoff Command](#1-takeoff)
3. [Land Command](#2-land)
4. [RTL Command](#3-rtl-return-to-launch)
5. [Wait Command](#4-wait)
6. [Goto Command](#5-goto-navigation)
7. [Emergency Stop](#6-emergency-stop)
8. [Command Sequences](#command-sequences)
9. [Safety Rules](#safety-rules)
10. [Error Handling](#error-handling)

---

## 🎯 **COMMAND OVERVIEW**

### Available Commands

| Command | Purpose | Complexity | Safety Level |
|---------|---------|------------|--------------|
| `takeoff` | Ascend to specified altitude | Simple | CRITICAL |
| `land` | Controlled descent and landing | Simple | CRITICAL |
| `rtl` | Return to launch point | Simple | SAFE |
| `wait` | Hover for specified duration | Simple | SAFE |
| `goto` | Navigate to position | Complex | MODERATE |
| `emergency_stop` | Immediate safety landing | Simple | EMERGENCY |

### Command Execution Modes

- **CRITICAL**: Failure triggers emergency RTL
- **CONTINUE**: Failure continues to next command (default)
- **ABORT_ON_FAIL**: Failure aborts sequence

---

## 1. **TAKEOFF**

### Purpose
Arm drone and ascend to specified altitude above ground level.

### Parameters

```json
{
  "name": "takeoff",
  "params": {
    "altitude": 10
  }
}
```

| Parameter | Type | Required | Range | Default | Description |
|-----------|------|----------|-------|---------|-------------|
| `altitude` | float | Yes | 1-120m | - | Target altitude above ground |

### Behavior
1. Arms the drone
2. Activates TAKEOFF mode
3. Ascends to target altitude
4. Switches to HOLD mode
5. Returns success when altitude reached

### Timing
- **Duration:** ~8-10 seconds for 10m altitude
- **Monitoring:** Real-time altitude checking

### Safety Checks
- ✅ Drone must be connected
- ✅ Drone must be on ground (not already armed)
- ✅ Altitude within safe limits (1-120m)
- ✅ GPS fix required

### Examples

**Simple Takeoff:**
```json
{"name": "takeoff", "params": {"altitude": 10}}
```

**High Altitude:**
```json
{"name": "takeoff", "params": {"altitude": 50}}
```

### Error Messages
- `"Backend not connected to drone"` - No MAVSDK connection
- `"Drone must be disarmed before takeoff"` - Already armed
- `"altitude must be between 1 and 120 meters"` - Invalid altitude

### API Usage

**Direct Agent:**
```bash
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"takeoff","params":{"altitude":15}}],"target_drone":1}'
```

**Via Server:**
```bash
curl -X POST http://localhost:8002/fleet/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"takeoff","params":{"altitude":15}}],"target_drone":1}'
```

**MCP Tool (execute_drone_command):**
```
"takeoff to 15 meters"
"take off to 20m"
"بلند شو به ۱۵ متر" (Persian)
```

---

## 2. **LAND**

### Purpose
Controlled descent and landing at current position.

### Parameters

```json
{
  "name": "land",
  "params": {}
}
```

No parameters required.

### Behavior
1. Activates LAND mode
2. Descends at controlled rate (~1 m/s)
3. Detects ground contact
4. Disarms automatically
5. Returns success when disarmed

### Timing
- **Duration:** ~10-15 seconds from 10m altitude
- **Monitoring:** Real-time altitude and armed status

### Safety Checks
- ✅ Drone must be connected
- ✅ Drone should be armed (will succeed even if not)
- ✅ Drone should be airborne (can land from ground)

### Examples

**Simple Land:**
```json
{"name": "land", "params": {}}
```

### Error Messages
- `"Backend not connected to drone"` - No MAVSDK connection

### API Usage

**Direct Agent:**
```bash
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"land","params":{}}],"target_drone":1}'
```

**MCP Tool:**
```
"land"
"land the drone"
"فرود بیا" (Persian)
```

---

## 3. **RTL (Return to Launch)**

### Purpose
Navigate back to takeoff point and land automatically.

### Parameters

```json
{
  "name": "rtl",
  "params": {}
}
```

No parameters required.

### Behavior
1. Activates RTL mode
2. Climbs to RTL altitude (if needed)
3. Navigates to home position
4. Descends and lands
5. Disarms automatically

### Timing
- **Duration:** Varies based on distance from home
- **Monitoring:** Real-time flight mode

### Safety Checks
- ✅ Drone must be connected
- ✅ Home position must be set (automatic on first GPS fix)
- ✅ GPS must be available

### Examples

**Return to Launch:**
```json
{"name": "rtl", "params": {}}
```

### Error Messages
- `"Backend not connected to drone"` - No MAVSDK connection
- `"RTL failed to activate"` - Mode change unsuccessful

### API Usage

**Direct Agent:**
```bash
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"rtl","params":{}}],"target_drone":1}'
```

**MCP Tool:**
```
"return to launch"
"go home"
"rtl"
```

---

## 4. **WAIT**

### Purpose
Hover at current position for specified duration.

### Parameters

```json
{
  "name": "wait",
  "params": {
    "duration": 5,
    "message": "Waiting for 5 seconds"
  }
}
```

| Parameter | Type | Required | Range | Default | Description |
|-----------|------|----------|-------|---------|-------------|
| `duration` | float | Yes | 0.1-300s | - | Wait time in seconds |
| `message` | string | No | - | "" | Optional status message |

### Behavior
1. Maintains current position (HOLD mode)
2. Waits for specified duration
3. Returns success when complete

### Timing
- **Duration:** Exactly as specified
- **Accuracy:** ±0.5 seconds

### Safety Checks
- ✅ Duration within reasonable limits (0.1-300s)

### Examples

**Simple Wait:**
```json
{"name": "wait", "params": {"duration": 5}}
```

**Wait with Message:**
```json
{"name": "wait", "params": {"duration": 10, "message": "Stabilizing before next maneuver"}}
```

### Error Messages
- `"duration must be between 0.1 and 300 seconds"` - Invalid duration

### API Usage

**Direct Agent:**
```bash
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"wait","params":{"duration":3}}],"target_drone":1}'
```

**MCP Tool:**
```
"wait 5 seconds"
"hover for 10 seconds"
"stay here for 3 seconds"
```

---

## 5. **GOTO (Navigation)**

### Purpose
Navigate to specified position using various coordinate systems.

### Coordinate Modes

The goto command supports **4 coordinate systems**:

#### A. Absolute GPS Coordinates

```json
{
  "name": "goto",
  "params": {
    "latitude": 47.398,
    "longitude": 8.546,
    "altitude": 503.0,
    "speed": 5.0
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `latitude` | float | Yes | Decimal degrees (-90 to 90) |
| `longitude` | float | Yes | Decimal degrees (-180 to 180) |
| `altitude` | float | Yes | MSL altitude in meters |
| `speed` | float | No | Flight speed (default: 5.0, max: 20.0) |

**Use For:** Specific GPS waypoints, absolute positioning

#### B. NED from Origin

```json
{
  "name": "goto",
  "params": {
    "north": 50,
    "east": 30,
    "down": -15
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `north` | float | Yes | Meters north from PX4 origin |
| `east` | float | Yes | Meters east from PX4 origin |
| `down` | float | Yes | Meters down (negative = up) |

**Use For:** Relative positioning from home/origin

#### C. Body Frame (NEW!)

```json
{
  "name": "goto",
  "params": {
    "forward": 10,
    "right": 5,
    "up_body": 3,
    "maintain_altitude": true
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `forward` | float | No | Meters forward (negative = backward) |
| `right` | float | No | Meters right (negative = left) |
| `up_body` | float | No | Meters up (positive = up) |
| `maintain_altitude` | bool | No | Keep current altitude (default: false) |

**Use For:** "Fly forward 10m", relative to drone heading

**Note:** Handled by MCP smart_navigate tool, converts to GPS before sending to agent

#### D. Offset from Reference (NEW!)

```json
{
  "name": "goto",
  "params": {
    "offset_north": 10,
    "offset_east": 5,
    "offset_up": 3,
    "reference": "current",
    "maintain_altitude": true
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `offset_north` | float | No | Meters north from reference |
| `offset_east` | float | No | Meters east from reference |
| `offset_up` | float | No | Meters up (positive = up!) |
| `reference` | string | No | "current", "home", or "origin" |
| `maintain_altitude` | bool | No | Keep current altitude |

**Use For:** "Go 5m north", "Go 20m north from home"

**Note:** Handled by MCP smart_navigate tool, converts to GPS before sending to agent

### Behavior
1. Validates drone is armed and airborne
2. Sends goto_location command to PX4
3. Monitors progress (3D distance calculation)
4. Returns success when within acceptance radius

### Timing
- **Duration:** Varies by distance and speed
- **Typical:** 9-11 seconds for 50m at 5 m/s
- **Timeout:** 60 seconds

### Safety Checks
- ✅ Drone must be armed
- ✅ Drone must be airborne (altitude > 0.5m)
- ✅ Coordinates within valid ranges
- ✅ PX4 origin available (for NED conversion)

### Examples

**GPS Navigation:**
```json
{"name": "goto", "params": {"latitude": 47.398, "longitude": 8.546, "altitude": 503.0}}
```

**NED Navigation:**
```json
{"name": "goto", "params": {"north": 50, "east": 30, "down": -15}}
```

**Fast Navigation:**
```json
{"name": "goto", "params": {"latitude": 47.398, "longitude": 8.546, "altitude": 503.0, "speed": 10.0}}
```

### Error Messages
- `"goto command requires drone to be armed"` - Not armed
- `"goto command requires drone to be airborne"` - On ground
- `"latitude must be a number between -90 and 90 degrees"` - Invalid GPS
- `"NED coordinates require pymap3d library"` - Missing dependency

### API Usage

**MCP smart_navigate Tool (RECOMMENDED):**
```python
# Body frame
smart_navigate(forward=10, maintain_altitude=True)

# Offset from current
smart_navigate(offset_north=5, reference="current", maintain_altitude=True)

# Offset from home
smart_navigate(offset_north=20, reference="home")

# GPS
smart_navigate(latitude=47.398, longitude=8.546, altitude_msl=500)
```

**Direct API:**
```bash
curl -X POST http://localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{"commands":[{"name":"goto","params":{"latitude":47.398,"longitude":8.546,"altitude":503}}],"target_drone":1}'
```

---

## 6. **EMERGENCY_STOP**

### Purpose
Immediate safety landing (emergency use only).

### Parameters

**MCP Tool Only:**
```python
emergency_stop(drone_id=1)
```

### Behavior
1. Immediately activates LAND mode
2. Aborts current command sequence
3. Triggers safety protocols

### Safety
- Use only in emergencies
- Cannot be aborted once triggered
- Will land at current position

### API Usage

**MCP Tool:**
```
"emergency stop"
"stop immediately"
"emergency land"
```

---

## 🔗 **COMMAND SEQUENCES**

### Sequence Execution

Commands can be chained into sequences:

```json
{
  "commands": [
    {"name": "takeoff", "params": {"altitude": 15}},
    {"name": "goto", "params": {"north": 50, "east": 30, "down": -15}},
    {"name": "wait", "params": {"duration": 5}},
    {"name": "goto", "params": {"north": 0, "east": 0, "down": -15}},
    {"name": "land", "params": {}}
  ],
  "queue_mode": "override",
  "target_drone": 1
}
```

### Queue Modes
- **`override`**: Replace current queue (default)
- **`append`**: Add to existing queue

### Command Modes
- **`continue`**: Continue on failure (default)
- **`critical`**: Trigger RTL on failure
- **`abort_on_fail`**: Stop sequence on failure

---

## 🛡️ **SAFETY RULES**

### Global Safety
1. **Maximum Altitude:** 120m (configurable)
2. **Minimum Battery:** Commands rejected below threshold
3. **GPS Required:** For all navigation commands
4. **Geofencing:** Configurable boundaries
5. **Emergency RTL:** Auto-trigger on critical failures

### SITL vs Production

**SITL Mode (Development):**
- Relaxed altitude limits (up to 500m for testing)
- Battery warnings disabled
- Simplified validation

**Production Mode:**
- Strict 120m altitude limit
- 20% minimum battery for operations
- 15% battery triggers auto-RTL
- Weather checks enabled
- No-fly zone enforcement

### Configuration

Edit `mcp-server/prompts/config.yaml`:

```yaml
safety:
  production_mode:
    - "Maximum altitude: 120 meters"
    - "Minimum battery: 20%"
    - "Return to launch if battery < 15%"
```

---

## ⚠️ **ERROR HANDLING**

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Backend not connected | MAVSDK disconnected | Check SITL/drone connection |
| Drone must be armed | Not armed for flight command | Takeoff first |
| Requires airborne | On ground for goto | Takeoff first |
| GPS origin not available | No GPS fix | Wait for GPS lock |
| Coordinate out of range | Invalid parameters | Check coordinate values |
| Command timeout | Took too long | Check drone response, reduce distance |

### Error Response Format

```json
{
  "success": false,
  "message": "Detailed error description",
  "error": "error_code",
  "duration": 2.5
}
```

---

## 📊 **PERFORMANCE METRICS**

| Command | Typical Duration | Factors |
|---------|------------------|---------|
| takeoff (10m) | 8-10s | Altitude, acceleration |
| land (10m) | 10-15s | Altitude, descent rate |
| rtl | Variable | Distance from home |
| wait | Exact | As specified |
| goto (50m) | 9-11s | Distance, speed, wind |

### Timing Accuracy
- **takeoff:** ±1s
- **land:** ±2s
- **wait:** ±0.5s
- **goto:** ±2s (distance dependent)

---

## 🔧 **ADVANCED USAGE**

### Custom Command Speeds

```json
{"name": "goto", "params": {"north": 100, "east": 0, "down": -20, "speed": 15.0}}
```

### Precision Landing

```json
{"name": "goto", "params": {"latitude": 47.398, "longitude": 8.546, "altitude": 503, "acceptance_radius": 1.0}}
```

### Multi-Language Support

All commands support natural language in:
- English
- Persian (فارسی)
- Spanish
- French
- German

---

## 📚 **SEE ALSO**

- **Navigation Guide:** `NAVIGATION_GUIDE.md` - Detailed coordinate systems
- **Quick Start:** `QUICKSTART_NAVIGATION.md` - Fast testing guide
- **Implementation:** `IMPLEMENTATION_SUMMARY.md` - Technical details
- **API Documentation:** README.md - Full system overview

---

**Last Updated:** September 30, 2025
**Version:** 3.0 with Smart Navigation
**Status:** Production Ready
