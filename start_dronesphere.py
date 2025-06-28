#!/usr/bin/env python3
# start_dronesphere.py - Main startup script for DroneSphere

import os
import subprocess
import sys
import time
from pathlib import Path

# Colors
G = "\033[92m"  # Green
R = "\033[91m"  # Red
Y = "\033[93m"  # Yellow
B = "\033[94m"  # Blue
NC = "\033[0m"  # No Color


def print_header():
    print(f"\n{B}╔═══════════════════════════════════════╗{NC}")
    print(f"{B}║        DroneSphere Control System     ║{NC}")
    print(f"{B}╚═══════════════════════════════════════╝{NC}\n")


def check_environment():
    """Check and setup environment."""
    root = Path(__file__).parent
    os.chdir(root)

    # Check .env
    if not Path(".env").exists():
        print(f"{Y}Setting up environment...{NC}")
        subprocess.run(["cp", ".env.example", ".env"])
        subprocess.run([sys.executable, "scripts/fix_env.py"])

    # Load environment
    from dotenv import load_dotenv

    load_dotenv()

    return os.getenv("SERVER_PORT", "8001")


def kill_port(port):
    """Kill process on port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], capture_output=True, text=True
        )
        if result.stdout.strip():
            print(f"{Y}Killing existing process on port {port}...{NC}")
            subprocess.run(["kill", "-9", result.stdout.strip()])
            time.sleep(1)
    except:
        pass


def start_server(port):
    """Start the server."""
    print(f"\n{G}Starting Server on port {port}...{NC}")
    print(f"API Documentation: http://localhost:{port}/docs")
    print(f"Health Check: http://localhost:{port}/health")
    print(f"\n{Y}Press Ctrl+C to stop{NC}\n")
    print("-" * 50)

    # Setup Python path
    server_src = Path("server/src").absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{server_src}:{env.get('PYTHONPATH', '')}"

    # Run from server directory
    os.chdir("server")

    # Start uvicorn
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        port,
        "--reload",
        "--reload-dir",
        "src",
    ]

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print(f"\n{Y}Server stopped.{NC}")


def main():
    """Main entry point."""
    print_header()

    # Check Python version
    if sys.version_info < (3, 10):
        print(f"{R}Error: Python 3.10+ required{NC}")
        sys.exit(1)

    # Setup environment
    port = check_environment()

    # Kill existing process
    kill_port(port)

    # Start server
    start_server(port)


if __name__ == "__main__":
    main()
