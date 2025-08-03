#!/bin/bash
# diagnostic_fix.sh - Diagnose and fix telemetry issues

echo "🔧 DroneSphere Diagnostic and Fix Script"
echo "========================================"
echo ""

echo "📋 Step 1: Check Current System Status"
echo "======================================"
echo "Agent status:"
curl -s http://localhost:8001/health >/dev/null 2>&1 && echo "✅ Agent responding" || echo "❌ Agent not responding"

echo "Server status:"
curl -s http://localhost:8002/health >/dev/null 2>&1 && echo "✅ Server responding" || echo "❌ Server not responding"

echo ""
echo "📊 Step 2: Check Server Logs"
echo "============================"
if [[ -f /tmp/server.log ]]; then
    echo "Last 10 lines of server log:"
    tail -10 /tmp/server.log
else
    echo "❌ No server log found"
fi

echo ""
echo "🔧 Step 3: Fix UV Installation Issue"
echo "==================================="
echo "Checking UV installation..."
which uv && echo "✅ UV found in system" || echo "❌ UV not found"

echo "Installing server dependencies correctly..."
cd server
if [[ -d server-env ]]; then
    echo "✅ Server virtual environment exists"
    echo "Installing dependencies with system UV..."
    uv pip install -r requirements.txt --python server-env/bin/python
    echo "✅ Dependencies installed"
else
    echo "❌ Server virtual environment missing - creating..."
    uv venv server-env
    uv pip install -r requirements.txt --python server-env/bin/python
    echo "✅ Server environment created and dependencies installed"
fi
cd ..

echo ""
echo "🔍 Step 4: Check Python Import Issues"
echo "===================================="
echo "Testing server dependencies:"
cd server
server-env/bin/python -c "
try:
    import sys
    print(f'✅ Python: {sys.version.split()[0]}')
    import fastapi
    print('✅ FastAPI imported')
    import httpx
    print('✅ HTTPX imported')
    import requests
    print('✅ Requests imported')
    import yaml
    print('✅ YAML imported')
    print('✅ All server dependencies working')
except Exception as e:
    print(f'❌ Import error: {e}')
"
cd ..

echo ""
echo "🔍 Step 5: Test Configuration Loading"
echo "===================================="
echo "Testing YAML configuration loading:"
cd server
server-env/bin/python -c "
import sys
sys.path.append('..')
try:
    from shared.drone_config import get_fleet_config
    fleet_config = get_fleet_config()
    print(f'✅ Configuration loaded: {fleet_config.fleet_name}')
    print(f'✅ Total drones: {len(fleet_config.drones)}')
    print(f'✅ Active drones: {len(fleet_config.get_active_drones())}')
    for drone in fleet_config.get_active_drones():
        print(f'  - {drone.name}: {drone.endpoint}')
except Exception as e:
    print(f'❌ Configuration error: {e}')
    import traceback
    traceback.print_exc()
"
cd ..

echo ""
echo "🚀 Step 6: Restart Server with Better Error Handling"
echo "=================================================="
echo "Stopping current server..."
lsof -ti:8002 | xargs -r kill -TERM 2>/dev/null || true
sleep 2

echo "Starting server with verbose logging..."
cd server
nohup server-env/bin/python main.py > /tmp/server.log 2>&1 &
SERVER_PID=$!
cd ..

echo "Server PID: $SERVER_PID"
sleep 5

echo ""
echo "📊 Step 7: Test Server Response"
echo "==============================="
echo "Testing basic server health:"
response=$(curl -s http://localhost:8002/health)
if [[ -n "$response" ]]; then
    echo "✅ Server responding with data:"
    echo "$response" | python3 -m json.tool
else
    echo "❌ Server not responding - checking logs..."
    if [[ -f /tmp/server.log ]]; then
        echo "Recent server log:"
        tail -20 /tmp/server.log
    fi
fi

echo ""
echo "🔄 Step 8: Test Telemetry Endpoints"
echo "=================================="
if curl -s http://localhost:8002/health >/dev/null 2>&1; then
    echo "Testing telemetry endpoints:"

    echo "1. Fleet telemetry:"
    curl -s http://localhost:8002/fleet/telemetry && echo "" || echo "❌ Fleet telemetry failed"

    echo "2. Telemetry status:"
    curl -s http://localhost:8002/fleet/telemetry/status && echo "" || echo "❌ Telemetry status failed"

    echo "3. Configuration endpoints:"
    curl -s http://localhost:8002/fleet/config >/dev/null && echo "✅ Config endpoint working" || echo "❌ Config endpoint failed"
else
    echo "❌ Server still not responding"
fi

echo ""
echo "🏆 Diagnostic Complete"
echo "====================="
echo "Check the output above to identify the specific issue."
echo "Common fixes:"
echo "1. If import errors: run 'make reinstall-deps'"
echo "2. If server not starting: check /tmp/server.log"
echo "3. If configuration errors: check shared/drones.yaml syntax"
echo ""
