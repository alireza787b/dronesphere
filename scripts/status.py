#!/usr/bin/env python3
# scripts/status.py
"""Show current DroneSphere status and configuration."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
NC = '\033[0m'

print(f"{BLUE}DroneSphere Status{NC}")
print("=" * 50)

# Configuration
print(f"\n{YELLOW}Configuration:{NC}")
print(f"  Server Port: {os.getenv('SERVER_PORT', '8001')}")
print(f"  Web Port: {os.getenv('WEB_PORT', '3010')}")
print(f"  LLM Provider: {os.getenv('LLM_PROVIDER', 'ollama')}")
print(f"  CORS Origins: {os.getenv('CORS_ORIGINS', '[]')}")

# Check services
print(f"\n{YELLOW}Service Checks:{NC}")

# Check if .env exists
if Path(".env").exists():
    print(f"  {GREEN}✓{NC} .env file exists")
else:
    print(f"  {RED}✗{NC} .env file missing (run: cp .env.example .env)")

# Check virtual environments
if Path("server/.venv").exists():
    print(f"  {GREEN}✓{NC} Server virtual environment")
else:
    print(f"  {RED}✗{NC} Server venv missing (run: cd server && uv venv)")

if Path("agent/.venv").exists():
    print(f"  {GREEN}✓{NC} Agent virtual environment")
else:
    print(f"  {RED}✗{NC} Agent venv missing (run: cd agent && uv venv)")

# Check ports
import socket
ports_to_check = {
    "Server (8001)": 8001,
    "Web (3010)": 3010,
    "SITL (14540)": 14540,
}

print(f"\n{YELLOW}Port Status:{NC}")
for name, port in ports_to_check.items():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        print(f"  {name}: {GREEN}In use{NC}")
    else:
        print(f"  {name}: {RED}Free{NC}")

# Quick start commands
print(f"\n{YELLOW}Quick Start Commands:{NC}")
print("  1. Start SITL:")
print("     docker run --rm -it jonasvautherin/px4-gazebo-headless:latest")
print("  2. Start Server:")
print("     cd server && python run_server.py")
print("  3. Start Agent:")
print("     cd agent && python run_agent.py --dev")
print("  4. Test System:")
print("     python scripts/test_system.py")

print(f"\n{YELLOW}Useful Commands:{NC}")
print(f"  Fix config: python scripts/fix_env.py")
print(f"  Debug env: python scripts/debug_env.py")
print(f"  Kill port: fuser -k 8001/tcp")
print(f"  API Docs: http://localhost:{os.getenv('SERVER_PORT', '8001')}/docs")