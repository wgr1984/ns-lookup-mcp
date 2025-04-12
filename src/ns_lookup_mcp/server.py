"""
Server implementation for the NS Lookup MCP Server.
"""

import subprocess
import sys
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

def create_server() -> Server:
    """Create and configure the NS Lookup MCP server."""
    server = Server("mcp-nslookup")
    logger.info("Creating NS Lookup MCP server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        logger.debug("Listing available tools")
        return [
            Tool(
                name="nslookup",
                description="Performs DNS lookups using the nslookup command. Supports both forward and reverse DNS lookups.",
                inputSchema=NSLookupRequest.model_json_schema(),
            )
        ]

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        logger.debug("Listing available prompts")
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
        logger.info(f"Calling tool {name} with arguments: {arguments}")
        try:
            args = NSLookupRequest(**arguments)
        except ValueError as e:
            logger.error(f"Invalid arguments: {e}")
            raise ErrorData(code=INVALID_PARAMS, message=str(e))

        if not args.hostname:
            logger.error("Hostname is required")
            raise ErrorData(code=INVALID_PARAMS, message="Hostname is required")

        try:
            cmd = ["nslookup"]
            if args.server:
                cmd.append(args.server)
            cmd.append(args.hostname)
            
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
            for line in lines:
                if line.startswith('Server:'):
                    formatted_lines.append(f"DNS:\t{line.split()[-1]}")
                elif line.startswith('Name:') or line.startswith('Address:'):
                    formatted_lines.append(line)
            
            logger.info(f"Successfully looked up {args.hostname}")
            return [TextContent(type="text", text='\n'.join(formatted_lines))]
        except subprocess.CalledProcessError as e:
            logger.error(f"nslookup command failed: {e.stderr}")
            raise ErrorData(
                code=INTERNAL_ERROR,
                message=f"nslookup command failed: {e.stderr}"
            )

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        logger.info(f"Getting prompt {name} with arguments: {arguments}")
        if not arguments or "hostname" not in arguments:
            logger.error("Hostname is required")
            raise ErrorData(code=INVALID_PARAMS, message="Hostname is required")

        hostname = arguments["hostname"]
        server = arguments.get("server")

        try:
            cmd = ["nslookup"]
            if server:
                cmd.append(server)
            cmd.append(hostname)
            
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
            for line in lines:
                if line.startswith('Server:'):
                    formatted_lines.append(f"DNS:\t{line.split()[-1]}")
                elif line.startswith('Name:') or line.startswith('Address:'):
                    formatted_lines.append(line)
            
            if not formatted_lines:
                logger.warning(f"No DNS records found for {hostname}")
                return GetPromptResult(
                    description=f"No DNS records found for {hostname}",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(type="text", text="No DNS records found")
                        )
                    ],
                )
            
            logger.info(f"Successfully looked up {hostname}")
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
            error_msg = e.stderr.strip() if e.stderr else "Unknown error occurred"
            logger.error(f"nslookup command failed: {error_msg}")
            return GetPromptResult(
                description=f"Failed to perform DNS lookup for {hostname}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=f"Error: {error_msg}")
                    )
                ],
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return GetPromptResult(
                description=f"Failed to perform DNS lookup for {hostname}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=f"Error: {str(e)}")
                    )
                ],
            )

    return server

async def run_server() -> None:
    """Run the NS Lookup MCP server."""
    logger.info("Starting NS Lookup MCP server")
    server = create_server()
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
    logger.info("NS Lookup MCP server stopped") 