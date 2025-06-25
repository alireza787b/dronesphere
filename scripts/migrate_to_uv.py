#!/usr/bin/env python3
"""Migrate from Poetry to UV package manager."""

import os
import subprocess
import sys
from pathlib import Path
import toml

def check_uv_installed():
    """Check if UV is installed."""
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_uv():
    """Install UV."""
    print("📦 Installing UV...")
    
    # Install using the official installer
    if sys.platform == "win32":
        subprocess.run(["powershell", "-c", "irm https://astral.sh/uv/install.ps1 | iex"], check=True)
    else:
        subprocess.run(["curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"], shell=True, check=True)
    
    print("✅ UV installed successfully")

def convert_pyproject():
    """Convert pyproject.toml for UV."""
    print("\n📝 Converting pyproject.toml...")
    
    # Read current pyproject.toml
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
    
    # Create UV-compatible pyproject.toml
    uv_config = {
        "project": {
            "name": data["tool"]["poetry"]["name"],
            "version": data["tool"]["poetry"]["version"],
            "description": data["tool"]["poetry"]["description"],
            "authors": [{"name": author.split("<")[0].strip(), "email": author.split("<")[1].strip(">")} 
                       for author in data["tool"]["poetry"]["authors"]],
            "readme": "README.md",
            "requires-python": ">=3.10",
            "dependencies": {},
            "optional-dependencies": {
                "dev": {},
                "test": {},
            }
        },
        "tool": {
            "uv": {
                "dev-dependencies": []
            }
        }
    }
    
    # Convert dependencies
    deps = data["tool"]["poetry"]["dependencies"]
    for name, version in deps.items():
        if name == "python":
            continue
        if isinstance(version, str):
            uv_config["project"]["dependencies"][name] = version
        elif isinstance(version, dict) and "version" in version:
            uv_config["project"]["dependencies"][name] = version["version"]
    
    # Convert dev dependencies
    if "group" in data["tool"]["poetry"]:
        dev_deps = data["tool"]["poetry"]["group"].get("dev", {}).get("dependencies", {})
        for name, version in dev_deps.items():
            if isinstance(version, str):
                uv_config["project"]["optional-dependencies"]["dev"][name] = version
            elif isinstance(version, dict) and "version" in version:
                uv_config["project"]["optional-dependencies"]["dev"][name] = version["version"]
    
    # Save new pyproject.toml
    Path("pyproject.toml.backup").write_text(Path("pyproject.toml").read_text())
    
    with open("pyproject.toml", "w") as f:
        toml.dump(uv_config, f)
    
    print("✅ Converted pyproject.toml (backup saved as pyproject.toml.backup)")

def create_uv_scripts():
    """Create UV-based scripts."""
    print("\n📝 Creating UV scripts...")
    
    # Update setup script
    setup_script = '''#!/bin/bash
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
'''
    
    Path("scripts/setup_uv.sh").write_text(setup_script)
    os.chmod("scripts/setup_uv.sh", 0o755)
    
    # Create requirements.txt for drone controller
    requirements = '''# Drone Controller Requirements
mavsdk>=2.0.0
asyncio
aiohttp>=3.9.0
pydantic>=2.0.0
python-dotenv>=1.0.0
structlog>=24.0.0
'''
    
    Path("drone_controller/requirements.txt").write_text(requirements)
    
    print("✅ Created UV scripts")

def create_drone_controller_structure():
    """Create drone controller directory structure."""
    print("\n📁 Creating drone controller structure...")
    
    dirs = [
        "drone_controller/src/mavsdk_adapter",
        "drone_controller/src/command_receiver",
        "drone_controller/src/telemetry",
        "drone_controller/src/safety",
        "drone_controller/tests",
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        (Path(dir_path) / "__init__.py").touch()
    
    # Create main.py for drone controller
    main_content = '''#!/usr/bin/env python3
"""Main entry point for drone controller on Raspberry Pi."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def main():
    """Main drone controller loop."""
    print("🚁 DroneSphere Drone Controller Starting...")
    
    # TODO: Initialize MAVSDK connection
    # TODO: Connect to server WebSocket
    # TODO: Start telemetry loop
    # TODO: Start command receiver
    
    print("✅ Drone controller ready")
    
    try:
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\\n👋 Shutting down drone controller")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    Path("drone_controller/main.py").write_text(main_content)
    os.chmod("drone_controller/main.py", 0o755)
    
    print("✅ Created drone controller structure")

def main():
    """Run UV migration."""
    print("🚀 DroneSphere UV Migration Tool\n")
    
    # Check if UV is installed
    if not check_uv_installed():
        response = input("UV is not installed. Install it now? (y/n): ")
        if response.lower() == 'y':
            install_uv()
        else:
            print("❌ UV is required for migration")
            return
    
    # Confirm migration
    print("\n⚠️  This will:")
    print("  1. Backup current pyproject.toml")
    print("  2. Convert to UV format")
    print("  3. Create drone_controller structure")
    print("  4. Update scripts for UV")
    
    response = input("\nProceed with migration? (y/n): ")
    if response.lower() != 'y':
        print("❌ Migration cancelled")
        return
    
    # Run migration
    convert_pyproject()
    create_drone_controller_structure()
    create_uv_scripts()
    
    print("\n✅ Migration complete!")
    print("\n📝 Next steps:")
    print("  1. Remove poetry.lock: rm poetry.lock")
    print("  2. Create new environment: uv venv")
    print("  3. Install dependencies: uv pip install -e '.[dev]'")
    print("  4. Update .env with drone controller settings")

if __name__ == "__main__":
    main()