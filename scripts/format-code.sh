#!/bin/bash
# Format code with Black and Ruff
# ===============================

set -e

echo "🎨 Formatting DroneSphere Code"
echo "=============================="

# Activate server environment (has all dev tools)
cd dronesphere/server
source .venv/bin/activate
cd ../..

echo "📝 Running Black formatter..."
black dronesphere/ scripts/ tests/ --line-length=88

echo "🔧 Running Ruff linter (with fixes)..."
ruff check dronesphere/ scripts/ tests/ --fix

echo "✅ Code formatting complete!"
