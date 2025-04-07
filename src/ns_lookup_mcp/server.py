"""
Server implementation for the NS Lookup MCP Server.
"""

import subprocess
import signal
import asyncio
from typing import Annotated, Optional

from pydantic import BaseModel, Field
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    ErrorData,
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)

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

def create_server() -> Server:
    """Create and configure the NS Lookup MCP server."""
    server = Server("mcp-nslookup")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="nslookup",
                description="Performs DNS lookups using the nslookup command. Supports both forward and reverse DNS lookups.",
                inputSchema=NSLookupRequest.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="nslookup",
                description="Perform a DNS lookup using nslookup",
                arguments=[
                    PromptArgument(
                        name="hostname",
                        description="Domain name or IP address to look up",
                        required=True,
                    ),
                    PromptArgument(
                        name="server",
                        description="Optional DNS server to use",
                        required=False,
                    ),
                ],
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            args = NSLookupRequest(**arguments)
        except ValueError as e:
            raise ErrorData(code=INVALID_PARAMS, message=str(e))

        if not args.hostname:
            raise ErrorData(code=INVALID_PARAMS, message="Hostname is required")

        try:
            cmd = ["nslookup"]
            if args.server:
                cmd.append(args.server)
            cmd.append(args.hostname)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process and format the output
            lines = result.stdout.split('\n')
            formatted_lines = []
            for line in lines:
                if line.startswith('Server:'):
                    formatted_lines.append(f"DNS:\t{line.split()[-1]}")
                elif line.startswith('Name:') or line.startswith('Address:'):
                    formatted_lines.append(line)
            
            return [TextContent(type="text", text='\n'.join(formatted_lines))]
        except subprocess.CalledProcessError as e:
            raise ErrorData(
                code=INTERNAL_ERROR,
                message=f"nslookup command failed: {e.stderr}"
            )

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        if not arguments or "hostname" not in arguments:
            raise ErrorData(code=INVALID_PARAMS, message="Hostname is required")

        hostname = arguments["hostname"]
        server = arguments.get("server")

        try:
            cmd = ["nslookup"]
            if server:
                cmd.append(server)
            cmd.append(hostname)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process and format the output
            lines = result.stdout.split('\n')
            formatted_lines = []
            for line in lines:
                if line.startswith('Server:'):
                    formatted_lines.append(f"DNS:\t{line.split()[-1]}")
                elif line.startswith('Name:') or line.startswith('Address:'):
                    formatted_lines.append(line)
            
            return GetPromptResult(
                description=f"DNS lookup results for {hostname}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text='\n'.join(formatted_lines))
                    )
                ],
            )
        except subprocess.CalledProcessError as e:
            return GetPromptResult(
                description=f"Failed to perform DNS lookup for {hostname}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=str(e.stderr))
                    )
                ],
            )

    return server

async def run_server() -> None:
    """Run the NS Lookup MCP server."""
    server = create_server()
    
    # Create an event to signal shutdown
    shutdown_event = asyncio.Event()

    # Set up signal handlers
    def handle_sigint():
        shutdown_event.set()
    
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, handle_sigint)
    loop.add_signal_handler(signal.SIGTERM, handle_sigint)

    options = server.create_initialization_options()
    try:
        async with stdio_server() as (read_stream, write_stream):
            # Create a task for the server
            server_task = asyncio.create_task(
                server.run(read_stream, write_stream, options, raise_exceptions=True)
            )
            
            # Create a task for the shutdown event
            shutdown_task = asyncio.create_task(shutdown_event.wait())
            
            # Wait for either the server to complete or shutdown signal
            done, pending = await asyncio.wait(
                [server_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # If we got a shutdown signal, cancel the server task
            if shutdown_event.is_set():
                server_task.cancel()
                try:
                    await server_task
                except asyncio.CancelledError:
                    pass
    finally:
        # Clean up signal handlers
        loop.remove_signal_handler(signal.SIGINT)
        loop.remove_signal_handler(signal.SIGTERM) 