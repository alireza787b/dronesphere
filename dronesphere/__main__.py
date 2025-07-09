# dronesphere/__main__.py
"""DroneSphere package entry point - defaults to agent mode."""

import asyncio
import sys


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        from .server.main import main as server_main

        asyncio.run(server_main())
    else:
        from .agent.main import main as agent_main

        asyncio.run(agent_main())


if __name__ == "__main__":
    main()
