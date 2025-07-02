# tests/test_env_fix.py
"""
Test environment loading fix.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


# Fix environment loading
def setup_environment():
    """Ensure environment is loaded before imports."""
    # Try multiple paths for .env file
    env_paths = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✅ Loaded environment from: {env_path}")
            break
    else:
        print("⚠️  No .env file found, using system environment")


# Load environment BEFORE any imports
setup_environment()

# Now do imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "server" / "src"))

# Test that environment is loaded
print(
    f"OPENROUTER_API_KEY: {'✅ Set' if os.getenv('OPENROUTER_API_KEY') else '❌ Not set'}"
)
print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'Not set')}")
