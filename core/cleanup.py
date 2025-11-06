"""
Background cleanup task for MCP server.
Manages periodic session cleanup operations.
"""

import asyncio
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from logging_config import get_logger
from config import config
from core.handle_manager import HandleManager
from core.session_manager import SessionManager

logger = get_logger(__name__)


async def cleanup_expired_sessions(handle_manager):
    """
    Periodic cleanup of expired sessions using HandleManager.
    Runs continuously in background until cancelled.
    """
    logger.info("Background session cleanup task started")

    while True:
        try:
            logger.info("Starting automated cleanup cycle...")

            # Clean expired sessions (older than configured TTL)
            expired_stats = await handle_manager.cleanup_expired_sessions(
                max_age_hours=config.session_ttl_hours or 24
            )

            # Clean large sessions (over 100MB)
            large_stats = await handle_manager.cleanup_large_sessions(max_size_mb=100)

            # Get storage statistics
            storage_stats = await handle_manager.get_storage_stats()

            # If total storage is too high, clean oldest sessions
            if storage_stats["total_size_mb"] > 500:  # Over 500MB total
                oldest_stats = await handle_manager.cleanup_oldest_sessions(
                    keep_count=50  # Keep only 50 newest sessions
                )
                logger.info(f"Storage cleanup: {oldest_stats}")

            # Log cleanup results
            total_cleaned = expired_stats["cleaned"] + large_stats["cleaned"]
            total_freed = expired_stats["freed_mb"] + large_stats["freed_mb"]

            if total_cleaned > 0:
                logger.info(
                    f"Cleanup completed: {total_cleaned} sessions removed, "
                    f"{total_freed:.1f}MB freed. Storage stats: {storage_stats}"
                )
            else:
                logger.info(
                    f"Cleanup completed: No sessions removed. "
                    f"Storage stats: {storage_stats}"
                )

            # Log any errors
            all_errors = expired_stats["errors"] + large_stats["errors"]
            if all_errors:
                logger.warning(f"Cleanup errors: {all_errors}")

            # Sleep for cleanup interval
            await asyncio.sleep(config.cleanup_interval_hours * 3600)

        except asyncio.CancelledError:
            logger.info("Background session cleanup task cancelled")
            break  # Exit the loop when cancelled
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
            logger.exception("Full cleanup error details:")
            await asyncio.sleep(300)  # Sleep 5 minutes on error