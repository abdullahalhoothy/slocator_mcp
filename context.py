"""Application context for MCP server."""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from core.session_manager import SessionManager
    from core.handle_manager import HandleManager


@dataclass
class AppContext:
    session_manager: "SessionManager"
    handle_manager: "HandleManager"


_app_context: Optional[AppContext] = None


def set_app_context(session_manager: "SessionManager", handle_manager: "HandleManager") -> None:
    global _app_context
    _app_context = AppContext(session_manager=session_manager, handle_manager=handle_manager)


def get_app_context(mcp: "FastMCP" = None) -> AppContext:
    if _app_context is None:
        raise RuntimeError("AppContext not initialized; call set_app_context() at server startup")
    return _app_context