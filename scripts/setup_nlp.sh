#!/bin/bash
# scripts/setup_nlp.sh
# Setup script for NLP service dependencies and verification

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚁 DroneSphere NLP Service Setup${NC}"
echo "===================================="

# Check if in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${RED}❌ Error: Not in a virtual environment!${NC}"
    echo "Please activate your virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "\n${YELLOW}Python version:${NC} $PYTHON_VERSION"

# Install spaCy if not installed
echo -e "\n${YELLOW}Checking spaCy installation...${NC}"
if ! python -c "import spacy" 2>/dev/null; then
    echo "Installing spaCy..."
    uv pip install spacy
else
    echo -e "${GREEN}✓ spaCy is installed${NC}"
fi

# Download spaCy models
echo -e "\n${YELLOW}Downloading spaCy models...${NC}"

# Function to download model if not exists
download_model() {
    local model=$1
    local size=$2
    
    echo -n "Checking $model ($size)... "
    
    if python -c "import spacy; spacy.load('$model')" 2>/dev/null; then
        echo -e "${GREEN}✓ Already installed${NC}"
    else
        echo -e "${YELLOW}Downloading...${NC}"
        python -m spacy download $model
    fi
}

# Download models (small is required, others optional)
download_model "en_core_web_sm" "~13MB - Required"
# download_model "en_core_web_md" "~40MB - Recommended for production"
# download_model "en_core_web_lg" "~560MB - Best accuracy"

# Create directory structure if not exists
echo -e "\n${YELLOW}Creating directory structure...${NC}"
mkdir -p src/core/ports/output
mkdir -p src/adapters/output/nlp/providers
mkdir -p tests/unit/adapters/nlp
mkdir -p tests/integration/nlp
mkdir -p config

# Create __init__.py files
touch src/core/ports/output/__init__.py
touch src/adapters/output/nlp/__init__.py
touch src/adapters/output/nlp/providers/__init__.py
touch tests/unit/adapters/nlp/__init__.py
touch tests/integration/nlp/__init__.py

echo -e "${GREEN}✓ Directory structure created${NC}"

# Verify imports work
echo -e "\n${YELLOW}Verifying NLP imports...${NC}"

python -c "
import sys
try:
    from src.core.ports.output.nlp_service import NLPServicePort
    print('✓ NLP Port import successful')
    
    from src.adapters.output.nlp.providers.spacy_adapter import SpacyNLPAdapter
    print('✓ spaCy Adapter import successful')
    
    from src.adapters.output.nlp.factory import NLPServiceFactory
    print('✓ NLP Factory import successful')
    
    from config.nlp_config import NLPConfig
    print('✓ NLP Config import successful')
    
    print('\n✅ All imports working correctly!')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

# Quick functionality test
echo -e "\n${YELLOW}Running quick functionality test...${NC}"

python -c "
import asyncio
from src.adapters.output.nlp.providers.spacy_adapter import SpacyNLPAdapter

async def test():
    adapter = SpacyNLPAdapter()
    result = await adapter.parse_command('take off to 50 meters')
    if result.success:
        print(f'✓ Successfully parsed: {result.command.describe()}')
        print(f'  Intent: {result.intent.intent} (confidence: {result.intent.confidence:.2f})')
        print(f'  Provider: {result.provider_used}')
        print(f'  Model: {result.model_used}')
        return True
    else:
        print(f'❌ Parse failed: {result.error}')
        return False

success = asyncio.run(test())
exit(0 if success else 1)
"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ NLP Service setup complete!${NC}"
    
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Run the comprehensive test:"
    echo "   python scripts/test_nlp_complete.py"
    echo ""
    echo "2. Run unit tests:"
    echo "   pytest tests/unit/adapters/nlp/ -v"
    echo ""
    echo "3. Run integration tests:"
    echo "   pytest tests/integration/nlp/ -v"
    echo ""
    echo "4. Configure your .env file with:"
    echo "   NLP_PROVIDER=spacy"
    echo "   SPACY_MODEL=en_core_web_sm"
    echo "   NLP_CONFIDENCE_THRESHOLD=0.7"
    
    echo -e "\n${GREEN}Optional: Install larger models for better accuracy:${NC}"
    echo "   python -m spacy download en_core_web_md  # Recommended"
    echo "   python -m spacy download en_core_web_lg  # Best accuracy"
    
    echo -e "\n${YELLOW}⚠️  Note about confidence scores:${NC}"
    echo "   The small model (en_core_web_sm) gives lower confidence scores (0.4-0.6)."
    echo "   This is normal. For production, use en_core_web_md or larger."
else
    echo -e "\n${RED}❌ Setup failed!${NC}"
    exit 1
fi