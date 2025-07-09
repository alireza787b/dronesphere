#!/bin/bash
# Run all quality checks
# ======================

set -e

echo "🔍 DroneSphere Quality Checks"
echo "============================="

# Activate server environment
cd dronesphere/server
source .venv/bin/activate
cd ../..

echo "📝 Checking code formatting..."
if black --check dronesphere/ tests/ scripts/ --line-length=88; then
    echo "✅ Code formatting OK"
else
    echo "❌ Code needs formatting. Run: ./scripts/format-code.sh"
    exit 1
fi

echo ""
echo "🔧 Checking linting..."
if ruff check dronesphere/ tests/ scripts/; then
    echo "✅ Linting OK"
else
    echo "❌ Linting issues found. Run: ./scripts/format-code.sh"
    exit 1
fi

echo ""
echo "🧪 Running unit tests..."
if pytest tests/unit/ -v --tb=short; then
    echo "✅ Unit tests OK"
else
    echo "❌ Unit tests failed"
    exit 1
fi

echo ""
echo "✅ All quality checks passed!"
