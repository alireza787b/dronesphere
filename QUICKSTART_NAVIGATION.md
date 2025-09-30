# 🚁 Quick Start: Smart Navigation System

## For Users, AI Agents, and Developers

---

## 🎯 **30-Second Overview**

DroneSphere now has **smart_navigate** - ONE tool that handles ALL types of drone movement commands automatically. No need to understand coordinates!

---

## 🚀 **Quick Test (5 minutes)**

```bash
# 1. Start system
cd /root/dronesphere
make dev              # Start SITL + Agent + Server (wait 30s)
make mcp-n8n          # Start MCP server

# 2. Test in another terminal
curl -X POST http://localhost:8003/test-smart-navigate \
  -H "Content-Type: application/json" \
  -d '{"forward": 10}'
```

---

## 💬 **Natural Language Examples**

### What You Say → What Happens

| You Say | System Does |
|---------|-------------|
| "fly 10 meters forward" | Moves 10m in direction drone is facing |
| "go 5 meters north" | Moves 5m north from current position |
| "move right 3 meters" | Moves 3m to the right |
| "go up 5 meters" | Climbs 5 meters |
| "go 20 meters north from home" | Moves 20m north from takeoff point |
| "fly to GPS 47.398, 8.546" | Flies to exact GPS coordinates |

---

## 🔧 **For AI Agents (LLM/MCP)**

### Use smart_navigate Tool:

```python
# Body frame (most natural)
smart_navigate(forward=10, maintain_altitude=True)
smart_navigate(right=5, maintain_altitude=True)
smart_navigate(up_body=3)

# Offset from current position
smart_navigate(offset_north=10, reference="current", maintain_altitude=True)
smart_navigate(offset_up=5, reference="current")

# Offset from home
smart_navigate(offset_north=20, reference="home")

# Absolute GPS
smart_navigate(latitude=47.398, longitude=8.546, altitude_msl=500)
```

### Tool Auto-Detects Mode:
- Sees `forward`/`right` → Body frame mode
- Sees `offset_north`/`offset_east` → Offset mode
- Sees `latitude`/`longitude` → GPS mode
- Sees `north`/`east` → NED mode

---

## 📐 **Coordinate Systems (Simplified)**

### 1. Body Frame (Easiest!)
**Think:** Relative to where drone is facing
- `forward`: Straight ahead
- `right`: To the right
- `up_body`: Upward

**Use For:** "fly forward", "move right"

### 2. Offset from Reference
**Think:** Meters in compass direction from a point
- `offset_north`: Meters north
- `offset_east`: Meters east
- `offset_up`: Meters up (positive = up!)
- `reference`: "current" or "home"

**Use For:** "go north 5m", "go back to home"

### 3. GPS Absolute
**Think:** Exact location on Earth
- `latitude`: degrees (47.398)
- `longitude`: degrees (8.546)
- `altitude_msl`: meters above sea level

**Use For:** "go to GPS coordinates"

---

## 🧪 **Testing Scenarios**

### Test 1: Basic Body Frame
```bash
1. Takeoff to 10m
2. fly forward 10m     # Should move forward
3. fly right 5m        # Should move right
4. Land
```

### Test 2: Reference Frames
```bash
1. Takeoff to 15m
2. go 20m north        # From current
3. go 10m east         # From new current
4. go 5m north from home  # Back toward home
5. Land
```

### Test 3: Altitude Changes
```bash
1. Takeoff to 10m
2. go up 5m            # Climb to 15m
3. fly forward 10m     # Forward at 15m
4. go down 5m          # Descend to 10m
5. Land
```

---

## 🎓 **For n8n Users**

### Workflow Setup:

1. Import example: `mcp-server/examples/n8n-workflow.json`
2. MCP Client Tool URL: `http://172.17.0.1:8003/sse`
3. AI Agent → Chat → "fly 10 meters forward"

### Example Chat Commands:
```
"takeoff to 10 meters"
"fly forward 5 meters"
"go north 10 meters"
"what's the status?"
"land"
```

---

## 🐛 **Troubleshooting**

### "No coordinates specified"
**Fix:** Include at least one movement parameter
```python
# Wrong
smart_navigate()

# Right
smart_navigate(forward=10)
```

### "Direction is backward"
**Cause:** Mixing body frame vs compass directions
- Body frame: relative to drone heading
- Compass: fixed (north always north)

### "Altitude wrong"
**Remember:**
- `offset_up`: Positive = UP ✅
- `down` (NED): Negative = UP ⚠️

---

## 📚 **Full Documentation**

- **Complete Guide:** `mcp-server/NAVIGATION_GUIDE.md`
- **Technical Details:** `IMPLEMENTATION_SUMMARY.md`
- **Source Code:** `mcp-server/tools_navigation_enhanced.py`

---

## ✅ **Verify It's Working**

```bash
# Check MCP tools registered
curl http://localhost:8003/tools | grep smart_navigate

# Should see: "smart_navigate_wrapper"
```

---

## 🎯 **Key Takeaway**

**ONE tool. ALL coordinate types. Automatic transformation.**

Just tell the drone what you want in natural language, and smart_navigate handles the rest!

---

*Updated: September 30, 2025*
*Status: Implemented, Testing Pending*
