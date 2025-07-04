# scripts/test.sh
# ===================================
#!/bin/bash

# Test runner script with different test categories

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
TEST_TYPE="all"
COVERAGE=false
VERBOSE=false
MARKERS=""

show_help() {
    cat << EOF
DroneSphere Test Runner

Usage: $0 [OPTIONS] [TEST_TYPE]

Test Types:
    unit            Run unit tests only
    integration     Run integration tests only
    sitl            Run SITL integration tests only
    performance     Run performance tests only
    all             Run all tests (default)

Options:
    -c, --coverage      Generate coverage report
    -v, --verbose       Verbose output
    -m, --markers       Additional pytest markers
    -f, --failfast      Stop on first failure
    -h, --help          Show this help message

Examples:
    $0                      # Run all tests
    $0 unit                 # Run only unit tests
    $0 --coverage unit      # Run unit tests with coverage
    $0 -v integration       # Run integration tests with verbose output
    $0 -m "not slow"        # Run tests excluding slow ones

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|sitl|performance|all)
            TEST_TYPE="$1"
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--failfast)
            FAILFAST=true
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

echo -e "${BLUE}🧪 DroneSphere Test Runner${NC}"
echo "=========================="
echo "Test type: $TEST_TYPE"
echo "Coverage: $COVERAGE"
echo "Verbose: $VERBOSE"
echo "=========================="

cd "$PROJECT_DIR"

# Activate virtual environment
if [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
elif [[ -f .venv/Scripts/activate ]]; then
    source .venv/Scripts/activate
else
    echo -e "${YELLOW}⚠️  No virtual environment found${NC}"
fi

# Build pytest command
PYTEST_CMD="python -m pytest"

# Add verbosity
if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# Add failfast
if [[ "$FAILFAST" == "true" ]]; then
    PYTEST_CMD="$PYTEST_CMD -x"
fi

# Add coverage
if [[ "$COVERAGE" == "true" ]]; then
    PYTEST_CMD="$PYTEST_CMD --cov=dronesphere --cov-report=term-missing --cov-report=html"
fi

# Add custom markers
if [[ -n "$MARKERS" ]]; then
    PYTEST_CMD="$PYTEST_CMD -m \"$MARKERS\""
fi

# Select test paths and markers based on type
case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}🔬 Running unit tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/unit/ -m unit"
        ;;
    integration)
        echo -e "${YELLOW}🔗 Running integration tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/integration/ -m integration"
        ;;
    sitl)
        echo -e "${YELLOW}🚁 Running SITL tests...${NC}"
        echo -e "${YELLOW}⚠️  Make sure SITL is running (./scripts/run_sitl.sh)${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/integration/sitl/ -m sitl"
        ;;
    performance)
        echo -e "${YELLOW}⚡ Running performance tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/performance/ -m performance"
        ;;
    all)
        echo -e "${YELLOW}🎯 Running all tests...${NC}"
        PYTEST_CMD="$PYTEST_CMD tests/"
        ;;
esac

# Check for SITL requirement
if [[ "$TEST_TYPE" == "sitl" || "$TEST_TYPE" == "all" ]]; then
    if ! curl -s -f http://localhost:8080/mavlink/vehicles >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  SITL not detected. Skipping SITL tests.${NC}"
        if [[ "$TEST_TYPE" == "sitl" ]]; then
            echo -e "${RED}❌ Cannot run SITL tests without SITL running${NC}"
            echo "Start SITL with: ./scripts/run_sitl.sh"
            exit 1
        else
            PYTEST_CMD="$PYTEST_CMD -m \"not sitl\""
        fi
    fi
fi

# Run tests
echo -e "${YELLOW}⚙️  Command: $PYTEST_CMD${NC}"
echo ""

if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✅ Tests passed!${NC}"
    
    if [[ "$COVERAGE" == "true" ]]; then
        echo -e "${BLUE}📊 Coverage report saved to htmlcov/index.html${NC}"
    fi
else
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    exit 1
fi
