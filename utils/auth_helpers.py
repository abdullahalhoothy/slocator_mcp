"""
Authentication helpers for MCP tools.

Centralises the repeated auth + session check that every tool
must perform before calling the backend.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.session_manager import SessionManager
    from models import SessionInfo


async def require_auth(
    session_manager: "SessionManager",
) -> "tuple[SessionInfo, str, str] | str":
    """
    Ensure the caller is authenticated and has a valid session.

    Returns either a ``(session, user_id, id_token)`` tuple ready for use,
    or a human-readable error string that the tool can return directly to
    the MCP client.

    Usage in a tool::

        result = await require_auth(session_manager)
        if isinstance(result, str):
            return result          # not authenticated — surface the error
        session, user_id, id_token = result
    """
    user_id, id_token = await session_manager.get_valid_id_token()
    if not id_token or not user_id:
        return "Not logged in. Please use the `user_login` tool first."

    session = await session_manager.get_current_session()
    if not session:
        session = await session_manager.create_session()

    return session, user_id, id_token