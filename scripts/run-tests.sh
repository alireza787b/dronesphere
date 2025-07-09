#!/bin/bash
# Run DroneSphere Tests
# ====================

set -e

echo "🧪 Running DroneSphere Tests"
echo "============================"

# Function to run tests in specific environment
run_tests_in_env() {
    local env_name="$1"
    local env_path="$2"
    local test_type="$3"
    
    echo ""
    echo "📱 Running $test_type tests in $env_name environment..."
    
    cd "$env_path"
    source .venv/bin/activate
    cd ../..
    
    if [ "$test_type" = "unit" ]; then
        pytest tests/unit/ -v -m "not integration"
    elif [ "$test_type" = "integration" ]; then
        pytest tests/integration/ -v -m "integration"
    else
        pytest tests/ -v
    fi
    
    deactivate
}

# Default to unit tests (fast)
TEST_TYPE=${1:-unit}

case $TEST_TYPE in
    "unit")
        echo "🏃 Running unit tests (fast)..."
        run_tests_in_env "Server" "dronesphere/server" "unit"
        ;;
    "integration")
        echo "🔌 Running integration tests (requires running services)..."
        run_tests_in_env "Server" "dronesphere/server" "integration"
        ;;
    "all")
        echo "🎯 Running all tests..."
        run_tests_in_env "Server" "dronesphere/server" "all"
        ;;
    *)
        echo "Usage: $0 [unit|integration|all]"
        echo "  unit:        Fast unit tests (default)"
        echo "  integration: Integration tests (requires services)"
        echo "  all:         All tests"
        exit 1
        ;;
esac

echo ""
echo "✅ Tests complete!"
