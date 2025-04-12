"""
NS Lookup MCP Server package.

This package provides a Model Control Protocol (MCP) server for performing DNS lookups
using the nslookup command. It supports both forward and reverse DNS lookups.
"""

import asyncio
import sys
from .server import run_server

def main() -> int:
    """Run the NS Lookup MCP server."""
    try:
        asyncio.run(run_server())
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        if "TaskGroup" in str(e):
            return 0  # Ignore task group errors during shutdown
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 