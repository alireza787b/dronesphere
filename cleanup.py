#!/usr/bin/env python3
# cleanup.py - Clean up redundant scripts and organize project

import os
import shutil
from pathlib import Path

print("🧹 Cleaning up DroneSphere project...")
print("=" * 50)

# Files to remove (redundant/temporary)
files_to_remove = [
    # Root level redundant scripts
    "fix_all.py",
    "simple_start.py",
    "start_server.sh",
    "test_direct.py",
    "test_server.py",
    "run_server.sh",
    "final_fix.py",
    # Server redundant scripts
    "server/direct_run.py",
    "server/run_server.py",
    "server/start.py",
    # Scripts redundant scripts
    "scripts/check_env.sh",
    "scripts/check_imports.py",
    "scripts/debug_env.py",
    "scripts/diagnose.py",
    "scripts/fix_structure.py",
    "scripts/quick_start.sh",
    "scripts/run_all.sh",
    "scripts/test_config.py",
    "scripts/test_final.sh",
    "scripts/test_openrouter_api.py",
    # Weird directory
    "# server",
    "erver",
]

# Remove files
removed = 0
for file_path in files_to_remove:
    path = Path(file_path)
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        print(f"  ✓ Removed {file_path}")
        removed += 1

print(f"\n📊 Removed {removed} redundant files/directories")

# Create proper startup script
startup_content = '''#!/usr/bin/env python3
"""
DroneSphere Server Startup Script

Usage:
    python start_server.py [--port PORT]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Start DroneSphere Server")
    parser.add_argument("--port", type=int, default=8001, help="Server port (default: 8001)")
    args = parser.parse_args()

    # Setup environment
    root_dir = Path(__file__).parent
    os.chdir(root_dir)

    # Load .env
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()

    # Kill existing process on port
    subprocess.run(["fuser", "-k", f"{args.port}/tcp"], stderr=subprocess.DEVNULL)

    print(f"🚁 Starting DroneSphere Server on port {args.port}")
    print(f"📚 API Docs: http://localhost:{args.port}/docs")
    print(f"🔍 Health: http://localhost:{args.port}/health")
    print("-" * 50)

    # Start server
    os.chdir("server")
    os.environ["PYTHONPATH"] = f"src:{os.environ.get('PYTHONPATH', '')}"

    cmd = [
        sys.executable, "-m", "uvicorn",
        "server.main:app",
        "--host", "0.0.0.0",
        "--port", str(args.port),
        "--reload"
    ]

    subprocess.run(cmd)

if __name__ == "__main__":
    main()
'''

# Create the single startup script
with open("start_server.py", "w") as f:
    f.write(startup_content)
os.chmod("start_server.py", 0o755)
print("\n✅ Created unified start_server.py")

# Update scripts/demo.sh to use new structure
demo_content = """#!/bin/bash
# scripts/demo.sh
# Run complete DroneSphere demo

set -e

GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

echo -e "${GREEN}🚁 DroneSphere Demo${NC}"
echo "===================="

# Check SITL
if ! nc -z localhost 14540 2>/dev/null; then
    echo -e "${YELLOW}⚠️  SITL not detected${NC}"
    echo "Run: docker run --rm -it jonasvautherin/px4-gazebo-headless:latest"
    exit 1
fi

# Start services
echo -e "${GREEN}Starting services...${NC}"

# Server
echo "1. Starting server..."
python start_server.py &
SERVER_PID=$!

sleep 5

# Agent
echo "2. Starting agent..."
cd agent && python run_agent.py --dev &
AGENT_PID=$!
cd ..

echo -e "\\n${GREEN}✅ Demo running!${NC}"
echo "Server: http://localhost:8001/docs"
echo "Press Ctrl+C to stop"

trap "kill $SERVER_PID $AGENT_PID 2>/dev/null" EXIT
wait
"""

with open("scripts/demo.sh", "w") as f:
    f.write(demo_content)
os.chmod("scripts/demo.sh", 0o755)

print("\n📁 Final clean structure:")
print(
    """
dronesphere/
├── start_server.py      # Main server startup script
├── start_dronesphere.py # Alternative unified starter (kept)
├── agent/              # Drone agent
├── server/             # Control server
├── web/                # Frontend (to be built)
├── shared/             # Shared resources
├── scripts/            # Utility scripts
│   ├── setup.sh       # Initial setup
│   ├── demo.sh        # Run full demo
│   ├── dev.sh         # Development mode
│   ├── status.py      # Check system status
│   ├── fix_env.py     # Fix environment
│   └── test_*.py      # Test scripts
├── docs/               # Documentation
└── tests/              # Test suites
"""
)

print("\n✅ Cleanup complete! Project structure is now clean and professional.")
print("\n🚀 To start the server: python start_server.py")
print("📊 To check status: python scripts/status.py")
