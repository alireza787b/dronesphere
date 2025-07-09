
set -e

echo "🚁 DroneSphere Setup"
echo "==================="

# Check UV is installed
if ! command -v uv >/dev/null; then
    echo "❌ UV not found. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ UV detected: $(uv --version)"

# Create virtual environments with UV
echo "📦 Creating UV virtual environments..."
cd dronesphere/
uv venv .venv-agent
uv venv .venv-server
cd ..

# Install dependencies in both environments using uv sync
echo "📥 Installing dependencies with UV..."

# Agent environment
cd dronesphere/
uv sync --env .venv-agent
touch .venv-agent/installed

# Server environment  
uv sync --env .venv-server
touch .venv-server/installed
cd ..

# Make scripts executable
chmod +x scripts/*.sh

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 Quick start:"
echo "   ./scripts/quick-start.sh"
echo ""
echo "🔧 Manual start:"
echo "   ./scripts/run_sitl.sh      # Terminal 1"
echo "   ./scripts/start-server.sh  # Terminal 2" 
echo "   ./scripts/start-