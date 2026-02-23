"""
AUTONOMOUS CORTEX: MCP Interface Layer
Handles connections to local MCP servers for autonomous tool execution.
Replaces mocked tool execution with real capabilities via stdio protocol.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import subprocess
import sys

class MCPClient:
    """
    MCP (Model Context Protocol) Client
    Connects to local MCP servers via uvx for isolated execution.
    Supports: mcp-server-fetch, mcp-server-filesystem
    """
    
    def __init__(self, logger: logging.Logger = None):
        """
        Initialize MCP Client with server definitions.
        """
        self.logger = logger or logging.getLogger("MCPClient")
        
        # Define MCP servers available for autonomous operations
        self.servers = {
            "fetch": {
                "command": "uvx",
                "args": ["mcp-server-fetch"],
                "description": "Web content fetching via MCP"
            },
            "filesystem": {
                "command": "uvx", 
                "args": ["mcp-server-filesystem", "/tmp/mcp_workspace"],
                "description": "File system operations via MCP"
            }
        }
        
        self.logger.info("[MCP] Interface initialized - Zero Friction Mode")
    
    async def execute(self, server: str, tool: str, args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a tool on the specified MCP server.
        
        Args:
            server: Server name ('fetch' or 'filesystem')
            tool: Tool name to execute (e.g., 'fetch', 'read_file')
            args: Tool arguments as dictionary
            
        Returns:
            Result dictionary or None on failure
        """
        # Security: Validate server against whitelist
        if server not in self.servers:
            self.logger.error(f"[MCP] Unknown server: {server}")
            return None
        
        server_config = self.servers[server]
        self.logger.info(f"[MCP] Executing {tool} on {server_config['description']}")
        
        try:
            # Prepare MCP request payload
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool,
                    "arguments": args
                }
            }
            
            # Launch MCP server via uvx (isolated environment)
            process = await asyncio.create_subprocess_exec(
                server_config["command"],
                *server_config["args"],
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send request and read response
            request_bytes = (json.dumps(request) + "\n").encode()
            stdout, stderr = await asyncio.wait_for(
                process.communicate(request_bytes),
                timeout=30.0
            )
            
            if stderr:
                self.logger.warning(f"[MCP] Server stderr: {stderr.decode()}")
            
            # Parse response
            response = json.loads(stdout.decode().strip())
            
            if "result" in response:
                self.logger.info(f"[MCP] Tool execution successful: {tool}")
                return response["result"]
            elif "error" in response:
                self.logger.error(f"[MCP] Tool execution failed: {response['error']}")
                return None
            else:
                self.logger.warning(f"[MCP] Unexpected response format")
                return None
                
        except asyncio.TimeoutError:
            self.logger.error(f"[MCP] Tool execution timed out: {tool}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"[MCP] Failed to parse response: {e}")
            return None
        except Exception as e:
            self.logger.error(f"[MCP] Execution error: {e}")
            return None
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """
        Convenience method to fetch URL content.
        
        Args:
            url: Target URL to fetch
            
        Returns:
            HTML content or None on failure
        """
        result = await self.execute("fetch", "fetch", {"url": url})
        if result and "content" in result:
            return result["content"]
        return None
    
    async def health_check(self) -> bool:
        """
        Verify MCP infrastructure is available.
        
        Returns:
            True if MCP is operational, False otherwise
        """
        try:
            # Check if uvx is available
            process = await asyncio.create_subprocess_exec(
                "uvx", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.communicate(), timeout=5.0)
            
            if process.returncode == 0:
                self.logger.info("[MCP] Health check passed - uvx available")
                return True
            else:
                self.logger.warning("[MCP] Health check failed - uvx not available")
                return False
        except Exception as e:
            self.logger.warning(f"[MCP] Health check failed: {e}")
            return False
