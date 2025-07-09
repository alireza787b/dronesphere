#!/bin/bash
# DroneSphere Agent Startup
# =========================

set -e
echo "🚁 DroneSphere Agent"
echo "===================="

# Check SITL/Hardware connection
if ! nc -u -z localhost 14540 2>/dev/null; then
    echo "⚠️  Flight controller not detected on port 14540"
    echo "💡 For SITL: ./scripts/run_sitl.sh"
    echo "💡 For hardware: Check MAVLink connection"
    exit 1
fi

# Check agent environment exists
if [ ! -d "dronesphere/agent/.venv" ]; then
    echo "❌ Agent environment not found!"
    echo "💡 Run setup: ./setup-dronesphere-proper.sh"
    exit 1
fi

echo "📦 Activating agent environment (hardware-optimized)..."
cd dronesphere/agent
source .venv/bin/activate

# Verify imports
if ! cd ../.. && python -c "import dronesphere.agent.main" 2>/dev/null; then
    echo "❌ Agent environment damaged. Re-run setup."
    exit 1
fi

echo "🚀 Starting agent on port 8001..."
# Run from project root so shared/ paths work correctly  
python -m dronesphere.agent
