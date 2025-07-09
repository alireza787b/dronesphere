#!/bin/bash
# DroneSphere Server Startup
# ==========================

set -e
echo "🌐 DroneSphere Server"
echo "====================="

# Check server environment exists
if [ ! -d "dronesphere/server/.venv" ]; then
    echo "❌ Server environment not found!"
    echo "💡 Run setup: ./setup-dronesphere-proper.sh"
    exit 1
fi

echo "📦 Activating server environment (full-featured)..."
cd dronesphere/server
source .venv/bin/activate

# Verify imports
if ! cd ../.. && python -c "import dronesphere.server.main" 2>/dev/null; then
    echo "❌ Server environment damaged. Re-run setup."
    exit 1
fi

echo "🚀 Starting server on port 8002..."
# Run from project root so shared/ paths work correctly
python -m dronesphere.server
