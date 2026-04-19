"""
Session management for MCP server.
Handles session creation, authentication, and token refresh.
"""

import asyncio
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from models import SessionInfo
from utils import use_json, convert_to_serializable, post_to_backend_no_auth, BackendError
from logging_config import get_logger, setup_session_logging, end_session_logging
from config import config

logger = get_logger(__name__)


class SessionManager:
    """Manages user sessions including authentication and token management."""

    def __init__(self):
        self.base_path = Path(config.sessions_path)
        self.current_session: Optional[SessionInfo] = None
        logger.info(
            "Session manager initialized with base path: %s", self.base_path
        )

    async def create_session(self) -> SessionInfo:
        """Create a new session with dedicated logging."""
        session_id = str(uuid.uuid4())[:8]
        session_path = self.base_path / session_id
        session_path.mkdir(parents=True, exist_ok=True)

        session_info = SessionInfo(
            session_id=session_id,
            expires_at=datetime.now() + timedelta(hours=config.session_ttl_hours),
        )

        # Store session metadata
        metadata_path = str(session_path / "session_metadata.json")
        session_data = convert_to_serializable(session_info.model_dump())
        await use_json(metadata_path, "w", session_data)

        setup_session_logging(session_id, session_path)

        self.current_session = session_info
        logger.info(
            "Created new session: %s (expires: %s)", session_id, session_info.expires_at
        )

        return session_info

    async def cleanup_session(self, session_id: str):
        """Clean up session and its logging."""
        end_session_logging(session_id)

        session_path = self.base_path / session_id
        if session_path.exists():
            await asyncio.to_thread(shutil.rmtree, session_path)
            logger.info("Cleaned up expired session: %s", session_id)

    async def get_current_session(self) -> Optional[SessionInfo]:
        """Get current session, loading from disk if needed."""

        # If we have session in memory, return it
        if self.current_session:
            return self.current_session

        # If no session in memory, try to load from disk
        logger.info("No session in memory, scanning disk for valid sessions...")

        try:
            if not self.base_path.exists():
                return None

            # Find most recent valid session
            valid_sessions = []

            for session_dir in self.base_path.iterdir():
                if not session_dir.is_dir():
                    continue

                metadata_path = session_dir / "session_metadata.json"
                if metadata_path.exists():
                    try:
                        metadata = await use_json(str(metadata_path), "r")
                        if metadata:
                            session_info = SessionInfo(**metadata)
                            # Check if session is still valid
                            if datetime.now() < session_info.expires_at:
                                valid_sessions.append(
                                    (session_info, session_info.created_at)
                                )
                    except Exception as e:
                        logger.warning(
                            "Failed to load session %s: %s", session_dir.name, e
                        )

            if valid_sessions:
                # Load most recent valid session
                valid_sessions.sort(key=lambda x: x[1], reverse=True)
                session_info = valid_sessions[0][0]

                # Restore session to memory
                self.current_session = session_info
                setup_session_logging(
                    session_info.session_id, self.base_path / session_info.session_id
                )

                logger.info("Loaded session from disk: %s", session_info.session_id)
                return session_info
            else:
                logger.info("No valid sessions found on disk")
                return None

        except Exception as e:
            logger.error(f"Failed to load session from disk: {e}")
            return None

    async def load_session(self, session_id: str) -> Optional[SessionInfo]:
        """Load existing session from metadata file."""
        session_path = self.base_path / session_id
        metadata_path = str(session_path / "session_metadata.json")

        session_data = await use_json(metadata_path, "r")
        if session_data:
            session_info = SessionInfo(**session_data)
            # Check if session is still valid
            if datetime.now() < session_info.expires_at:
                self.current_session = session_info
                logger.info("Loaded existing session: %s", session_id)
                return session_info
            else:
                logger.info("Session %s has expired", session_id)
                await self.cleanup_session(session_id)
        return None

    async def update_session_auth(
        self,
        session_id: str,
        user_id: str,
        id_token: str,
        refresh_token: str,
        expires_in: int,
    ):
        """Updates the session with new authentication tokens."""
        session_path = self.base_path / session_id
        metadata_path = str(session_path / "session_metadata.json")

        metadata = await use_json(metadata_path, "r")
        if not metadata:
            logger.error(
                "Could not find session metadata for %s to update auth.", session_id
            )
            return

        metadata["user_id"] = user_id
        metadata["id_token"] = id_token
        metadata["refresh_token"] = refresh_token
        metadata["token_expires_at"] = (
            datetime.now() + timedelta(seconds=expires_in - 60)
        ).isoformat()  # -60s buffer

        await use_json(metadata_path, "w", metadata)

        # Update the in-memory session object as well
        if (
            self.current_session
            and self.current_session.session_id == session_id
        ):
            self.current_session.user_id = user_id
            self.current_session.id_token = id_token
            self.current_session.refresh_token = refresh_token
            self.current_session.token_expires_at = datetime.fromisoformat(
                metadata["token_expires_at"]
            )

        logger.info(
            "Updated auth tokens for user %s in session %s", user_id, session_id
        )

    async def get_valid_id_token(self) -> tuple[Optional[str], Optional[str]]:
        """
        Gets a valid ID token for the current session, refreshing it if necessary.
        Returns a tuple of (user_id, id_token).
        """
        session = await self.get_current_session()
        if not session or not session.refresh_token or not session.user_id:
            return None, None  # No user logged in

        # Check if token is expired or close to expiring
        if (
            not session.id_token
            or not session.token_expires_at
            or datetime.now() >= session.token_expires_at
        ):
            logger.info("Token expired for user %s. Refreshing...", session.user_id)
            try:
                token_data = await post_to_backend_no_auth(
                    config.endpoints.refresh_token,
                    {"grant_type": "refresh_token", "refresh_token": session.refresh_token},
                    "refreshing token",
                )
                await self.update_session_auth(
                    session.session_id,
                    token_data["localId"],
                    token_data["idToken"],
                    token_data["refreshToken"],
                    int(token_data["expiresIn"]),
                )
                logger.info("Successfully refreshed token for user %s.", session.user_id)
                # Important: return the newly fetched token, not the old one from session
                return token_data["localId"], token_data["idToken"]
            except BackendError as e:
                logger.error("Failed to refresh token: %s %s", e.status, e.text)
                return None, None
            except Exception as e:
                logger.error("Exception during token refresh: %s", e)
                return None, None

        # Token is still valid, return it
        return session.user_id, session.id_token