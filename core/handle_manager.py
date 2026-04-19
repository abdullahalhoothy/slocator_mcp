"""
Handle management for MCP server.
Manages data storage, retrieval, and cleanup operations.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

from utils import use_json, convert_to_serializable
from logging_config import get_logger

logger = get_logger(__name__)


class HandleManager:
    """Manages data handles for storing and retrieving session data."""

    def __init__(self, session_manager):
        self.session_manager = session_manager
        logger.info("Handle manager initialized")

    async def store_data(self, data_type: str, location: str, data: Any) -> str:
        """Store data and return simple handle."""
        session = await self.session_manager.get_current_session()

        # Create session if none exists
        if not session:
            logger.info("STORE: No active session found, creating new session")
            session = await self.session_manager.create_session()

        session_path = self.session_manager.base_path / session.session_id
        session_path.mkdir(parents=True, exist_ok=True)
        session_id = session.session_id

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        handle = f"{data_type}_{location}_{timestamp}_{session_id}.json"
        file_path = str(session_path / handle)

        logger.info("STORE: Saving %s data for %s to %s", data_type, location, handle)

        # Convert and store data
        serializable_data = convert_to_serializable(data)
        await use_json(file_path, "w", serializable_data)

        # Touch session to update access time for cleanup
        await self._touch_session(session.session_id)

        logger.info("STORE: Successfully stored data with handle: %s", handle)
        return handle

    async def read_data(self, handle: str) -> Optional[Dict]:
        """Read data using simple handle."""
        session = await self.session_manager.get_current_session()

        # Check if session exists
        if not session:
            logger.warning("READ: No active session found, cannot read data")
            return None

        session_path = self.session_manager.base_path / session.session_id
        file_path = str(session_path / handle)

        logger.info("READ: Loading data from handle: %s", handle)

        if os.path.exists(file_path):
            data = await use_json(file_path, "r")
            if data:
                # Update session access time
                await self._touch_session(session.session_id)
                logger.info("READ: Successfully loaded data from %s", handle)
                return data

        logger.warning("READ: No data found for handle: %s", handle)
        return None

    async def list_session_data(
        self, session_id: str = None
    ) -> list[Dict[str, Any]]:
        """List all data files in a session."""
        if not session_id:
            session = await self.session_manager.get_current_session()
            session_id = session.session_id if session else None

        if not session_id:
            return []

        session_path = self.session_manager.base_path / session_id

        if not session_path.exists():
            return []

        files = []
        for file_path in session_path.glob("*.json"):
            if file_path.name in ["session_info.json", "session_metadata.json"]:
                continue

            stat = file_path.stat()

            # Parse filename to extract data_type and location
            name_parts = file_path.stem.split("_", 1)
            data_type = name_parts[0] if name_parts else "unknown"
            location = name_parts[1] if len(name_parts) > 1 else "unknown"

            files.append(
                {
                    "handle": file_path.name,
                    "data_type": data_type,
                    "location": location,
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime),
                }
            )

        return sorted(files, key=lambda x: x["modified_at"], reverse=True)

    async def remove_data(self, handle: str, session_id: str = None) -> bool:
        """Remove specific data file."""
        if not session_id:
            session = await self.session_manager.get_current_session()
            session_id = session.session_id if session else None

        if not session_id:
            return False

        session_path = self.session_manager.base_path / session_id
        file_path = session_path / handle

        try:
            if file_path.exists():
                file_path.unlink()
                logger.info("REMOVE: Deleted data file: %s", handle)
                return True
            return False
        except Exception as e:
            logger.error("REMOVE: Failed to delete %s: %s", handle, e)
            return False

    # ===================== CLEANUP METHODS =====================

    async def cleanup_expired_sessions(
        self, max_age_hours: int = 24
    ) -> Dict[str, Any]:
        """Remove sessions older than max_age_hours."""
        logger.info("CLEANUP: Starting cleanup of sessions older than %s hours", max_age_hours)

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        sessions_dir = self.session_manager.base_path

        if not sessions_dir.exists():
            return {"cleaned": 0, "freed_mb": 0, "errors": []}

        cleaned_count = 0
        freed_bytes = 0
        errors = []

        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                # Check last access time
                last_access = await self._get_session_last_access(session_dir.name)

                if last_access and last_access < cutoff_time:
                    # Calculate size before deletion
                    size = await self._calculate_directory_size(session_dir)

                    # Remove entire session directory
                    await self._remove_directory_recursive(session_dir)

                    cleaned_count += 1
                    freed_bytes += size
                    logger.info("CLEANUP: Removed expired session %s", session_dir.name)

            except Exception as e:
                error_msg = f"Failed to cleanup session {session_dir.name}: {e}"
                errors.append(error_msg)
                logger.error("CLEANUP: %s", error_msg)

        result = {
            "cleaned": cleaned_count,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors,
        }

        logger.info("CLEANUP: Completed - %s", result)
        return result

    async def cleanup_large_sessions(self, max_size_mb: int = 100) -> Dict[str, Any]:
        """Remove sessions larger than max_size_mb."""
        logger.info("CLEANUP: Starting cleanup of sessions larger than %sMB", max_size_mb)

        sessions_dir = self.session_manager.base_path
        max_size_bytes = max_size_mb * 1024 * 1024

        if not sessions_dir.exists():
            return {"cleaned": 0, "freed_mb": 0, "errors": []}

        cleaned_count = 0
        freed_bytes = 0
        errors = []

        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                size = await self._calculate_directory_size(session_dir)

                if size > max_size_bytes:
                    await self._remove_directory_recursive(session_dir)
                    cleaned_count += 1
                    freed_bytes += size
                    logger.info(
                        "CLEANUP: Removed large session %s (%.1fMB)",
                        session_dir.name,
                        size / 1024 / 1024,
                    )

            except Exception as e:
                error_msg = f"Failed to cleanup large session {session_dir.name}: {e}"
                errors.append(error_msg)
                logger.error("CLEANUP: %s", error_msg)

        result = {
            "cleaned": cleaned_count,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors,
        }

        logger.info("CLEANUP: Completed large session cleanup - %s", result)
        return result

    async def cleanup_oldest_sessions(self, keep_count: int = 50) -> Dict[str, Any]:
        """Keep only the newest N sessions, remove the rest."""
        logger.info("CLEANUP: Keeping only %s newest sessions", keep_count)

        sessions_dir = self.session_manager.base_path

        if not sessions_dir.exists():
            return {"cleaned": 0, "freed_mb": 0, "errors": []}

        # Get all sessions with their last access times
        sessions = []
        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                last_access = await self._get_session_last_access(session_dir.name)
                sessions.append((session_dir, last_access or datetime.min))
            except Exception as e:
                logger.error("CLEANUP: Error getting session info for %s: %s", session_dir.name, e)

        # Sort by last access (newest first) and keep only the top N
        sessions.sort(key=lambda x: x[1], reverse=True)
        sessions_to_remove = sessions[keep_count:]

        cleaned_count = 0
        freed_bytes = 0
        errors = []

        for session_dir, _ in sessions_to_remove:
            try:
                size = await self._calculate_directory_size(session_dir)
                await self._remove_directory_recursive(session_dir)
                cleaned_count += 1
                freed_bytes += size
                logger.info("CLEANUP: Removed old session %s", session_dir.name)
            except Exception as e:
                error_msg = f"Failed to cleanup old session {session_dir.name}: {e}"
                errors.append(error_msg)
                logger.error("CLEANUP: %s", error_msg)

        result = {
            "cleaned": cleaned_count,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "errors": errors,
        }

        logger.info("CLEANUP: Completed oldest session cleanup - %s", result)
        return result

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        sessions_dir = self.session_manager.base_path

        if not sessions_dir.exists():
            return {
                "total_sessions": 0,
                "total_size_mb": 0,
                "total_files": 0,
                "largest_session_mb": 0,
                "oldest_session": None,
                "newest_session": None,
            }

        total_size = 0
        total_files = 0
        session_count = 0
        largest_size = 0
        oldest_time = datetime.max
        newest_time = datetime.min

        for session_dir in sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session_count += 1

            try:
                # Calculate session size and file count
                size, files = await self._calculate_directory_stats(session_dir)
                total_size += size
                total_files += files

                if size > largest_size:
                    largest_size = size

                # Get session times
                last_access = await self._get_session_last_access(session_dir.name)
                if last_access:
                    if last_access < oldest_time:
                        oldest_time = last_access
                    if last_access > newest_time:
                        newest_time = last_access

            except Exception as e:
                logger.error(
                    f"STATS: Error processing session {session_dir.name}: {e}"
                )

        return {
            "total_sessions": session_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": total_files,
            "largest_session_mb": round(largest_size / (1024 * 1024), 2),
            "oldest_session": oldest_time if oldest_time != datetime.max else None,
            "newest_session": newest_time if newest_time != datetime.min else None,
        }

    # ===================== HELPER METHODS =====================

    async def _touch_session(self, session_id: str):
        """Update session access time."""
        session_path = self.session_manager.base_path / session_id
        info_path = session_path / "session_info.json"

        try:
            info = {
                "session_id": session_id,
                "last_access": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat(),
            }

            # If session info exists, preserve created_at
            if info_path.exists():
                existing = await use_json(str(info_path), "r")
                if existing and "created_at" in existing:
                    info["created_at"] = existing["created_at"]

            await use_json(str(info_path), "w", info)
        except Exception as e:
            logger.error("TOUCH: Failed to update session %s: %s", session_id, e)

    async def _get_session_last_access(self, session_id: str) -> Optional[datetime]:
        """Get last access time for a session."""
        session_path = self.session_manager.base_path / session_id
        info_path = session_path / "session_info.json"

        try:
            if info_path.exists():
                info = await use_json(str(info_path), "r")
                if info and "last_access" in info:
                    return datetime.fromisoformat(info["last_access"])

            # Fallback to directory modification time
            if session_path.exists():
                return datetime.fromtimestamp(session_path.stat().st_mtime)

        except Exception as e:
            logger.error("ACCESS_TIME: Error getting session time for %s: %s", session_id, e)

        return None

    async def _calculate_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error("SIZE: Error calculating size for %s: %s", directory, e)
        return total_size

    async def _calculate_directory_stats(self, directory: Path) -> Tuple[int, int]:
        """Calculate total size and file count for directory."""
        total_size = 0
        file_count = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        except Exception as e:
            logger.error("STATS: Error calculating stats for %s: %s", directory, e)
        return total_size, file_count

    async def _remove_directory_recursive(self, directory: Path):
        """Safely remove directory and all contents."""
        try:
            await asyncio.to_thread(shutil.rmtree, directory)
        except Exception as e:
            logger.error("REMOVE: Failed to remove directory %s: %s", directory, e)
            raise