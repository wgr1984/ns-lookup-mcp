"""
NS Lookup MCP Server package.

This package provides a Model Control Protocol (MCP) server for performing DNS lookups
using the nslookup command. It supports both forward and reverse DNS lookups.
"""

from .server import run_server

def main():
    """NS Lookup MCP Server - DNS lookup functionality for MCP"""
    import asyncio
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass  # Gracefully exit on Ctrl+C

if __name__ == "__main__":
    main() 