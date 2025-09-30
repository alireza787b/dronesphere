# 🧭 Coordinate Transformation Flow - Complete System

## Verification: All Paths Lead to `lat, lon, alt, yaw` for MAVSDK

---

## 🎯 **CRITICAL DESIGN PRINCIPLE**

**NO MATTER WHAT COORDINATE SYSTEM THE USER PROVIDES, THE AGENT ALWAYS SENDS:**
```python
await drone.action.goto_location(
    latitude_deg,    # float: decimal degrees
    longitude_deg,   # float: decimal degrees
    altitude_msl,    # float: meters MSL
    yaw_deg          # float: degrees (or NaN to maintain current)
)
```

---

## 📊 **TRANSFORMATION FLOW DIAGRAM**

```
User Input (Natural Language)
         ↓
    LLM Parser (mcp-server/core/llm_handler.py)
         ↓
   ┌─────────────────────────────────┐
   │  Detects Intent & Creates JSON  │
   └─────────────────────────────────┘
         ↓
   ┌─────────────────────────────────────────────────────────┐
   │                   FORK BY INTERFACE                      │
   ├─────────────────────────────────────────────────────────┤
   │                                                           │
   │  PATH A: Via MCP smart_navigate         PATH B: Direct  │
   │  (for body/offset coordinates)          (for GPS/NED)   │
   │           ↓                                     ↓         │
   │  smart_navigate tool                    goto command     │
   │  (tools_navigation_enhanced.py)         (JSON)           │
   │           ↓                                     ↓         │
   │  [TRANSFORMS TO GPS]                    [AS-IS]          │
   │     - Body → NED → GPS                                   │
   │     - Offset → GPS                                       │
   │     - Uses telemetry & pymap3d                          │
   │           ↓                                     ↓         │
   │  Creates goto command with GPS          goto command     │
   │           ↓                                     ↓         │
   │           └──────────────┬──────────────────────┘        │
   │                          ↓                                │
   │                  DroneAPI.send_commands()                │
   │                  (mcp-server/core/drone_api.py)          │
   └─────────────────────────────────────────────────────────┘
                              ↓
                   HTTP POST to Server/Agent
                   {"name": "goto", "params": {...}}
                              ↓
                   Server (port 8002) - Routes to Agent
                              ↓
                   Agent (port 8001) - Receives Command
                              ↓
                   executor.py - Validates & Executes
                              ↓
                   goto.py - GotoCommand class
                              ↓
         ┌─────────────────────────────────────┐
         │   COORDINATE NORMALIZATION          │
         ├─────────────────────────────────────┤
         │                                     │
         │  IF params has lat/lon/alt:        │
         │    ✅ Use directly (already GPS)   │
         │                                     │
         │  IF params has north/east/down:    │
         │    ✅ Convert NED → GPS            │
         │       using pymap3d               │
         │                                     │
         │  Result: target_lat, target_lon,   │
         │          target_alt_msl            │
         └─────────────────────────────────────┘
                              ↓
         ┌─────────────────────────────────────┐
         │    FINAL MAVSDK CALL                │
         ├─────────────────────────────────────┤
         │                                     │
         │  await drone.action.goto_location(  │
         │      target_lat,      # float      │
         │      target_lon,      # float      │
         │      target_alt_msl,  # float MSL  │
         │      float("nan")     # maintain yaw│
         │  )                                  │
         └─────────────────────────────────────┘
                              ↓
                      PX4 MAVLink Protocol
                              ↓
                      Drone Motors!
```

---

## 🔍 **PATH-BY-PATH VERIFICATION**

### **Path 1: User says "fly forward 10m"**

```
1. LLM Handler (fallback parser):
   Input: "fly forward 10m"
   Output: {"name": "goto", "params": {"forward": 10, "maintain_altitude": true}}

2. MCP smart_navigate (if using MCP tools):
   - Fetches current telemetry (lat, lon, alt, yaw)
   - Transforms body frame to NED:
     * ned_north = 10 * cos(yaw) - 0 * sin(yaw)
     * ned_east = 10 * sin(yaw) + 0 * cos(yaw)
   - Gets current position in NED
   - Adds offset: new_ned = current_ned + transform
   - Converts NED → GPS using pymap3d
   - Creates: {"name": "goto", "params": {"latitude": X, "longitude": Y, "altitude": Z}}

3. Agent goto.py receives GPS coordinates:
   - Validates GPS params
   - Already GPS, no conversion needed
   - Calls: drone.action.goto_location(lat, lon, alt, nan)

✅ RESULT: MAVSDK receives (lat, lon, alt, yaw)
```

### **Path 2: User says "go 5m north"**

```
1. LLM Handler:
   Input: "go 5m north"
   Output: {"name": "goto", "params": {"offset_north": 5, "reference": "current", "maintain_altitude": true}}

2. MCP smart_navigate:
   - Fetches current position (GPS)
   - Converts current position to NED
   - Applies offset: new_ned = current_ned + (5, 0, 0)
   - Converts NED → GPS
   - Creates: {"name": "goto", "params": {"latitude": X, "longitude": Y, "altitude": Z}}

3. Agent goto.py receives GPS:
   - Validates GPS params
   - Calls: drone.action.goto_location(lat, lon, alt, nan)

✅ RESULT: MAVSDK receives (lat, lon, alt, yaw)
```

### **Path 3: User says "go to GPS 47.398, 8.546 at 500m"**

```
1. LLM Handler:
   Input: "go to GPS 47.398, 8.546 at 500m"
   Output: {"name": "goto", "params": {"latitude": 47.398, "longitude": 8.546, "altitude": 500}}

2. MCP (if used) or Direct:
   - Command already in GPS format
   - Passes through unchanged

3. Agent goto.py:
   - Validates GPS params
   - Already GPS, use directly
   - Calls: drone.action.goto_location(47.398, 8.546, 500, nan)

✅ RESULT: MAVSDK receives (lat, lon, alt, yaw)
```

### **Path 4: User says "go 50m north from origin" (Direct API)**

```
1. Direct API call:
   Input: {"name": "goto", "params": {"north": 50, "east": 0, "down": -15}}

2. Agent goto.py receives NED:
   - Detects NED coordinates (has north/east/down)
   - Calls _convert_ned_to_gps():
     * Fetches PX4 origin from telemetry
     * Uses pymap3d.ned2geodetic(50, 0, -15, origin_lat, origin_lon, origin_alt)
     * Returns: (target_lat, target_lon, target_alt_msl)
   - Calls: drone.action.goto_location(target_lat, target_lon, target_alt_msl, nan)

✅ RESULT: MAVSDK receives (lat, lon, alt, yaw)
```

### **Path 5: User says "return home"**

```
1. LLM Handler:
   Input: "return home"
   Output: {"name": "rtl", "params": {}}

2. Agent rtl.py:
   - Calls: await drone.action.return_to_launch()
   - PX4 handles navigation internally

✅ RESULT: PX4 native RTL (better than manual goto!)
```

---

## ✅ **VERIFICATION CHECKLIST**

### Agent goto.py (agent/commands/goto.py)

- [x] **Line 236-238**: Final MAVSDK call always uses `goto_location(lat, lon, alt, yaw)`
- [x] **Line 200-210**: GPS path - uses params directly
- [x] **Line 212-223**: NED path - converts to GPS first via `_convert_ned_to_gps()`
- [x] **Line 151-180**: `_convert_ned_to_gps()` uses pymap3d.ned2geodetic
- [x] **No other coordinate formats** reach MAVSDK

### MCP smart_navigate (mcp-server/tools_navigation_enhanced.py)

- [x] **Always outputs GPS**: Creates goto command with lat/lon/alt only
- [x] **Body frame**: Transforms to GPS before sending
- [x] **Offset**: Transforms to GPS before sending
- [x] **NED**: Can optionally pass through as NED (agent will convert)
- [x] **GPS**: Passes through unchanged

### Summary

✅ **ALL PATHS VERIFIED**
- Body frame → GPS (in MCP layer)
- Offset → GPS (in MCP layer)
- NED → GPS (in agent layer OR MCP layer)
- GPS → GPS (unchanged)
- Result: MAVSDK always gets `(lat, lon, alt, yaw)`

---

## 🎯 **WHY THIS DESIGN IS CORRECT**

### 1. **Clean Separation of Concerns**
- **MCP Layer**: Smart transformations for AI agents
- **Agent Layer**: Fallback NED support for direct API users
- **MAVSDK**: Only deals with GPS (standard MAVLink protocol)

### 2. **Backward Compatibility**
- Old API calls with NED still work (agent converts)
- New smart_navigate tool works seamlessly
- No breaking changes

### 3. **Performance**
- Transformations done once, close to data source
- No redundant conversions
- Telemetry fetched when needed for context

### 4. **Safety**
- Final GPS coordinates validated
- PX4 origin verification
- Bounds checking at multiple layers

---

## 🔒 **GUARANTEED MAVSDK INPUT**

```python
# THIS IS WHAT MAVSDK ALWAYS RECEIVES (agent/commands/goto.py:236)
await drone.action.goto_location(
    latitude_deg=float,    # WGS84 decimal degrees (-90 to 90)
    longitude_deg=float,   # WGS84 decimal degrees (-180 to 180)
    absolute_altitude_m=float,  # MSL altitude in meters
    yaw_deg=float         # Heading in degrees (or NaN for current)
)
```

**No Exceptions. No Alternatives. Always GPS.**

---

## 📚 **RELATED FILES**

- `agent/commands/goto.py` - Final GPS → MAVSDK conversion
- `mcp-server/tools_navigation_enhanced.py` - Smart coordinate transformations
- `mcp-server/core/llm_handler.py` - Natural language parsing
- `mcp-server/core/drone_api.py` - HTTP client for sending commands

---

**Verified:** September 30, 2025
**Status:** ✅ ALL COORDINATE PATHS CONFIRMED TO OUTPUT GPS FOR MAVSDK
