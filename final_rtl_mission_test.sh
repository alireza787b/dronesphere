# FINAL COMPREHENSIVE MISSION TEST WITH RTL
# This validates all systems working correctly

echo "🚀 Starting Final DroneSphere Mission Test with RTL"
echo "=================================================="

# 1. Pre-flight System Check
echo "📋 Pre-flight System Status Check..."
curl -s localhost:8001/health | jq '.'
curl -s localhost:8001/telemetry/state | jq '.'
curl -s localhost:8001/telemetry/position | jq '.position'

echo ""
echo "🎯 FINAL MISSION: Takeoff → Wait 5s → Navigate → Wait 3s → RTL"
echo "============================================================="

# 2. Execute Complete Mission with RTL
curl -X POST localhost:8001/commands \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {
        "name": "takeoff", 
        "params": {
          "altitude": 5.0,
          "altitude_tolerance": 0.5
        }
      },
      {
        "name": "wait", 
        "params": {
          "duration": 5.0
        }
      },
      {
        "name": "goto", 
        "params": {
          "north": 3.0,
          "east": 3.0, 
          "down": -5.0,
          "max_speed": 2.5,
          "tolerance": 1.5
        }
      },
      {
        "name": "wait", 
        "params": {
          "duration": 3.0
        }
      },
      {
        "name": "rtl", 
        "params": {
          "timeout": 120.0,
          "wait_for_landing": true
        }
      }
    ]
  }' | jq '.'

echo ""
echo "✅ Mission submitted! Monitoring execution..."
echo "============================================="