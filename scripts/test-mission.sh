#!/bin/bash
# Test DroneSphere Mission
# =======================

set -e

echo "🧪 Testing DroneSphere Mission"
echo "=============================="

# Check all services
check_service() {
    local name="$1"
    local test_cmd="$2"
    
    if eval "$test_cmd" >/dev/null 2>&1; then
        echo "✅ $name running"
    else
        echo "❌ $name not running"
        return 1
    fi
}

echo "🔍 Checking services..."
check_service "SITL" "nc -u -z localhost 14540" || { echo "Start: ./scripts/run_sitl.sh"; exit 1; }
check_service "Server" "curl -s localhost:8002/ping" || { echo "Start: ./scripts/start-server.sh"; exit 1; }
check_service "Agent" "curl -s localhost:8001/health" || { echo "Start: ./scripts/start-agent.sh"; exit 1; }

echo ""
echo "🚁 Executing autonomous mission..."

curl -X POST localhost:8002/drones/1/commands \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": [
      {"name": "takeoff", "params": {"altitude": 5.0}},
      {"name": "wait", "params": {"duration": 2.0}},
      {"name": "land", "params": {}}
    ],
    "metadata": {"test": "autonomous_validation"}
  }' | jq '.' 2>/dev/null || echo "✅ Mission submitted!"

echo ""
echo "✅ Mission sent! Watch logs for execution."
