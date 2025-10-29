#!/usr/bin/env python3
"""
bigtorig-mcp-hub Server

A simple MCP server providing access to Hostinger infrastructure services.
This is the initial version without any tools - to be expanded later.
"""

from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("bigtorig-mcp-hub")


@mcp.tool()
def health_check() -> dict:
    """
    Check if the MCP server is running and healthy.
    
    Returns:
        dict: Status information about the server
    """
    return {
        "status": "healthy",
        "service": "bigtorig-mcp-hub",
        "version": "0.1.0",
        "message": "MCP hub is operational"
    }


@mcp.tool()
def list_services() -> dict:
    """
    List all available infrastructure services.
    
    Returns:
        dict: Information about available services
    """
    services = {
        "postgres": {
            "name": "Supabase Postgres",
            "endpoint": "db:5432",
            "status": "available",
            "tools": ["Coming soon"]
        },
        "qdrant": {
            "name": "Qdrant Vector Database",
            "endpoint": "qdrant:6333",
            "status": "available",
            "tools": ["Coming soon"]
        },
        "neo4j": {
            "name": "Neo4j Graph Database",
            "endpoint": "neo4j:7687",
            "status": "available",
            "tools": ["Coming soon"]
        }
    }
    
    return {
        "total_services": len(services),
        "services": services
    }


if __name__ == "__main__":
    # Run the MCP server
    # By default, FastMCP runs on stdio for local use
    # For HTTP access, use: mcp.run(transport="sse", port=8000)
    
    print("🔌 bigtorig-mcp-hub starting...")
    print("📡 Available tools: health_check, list_services")
    print("🚀 Ready to accept connections")
    
    # Run with SSE transport for HTTP access
    mcp.run(transport="sse", port=8000, host="0.0.0.0")
