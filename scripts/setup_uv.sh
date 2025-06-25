#!/bin/bash
# DroneSphere UV Setup Script

echo "🚁 Setting up DroneSphere with UV..."

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv pip install -e ".[dev]"

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
uv pip install pre-commit
pre-commit install

echo "✅ Setup complete! Activate with: source .venv/bin/activate"
