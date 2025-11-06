"""
MCP Server for Saudi Location Intelligence.
Simplified main server file with extracted components.
"""

import asyncio
import os
import uvicorn
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

# FastMCP imports
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
from starlette.applications import Starlette

# Local imports
from logging_config import get_logger
from config import config
from context import AppContext
from core.handle_manager import HandleManager
from core.session_manager import SessionManager
from core.cleanup import cleanup_expired_sessions

# Tool imports
from tools.auth_tools import register_auth_tools
from tools.geospatial import register_geospatial_tools
from tools.optimize_sales_territories import register_territory_optimization_tools
from tools.report_tools import register_territory_report_tools, register_report_analysis_tools
from tools.analysis_tools import register_natural_language_hub_analyzer_tools, register_pharmacy_report_tools

logger = get_logger(__name__)

# ===== Initialize Global Managers =====
session_manager = SessionManager()
handle_manager = HandleManager(session_manager)


# ===== FastMCP with CORS Support =====
class FastMCPWithCORS(FastMCP):
    """FastMCP server with CORS middleware for SSE transport.

    This subclass adds CORS headers to allow browser-based clients
    like the MCP Inspector to connect to the SSE endpoint.
    """

    def sse_app(self, mount_path: str | None = None) -> Starlette:
        """Override sse_app to add CORS middleware."""
        app = super().sse_app(mount_path)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify your client domains
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        return app

    def run(self, transport: str = "sse"):
        """Override run to bind to 0.0.0.0 instead of 127.0.0.1"""
        import uvicorn

        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_SERVER_PORT", str(self.settings.port)))

        if transport == "sse":
            app = self.sse_app()
            uvicorn.run(app, host=host, port=port)
        else:
            super().run(transport)


# ===== FastMCP Server =====
mcp = FastMCPWithCORS("saudi-location-intelligence", port=8001)

# Register all tools
register_auth_tools(mcp)
register_geospatial_tools(mcp)
register_territory_optimization_tools(mcp)
register_territory_report_tools(mcp)
register_natural_language_hub_analyzer_tools(mcp)
register_report_analysis_tools(mcp)
register_pharmacy_report_tools(mcp)


# ===== Resource Implementations =====
@mcp.resource("session://current")
async def get_current_session() -> str:
    """Get information about the current session."""
    ctx = mcp.get_context()
    app_ctx = ctx.request_context.lifespan_context
    session_manager = app_ctx.session_manager

    session = await session_manager.get_current_session()
    if session:
        return f"Current session: {session.session_id} (expires: {session.expires_at.isoformat()})"
    else:
        return "No active session"


@mcp.resource("config://server")
def get_server_config() -> str:
    """Get server configuration information."""
    return f"""Saudi Location Intelligence MCP Server Configuration:
- Session TTL: {config.session_ttl_hours} hours
- Storage Path: {config.temp_storage_path}
- Cleanup Interval: {config.cleanup_interval_hours} hours
- Server Name: saudi-location-intelligence
- Available Tools: 7 registered tools
- Transport Support: stdio, SSE
"""


# ===== Main Function =====
def main():
    """Main entry point for the MCP server."""
    logger.info("🇸🇦 Saudi Location Intelligence MCP Server")

    # Get host and port from environment
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8001"))

    logger.info(f"🌐 Starting SSE transport on http://{host}:{port}/sse")
    logger.info(f"🔍 Connect MCP Inspector to: http://localhost:{port}/sse")

    # Get the SSE app and run it with uvicorn
    mcp.run("sse")


if __name__ == "__main__":
    main()