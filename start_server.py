#!/usr/bin/env python3
"""
DroneSphere Server Startup Script

Usage:
    python start_server.py [--port PORT]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Start DroneSphere Server")
    parser.add_argument(
        "--port", type=int, default=8001, help="Server port (default: 8001)"
    )
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
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(args.port),
        "--reload",
    ]

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
