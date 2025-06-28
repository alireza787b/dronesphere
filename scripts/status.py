#!/usr/bin/env python3
# scripts/status.py
"""Show current DroneSphere status."""

import os
import socket
from pathlib import Path

from dotenv import load_dotenv

# Load environment
load_dotenv()

# Colors
G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[94m"
NC = "\033[0m"

print(f"\n{B}═══ DroneSphere Status ═══{NC}\n")

# Environment
print(f"{Y}Environment:{NC}")
print(f"  Server Port: {os.getenv('SERVER_PORT', '8001')}")
print(f"  LLM Provider: {os.getenv('LLM_PROVIDER', 'ollama')}")

# System checks
print(f"\n{Y}System Checks:{NC}")
checks = {
    ".env file": Path(".env").exists(),
    "Server venv": Path("server/.venv").exists(),
    "Agent venv": Path("agent/.venv").exists(),
}

for item, status in checks.items():
    symbol = f"{G}✓{NC}" if status else f"{R}✗{NC}"
    print(f"  {symbol} {item}")

# Port status
print(f"\n{Y}Port Status:{NC}")
ports = {"Server": 8001, "SITL": 14540}
for name, port in ports.items():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("localhost", port))
    sock.close()
    status = f"{G}Active{NC}" if result == 0 else f"{R}Free{NC}"
    print(f"  {name} ({port}): {status}")

# Quick commands
print(f"\n{Y}Commands:{NC}")
print(f"  Start server:  {G}python start_server.py{NC}")
print(f"  Start agent:   {G}cd agent && python run_agent.py{NC}")
print(f"  Run demo:      {G}./scripts/demo.sh{NC}")
print(f"  API docs:      {B}http://localhost:8001/docs{NC}")

# Current phase
print(f"\n{Y}Current Phase:{NC}")
print("  ✅ Agent implementation")
print("  ✅ Server foundation")
print("  ✅ WebSocket communication")
print("  🔄 Ready for LLM integration")
print("  ⏳ Frontend development\n")
