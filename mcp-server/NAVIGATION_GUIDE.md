# 🧭 DroneSphere Navigation System - Complete Guide

## For AI Agents, LLMs, and MCP Developers

---

## 📐 **COORDINATE SYSTEMS EXPLAINED**

### **1. GPS (Absolute Global Coordinates)**
- **Frame:** WGS84 Earth reference
- **Units:** Latitude/Longitude (degrees), Altitude MSL (meters)
- **Use:** "Go to specific GPS location"
- **Example:** Zurich ETH: `47.3977°N, 8.5456°E, 488m MSL`

### **2. NED (North-East-Down from Origin)**
- **Frame:** Local tangent plane from PX4 origin
- **Origin:** First GPS fix location (home/takeoff point)
- **Units:** Meters
- **Axes:**
  - North: Positive = north direction
  - East: Positive = east direction
  - Down: Positive = down, Negative = up
- **Use:** "Go X meters north/east from home"

### **3. Body Frame (Drone-Relative)**
- **Frame:** Attached to drone, moves with it
- **Axes:**
  - Forward: Positive = forward (nose direction)
  - Right: Positive = right (starboard)
  - Up: Positive = up (towards sky)
- **Use:** "Fly 10m forward" (relative to where drone faces)

### **4. Offset from Reference**
- **Frame:** Offset from specified reference point
- **Reference Options:**
  - `current`: From current position
  - `home`: From PX4 origin (takeoff point)
  - `origin`: Same as home
- **Use:** "Go 5m north from current position"

---

## 🎯 **THE smart_navigate TOOL**

### **Design Philosophy**

**ONE TOOL TO RULE THEM ALL**

The `smart_navigate` tool automatically:
1. Detects which coordinate system you're using
2. Fetches required telemetry (position, yaw, origin)
3. Performs ALL necessary transformations
4. Sends properly formatted command to drone

**LLM doesn't need to:**
- Chain multiple tool calls
- Understand coordinate mathematics
- Know about pymap3d or transformations
- Worry about reference frames

---

## 📝 **USAGE EXAMPLES FOR LLMs**

### **Mode 1: Absolute GPS**

**User Intent:** "Go to GPS coordinates 47.398, 8.546 at 500m altitude"

**MCP Tool Call:**
```python
smart_navigate(
    latitude=47.398,
    longitude=8.546,
    altitude_msl=500
)
```

---

### **Mode 2: NED from Origin (Home)**

**User Intent:** "Go 50 meters north and 30 meters east from home"

**MCP Tool Call:**
```python
smart_navigate(
    north=50,
    east=30,
    down=-15  # 15m altitude above origin
)
```

---

### **Mode 3: Body Frame (Most Natural!)**

**User Intent:** "Fly 10 meters forward"

**MCP Tool Call:**
```python
smart_navigate(
    forward=10,
    maintain_altitude=True
)
```

**User Intent:** "Move 10m forward and 5m right"

**MCP Tool Call:**
```python
smart_navigate(
    forward=10,
    right=5,
    maintain_altitude=True
)
```

**User Intent:** "Go up 5 meters"

**MCP Tool Call:**
```python
smart_navigate(
    up_body=5  # Or use offset_up=5 with reference="current"
)
```

---

### **Mode 4: Offset from Reference**

**User Intent:** "Go 5 meters north"

**MCP Tool Call:**
```python
smart_navigate(
    offset_north=5,
    reference="current",  # From current position
    maintain_altitude=True
)
```

**User Intent:** "Go 20 meters north from home"

**MCP Tool Call:**
```python
smart_navigate(
    offset_north=20,
    reference="home"  # From home/origin
)
```

**User Intent:** "Move 10m north, 5m east, and 3m up from current position"

**MCP Tool Call:**
```python
smart_navigate(
    offset_north=10,
    offset_east=5,
    offset_up=3,
    reference="current"
)
```

---

## 🔄 **AUTOMATIC TRANSFORMATIONS**

### **What Happens Behind the Scenes**

#### **Example: "Fly 10m forward"**

1. **LLM calls:** `smart_navigate(forward=10, maintain_altitude=True)`
2. **Tool fetches telemetry:**
   - Current position: 47.3977°N, 8.5456°E, 488m MSL
   - Current yaw: 45° (facing northeast)
   - PX4 origin: 47.3977°N, 8.5456°E, 488m MSL
3. **Tool transforms Body → NED:**
   ```python
   # Rotation by yaw angle
   ned_north = 10 * cos(45°) - 0 * sin(45°) = 7.07m
   ned_east = 10 * sin(45°) + 0 * cos(45°) = 7.07m
   ```
4. **Tool converts NED → GPS:**
   ```python
   # Using pymap3d with current position as reference
   target_lat = 47.397763° N  # ~7m north
   target_lon = 8.545697° E   # ~7m east
   target_alt = 488m MSL      # Maintain altitude
   ```
5. **Tool sends to agent:**
   ```json
   {
     "name": "goto",
     "params": {
       "latitude": 47.397763,
       "longitude": 8.545697,
       "altitude": 488.0,
       "speed": 5.0
     }
   }
   ```

---

## 🎓 **LLM TRAINING EXAMPLES**

### **Natural Language → Tool Call Mapping**

| User Says | Tool Call |
|-----------|-----------|
| "fly 5 meters forward" | `smart_navigate(forward=5, maintain_altitude=True)` |
| "move right 3 meters" | `smart_navigate(right=3, maintain_altitude=True)` |
| "go up 10 meters" | `smart_navigate(offset_up=10, reference="current")` |
| "fly north 20 meters" | `smart_navigate(offset_north=20, reference="current", maintain_altitude=True)` |
| "return to home" | Use `execute_drone_command("rtl")` instead |
| "go to GPS 47.398, 8.546" | `smart_navigate(latitude=47.398, longitude=8.546)` |
| "fly 10m forward then 5m right" | TWO calls: `smart_navigate(forward=10)` then `smart_navigate(right=5)` |
| "move 10m forward and 5m right" | ONE call: `smart_navigate(forward=10, right=5, maintain_altitude=True)` |
| "go 50m north from home" | `smart_navigate(offset_north=50, reference="home")` |

---

## ⚙️ **ADVANCED PARAMETERS**

### **Speed Control**
```python
smart_navigate(forward=20, speed=10.0)  # Fast movement
smart_navigate(forward=5, speed=1.0)    # Slow/precise
```

### **Yaw/Heading Control**
```python
smart_navigate(
    offset_north=10,
    reference="current",
    yaw=180  # Face south while moving
)
```

### **Maintain Current Altitude**
```python
smart_navigate(
    forward=10,
    maintain_altitude=True  # Stay at current height
)
```

---

## 🔍 **COORDINATE PRIORITY & DETECTION**

The tool detects coordinate mode in this order:

1. **Absolute GPS** (if `latitude` AND `longitude` provided)
2. **NED from origin** (if `north` OR `east` OR `down` provided)
3. **Body frame** (if `forward` OR `right` OR `up_body` provided)
4. **Offset from reference** (if `offset_north` OR `offset_east` OR `offset_up` provided)
5. **Error** (if nothing provided)

**Mixing Modes:** Tool will use the FIRST matching mode and ignore others.

---

## 🧪 **TESTING THE SYSTEM**

### **Test Scenario 1: Body Frame Navigation**

```bash
# Start system
make dev
make mcp-n8n

# In n8n or MCP Inspector:
1. "takeoff to 10 meters"
2. "fly 5 meters forward"
3. "turn right and fly 10 meters forward"  # Requires two commands
4. "land"
```

### **Test Scenario 2: Reference-Based Navigation**

```bash
1. "takeoff to 15 meters"
2. "go 20 meters north"  # From current
3. "go 10 meters east"   # From new current
4. "go back to home location"  # offset_north=0, offset_east=0, reference="home"
5. "land"
```

### **Test Scenario 3: Absolute GPS**

```bash
1. "takeoff to 10 meters"
2. "go to GPS coordinates 47.398, 8.546 at altitude 500 meters"
3. "land"
```

---

## 🚨 **COMMON PITFALLS & SOLUTIONS**

### **Problem: "Fly forward doesn't work"**
**Cause:** Old LLM handler using execute_drone_command instead of smart_navigate
**Solution:** Update LLM system prompt to prioritize smart_navigate for navigation

### **Problem: "Direction is wrong"**
**Cause:** Confusing body frame vs NED frame
**Solution:**
- Body frame: "forward/right" (relative to drone heading)
- NED frame: "north/east" (absolute directions)

### **Problem: "Altitude is wrong"**
**Cause:** Mixing MSL vs relative altitude
**Solution:**
- GPS: Always MSL (Mean Sea Level)
- NED down: Negative for altitude (down=-15 means 15m up)
- offset_up: Positive for altitude (offset_up=15 means 15m up)

---

## 📚 **INTEGRATION WITH EXISTING TOOLS**

### **When to Use smart_navigate:**
✅ Any movement command
✅ Position changes
✅ Navigation requests

### **When to Use execute_drone_command:**
✅ Takeoff
✅ Land
✅ RTL (return to launch)
✅ Wait/hover
✅ Complex multi-step sequences

### **When to Use get_drone_status:**
✅ Status queries
✅ Battery checks
✅ Position queries (but not for navigation)

---

## 🎯 **BEST PRACTICES FOR LLM AGENTS**

1. **Always use smart_navigate for movement**
   - Don't try to calculate coordinates yourself
   - Don't chain transformation tools manually

2. **Use maintain_altitude=True for horizontal movement**
   ```python
   smart_navigate(forward=10, maintain_altitude=True)
   ```

3. **Be explicit about reference frames**
   ```python
   # Good
   smart_navigate(offset_north=10, reference="current")

   # Less clear
   smart_navigate(north=10)  # From origin? From current? Ambiguous!
   ```

4. **Break complex maneuvers into simple steps**
   ```python
   # User: "fly forward 10m then right 5m"
   # Call 1:
   smart_navigate(forward=10, maintain_altitude=True)
   # Call 2:
   smart_navigate(right=5, maintain_altitude=True)
   ```

5. **Always check success response**
   - Tool returns detailed success/error info
   - Use command_id to track execution

---

## 🔧 **TROUBLESHOOTING**

### **Error: "No coordinates specified"**
**Solution:** Provide at least one coordinate parameter

### **Error: "PX4 origin not available"**
**Solution:** Ensure drone has GPS fix before using NED coordinates

### **Error: "pymap3d library required"**
**Solution:** Should never happen (pre-installed), but: `uv pip install pymap3d`

---

## 📊 **PERFORMANCE CHARACTERISTICS**

- **Telemetry fetch:** ~50ms (cached) to ~500ms (live)
- **Coordinate transformation:** <1ms (pymap3d is fast)
- **Command execution:** Asynchronous (returns immediately)
- **Movement time:** Depends on distance and speed

---

## 🎓 **FOR MCP/LLM DEVELOPERS**

### **Why This Design?**

1. **Single tool simplicity:** LLM calls ONE tool, not a chain
2. **Automatic detection:** No need to teach LLM coordinate math
3. **Natural language friendly:** Maps directly to user intent
4. **Robust:** Handles edge cases internally
5. **Extensible:** Easy to add new coordinate modes

### **Architecture Benefits:**

- **LLM sees:** Simple tool with clear intent
- **Tool handles:** Complex coordinate transformations
- **Agent receives:** Clean, validated GPS commands
- **PX4 gets:** Standard lat/lon/alt/yaw MAVLink commands

### **Why Not Just GPS?**

Users don't think in GPS coordinates! They say:
- "Fly forward" ← Body frame
- "Go north 5 meters" ← Relative offset
- "Return to starting point" ← Reference frame

Our system bridges natural language ↔ GPS coordinates automatically.

---

**Welcome to professional drone navigation! 🚁**

*The smart_navigate tool makes complex coordinate transformations invisible to AI agents, enabling truly natural language drone control.*
