#!/bin/bash
# Validate DroneSphere Setup
# =========================

set -e

echo "🔍 DroneSphere Setup Validation"
echo "==============================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

errors=0

# Check environments
echo "📱 Checking Agent Environment..."
if [ -d "dronesphere/agent/.venv" ]; then
    cd dronesphere/agent
    if source .venv/bin/activate 2>/dev/null && cd ../.. && python -c "import dronesphere.agent.main" 2>/dev/null; then
        print_success "Agent environment working"
    else
        print_error "Agent environment has import issues"
        errors=$((errors+1))
    fi
    deactivate 2>/dev/null || true
else
    print_error "Agent environment missing"
    errors=$((errors+1))
fi

echo ""
echo "🖥️  Checking Server Environment..."
if [ -d "dronesphere/server/.venv" ]; then
    cd dronesphere/server
    if source .venv/bin/activate 2>/dev/null && cd ../.. && python -c "import dronesphere.server.main" 2>/dev/null; then
        print_success "Server environment working"
    else
        print_error "Server environment has import issues"
        errors=$((errors+1))
    fi
    deactivate 2>/dev/null || true
else
    print_error "Server environment missing"
    errors=$((errors+1))
fi

echo ""
echo "🧪 Checking Tests..."
cd dronesphere/server && source .venv/bin/activate && cd ../..
if pytest tests/unit/test_config.py tests/unit/test_imports.py -v --tb=short 2>/dev/null; then
    print_success "Basic tests passing"
else
    print_warning "Some tests failing (may need fixes)"
fi

echo ""
echo "🎨 Checking Code Quality Tools..."
if black --check dronesphere/ tests/ scripts/ --exclude "scripts/buil_mavlink2rest.py" 2>/dev/null; then
    print_success "Code formatting OK"
else
    print_warning "Code needs formatting"
fi

if ruff check dronesphere/ tests/ scripts/ --exclude "scripts/buil_mavlink2rest.py" 2>/dev/null; then
    print_success "Linting OK"
else
    print_warning "Linting issues found"
fi

echo ""
echo "📁 Checking File Structure..."
required_files=(
    "dronesphere/agent/.venv"
    "dronesphere/server/.venv"
    "shared/drones.yaml"
    "scripts/start-agent.sh"
    "scripts/start-server.sh"
    ".pre-commit-config.yaml"
    "pytest.ini"
)

for file in "${required_files[@]}"; do
    if [ -e "$file" ]; then
        print_success "$file exists"
    else
        print_error "$file missing"
        errors=$((errors+1))
    fi
done

echo ""
if [ $errors -eq 0 ]; then
    print_success "All validation checks passed!"
    echo ""
    echo "🚀 Ready for development:"
    echo "   ./scripts/run_sitl.sh      # Terminal 1"
    echo "   ./scripts/start-server.sh  # Terminal 2"  
    echo "   ./scripts/start-agent.sh   # Terminal 3"
else
    print_error "$errors validation errors found"
    echo ""
    echo "🔧 Fix issues and run again: ./scripts/validate-setup.sh"
fi

deactivate 2>/dev/null || true
