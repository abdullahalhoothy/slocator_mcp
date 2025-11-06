"""
Application context for MCP server.
Provides type-safe context for lifespan management.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Use forward references to avoid circular imports
if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from core.session_manager import SessionManager
    from core.handle_manager import HandleManager


@dataclass
class AppContext:
    """
    Application context for lifespan management.
    This is defined here to be importable by both the server and tools
    without creating a circular dependency.
    """

    session_manager: "SessionManager"
    handle_manager: "HandleManager"


def get_app_context(mcp: "FastMCP") -> AppContext:
    """
    A typed helper to retrieve the specific AppContext from the global managers.
    This provides full IntelliSense for session_manager and handle_manager.
    """
    from mcp_server import session_manager, handle_manager

    return AppContext(session_manager=session_manager, handle_manager=handle_manager)