#!/usr/bin/env python3
# scripts/fix_env.py
"""Fix .env file format issues."""

import os


def fix_env_file():
    """Fix common .env file issues."""

    env_path = ".env"

    # Read current .env
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()
    else:
        print("Creating .env from .env.example...")
        with open(".env.example") as f:
            lines = f.readlines()

    # Fix common issues
    fixed_lines = []
    for line in lines:
        # Fix CORS_ORIGINS format
        if (
            line.startswith("CORS_ORIGINS=")
            and "http://localhost:3010" in line
            and "[" not in line
        ):
            fixed_lines.append('CORS_ORIGINS=["http://localhost:3010"]\n')
        # Fix port 8000 to 8001
        elif line.strip() == "SERVER_PORT=8000":
            fixed_lines.append("SERVER_PORT=8001\n")
        # Fix agent URL
        elif "ws://localhost:8000/ws/agent" in line:
            fixed_lines.append(line.replace("8000", "8001"))
        else:
            fixed_lines.append(line)

    # Add AGENT_SERVER_URL if missing
    env_content = "".join(fixed_lines)
    if "AGENT_SERVER_URL" not in env_content:
        fixed_lines.insert(3, "AGENT_SERVER_URL=ws://localhost:8001/ws/agent\n")

    # Write fixed .env
    with open(env_path, "w") as f:
        f.writelines(fixed_lines)

    print("✅ Fixed .env file")
    print("\nKey settings:")
    for line in fixed_lines:
        if any(
            key in line for key in ["SERVER_PORT", "CORS_ORIGINS", "AGENT_SERVER_URL"]
        ):
            print(f"  {line.strip()}")


if __name__ == "__main__":
    fix_env_file()
