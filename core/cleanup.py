"""Background cleanup task for expired and oversized sessions."""

import asyncio

from config import config
from logging_config import get_logger

logger = get_logger(__name__)


async def cleanup_expired_sessions(handle_manager):
    logger.info("Background session cleanup task started")

    while True:
        try:
            logger.info("Starting automated cleanup cycle...")

            expired_stats = await handle_manager.cleanup_expired_sessions(
                max_age_hours=config.session.ttl_hours
            )
            large_stats = await handle_manager.cleanup_large_sessions(
                max_size_mb=config.cleanup.max_session_size_mb
            )
            storage_stats = await handle_manager.get_storage_stats()

            if storage_stats["total_size_mb"] > config.cleanup.max_total_size_mb:
                oldest_stats = await handle_manager.cleanup_oldest_sessions(
                    keep_count=config.cleanup.keep_session_count
                )
                logger.info("Storage cleanup: %s", oldest_stats)

            total_cleaned = expired_stats["cleaned"] + large_stats["cleaned"]
            total_freed = expired_stats["freed_mb"] + large_stats["freed_mb"]

            if total_cleaned > 0:
                logger.info(
                    "Cleanup completed: %s sessions removed, %.1fMB freed. Storage stats: %s",
                    total_cleaned, total_freed, storage_stats,
                )
            else:
                logger.info("Cleanup completed: No sessions removed. Storage stats: %s", storage_stats)

            all_errors = expired_stats["errors"] + large_stats["errors"]
            if all_errors:
                logger.warning("Cleanup errors: %s", all_errors)

            await asyncio.sleep(config.cleanup.interval_hours * 3600)

        except asyncio.CancelledError:
            logger.info("Background session cleanup task cancelled")
            break
        except Exception:
            logger.exception("Error in session cleanup")
            await asyncio.sleep(config.cleanup.retry_interval_seconds)