"""
Server implementation for the NS Lookup MCP Server using FastMCP.
"""

import subprocess
from typing import Annotated, Optional

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent

from .logging import setup_logging

# Set up logging
logger = setup_logging()

class NSLookupRequest(BaseModel):
    """Parameters for nslookup command."""
    hostname: Annotated[str, Field(description="Domain name or IP address to look up")]
    server: Annotated[
        Optional[str],
        Field(
            default=None,
            description="Specific DNS server to use for the lookup",
        ),
    ]

def run_nslookup(hostname: str, server: Optional[str] = None) -> str:
    """Execute nslookup command and format the output."""
    cmd = ["nslookup"]
    cmd.append(hostname)
    if server:
        cmd.append(server)
    
    logger.debug(f"Executing command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )
    
    # Process and format the output
    lines = result.stdout.split('\n')
    formatted_lines = []
    dns_server_info = []
    
    for line in lines:
        if line.startswith('Server:'):
            server_name = line.split()[-1]
            dns_server_info.append(f"Using DNS Server: {server_name}")
        elif line.startswith('Address:') and not dns_server_info:  # DNS server address
            addr_parts = line.split()[-1].split('#')
            addr = addr_parts[0]
            port = addr_parts[1] if len(addr_parts) > 1 else "53"
            dns_server_info.append(f"DNS Server Address: {addr} (Port: {port})")
        elif line.startswith('Name:'):
            formatted_lines.append("\nResolved Name:")
            formatted_lines.append(f"  {line.strip()}")
        elif line.startswith('Address:'):  # Result address
            formatted_lines.append(f"  {line.strip()}")
    
    return '\n'.join(dns_server_info + formatted_lines)

# Create FastMCP instance
mcp = FastMCP("NS Lookup")

@mcp.tool()
def nslookup(hostname: str, server: Optional[str] = None) -> str:
    """Performs DNS lookups using the nslookup command. Supports both forward and reverse DNS lookups."""
    logger.info(f"Performing nslookup for {hostname} with server {server}")
    try:
        return run_nslookup(hostname, server)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error occurred"
        logger.error(f"nslookup command failed: {error_msg}")
        raise ValueError(f"nslookup command failed: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise ValueError(f"Unexpected error: {str(e)}")

@mcp.prompt()
def nslookup_prompt(hostname: str, server: Optional[str] = None) -> str:
    """Create a prompt for DNS lookup results."""
    logger.info(f"Creating prompt for {hostname} with server {server}")
    try:
        result = run_nslookup(hostname, server)
        return f"DNS lookup results for {hostname}:\n\n{result}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown error occurred"
        logger.error(f"nslookup command failed: {error_msg}")
        return f"Failed to perform DNS lookup for {hostname}: {error_msg}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Failed to perform DNS lookup for {hostname}: {str(e)}"

def run_server() -> None:
    """Run the NS Lookup MCP server."""
    logger.info("Starting NS Lookup MCP server")
    mcp.run()

if __name__ == "__main__":
    run_server() 