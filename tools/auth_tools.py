import asyncio
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from context import get_app_context
from config import config
from utils import to_json_string_async, post_to_backend_no_auth, BackendError
from logging_config import get_logger

logger = get_logger(__name__)


def register_auth_tools(mcp: FastMCP):
    """Registers authentication-related tools with the MCP server."""

    logger.info("Registering authentication tools with MCP server")

    @mcp.tool()
    async def user_login(
        email: str = Field(description="The user's email address."),
        password: str = Field(description="The user's password.", sensitive=True),
    ) -> str:
        """
        Logs the user in to access their personal data and purchases.
        This must be done once per session to use other tools.
        """
        try:
            app_ctx = get_app_context(mcp)
            session_manager = app_ctx.session_manager

            session = await session_manager.get_current_session()
            if not session:
                session = await session_manager.create_session()

            logger.info("Attempting login for user %s", email)

            try:
                login_data = await post_to_backend_no_auth(
                    config.backend.endpoints.login,
                    {"email": email, "password": password},
                    "login request from mcp server",
                )
            except BackendError as e:
                logger.warning("Login failed for %s: %s", email, e.text)
                return f"Login failed. Please check your credentials. (Status: {e.status})"

            if not login_data:
                return "Login failed: The server response was malformed."

            await session_manager.update_session_auth(
                session.session_id,
                login_data["localId"],
                login_data["idToken"],
                login_data["refreshToken"],
                int(login_data["expiresIn"]),
            )

            logger.info("Successfully logged in user %s (%s)", email, login_data["localId"])
            return f"✅ Login successful for {login_data.get('email', email)}! You can now access your personalized data."

        except Exception:
            logger.exception("An unexpected error occurred during the login process.")
            return "An internal error occurred during login. Please try again later."

    @mcp.tool(
        name="list_stored_data",
        description="List all stored data files in your current session",
    )
    async def list_stored_data() -> str:
        """List all data files stored in the current session."""
        try:
            app_ctx = get_app_context(mcp)
            session_manager = app_ctx.session_manager
            handle_manager = app_ctx.handle_manager

            session = await session_manager.get_current_session()
            if not session:
                return "❌ No active session found."

            files = await handle_manager.list_session_data(session.session_id)

            if not files:
                return "📂 No data files found in current session."

            result = "📂 **Stored Data Files**:\n\n"
            for file_info in files:
                result += f"• **{file_info['handle']}** ({file_info['data_type']} - {file_info['location']})\n"
                result += f"  Size: {file_info['size_bytes']:,} bytes | Modified: {file_info['modified_at']}\n\n"

            return result

        except Exception as e:
            logger.exception("Error listing stored data")
            return f"❌ Error listing data: {str(e)}"

    @mcp.tool()
    async def get_data_from_handle(
        handle: str = Field(
            description="The data handle of the file to inspect (e.g., 'territory_optimization_riyadh_...json')."
        ),
    ) -> str:
        """Retrieves and displays the raw, pretty-printed JSON content of a stored data file."""
        try:
            app_ctx = get_app_context(mcp)
            session_manager = app_ctx.session_manager
            handle_manager = app_ctx.handle_manager

            session = await session_manager.get_current_session()
            if not session:
                return "❌ No active session found."

            data = await handle_manager.read_data(handle)
            if data is None:
                return f"❌ Error: No data found for handle `{handle}`."

            pretty_json = await to_json_string_async(data, indent=2)
            return f"📄 **Content of data handle `{handle}`:**\n\n```json\n{pretty_json}\n```"

        except Exception as e:
            logger.exception("Error retrieving data from handle: %s", handle)
            return f"❌ An unexpected error occurred while reading handle `{handle}`: {str(e)}"

    @mcp.tool()
    async def get_current_session_logs(lines: int = 50) -> str:
        """
        Get recent logs from your current session for debugging.
        Shows what happened during your login, tool calls, and other activities.
        """
        try:
            app_ctx = get_app_context(mcp)
            session_manager = app_ctx.session_manager

            session = await session_manager.get_current_session()
            if not session:
                return "❌ No active session found"

            session_id = session.session_id
            session_path: Path = session_manager.base_path / session_id
            log_files = list(session_path.glob(f"session_{session_id}_*.log"))

            if not log_files:
                return f"📂 No log file found for session {session_id}"

            current_log_file = max(log_files, key=lambda f: f.stat().st_mtime)

            # Use asyncio.to_thread to avoid blocking the event loop on file I/O
            all_lines = await asyncio.to_thread(
                lambda: current_log_file.read_text(encoding="utf-8").splitlines(keepends=True)
            )
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            return (
                f"📋 **Your Session ({session_id}) - Recent {len(recent_lines)} log entries:**\n\n"
                + "".join(recent_lines)
            )

        except Exception as e:
            logger.exception("Error reading current session logs")
            return f"❌ Error reading session logs: {str(e)}"