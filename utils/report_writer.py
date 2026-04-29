"""Single async report-saving helper used by all tools that produce report files."""

import asyncio
import os
from datetime import datetime
from typing import Optional

from config import config
from logging_config import get_logger

logger = get_logger(__name__)


def _safe_name(name: str) -> str:
    return "".join(c for c in name.replace(" ", "_") if c.isalnum() or c in "_-")


async def save_report(
    content: str,
    name: str,
    suffix: str,
    ext: str = "md",
    subdir: Optional[str] = None,
) -> str:
    base = config.paths.reports_dir
    if subdir:
        base = os.path.join(base, subdir)
    os.makedirs(base, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_name(name)}_{suffix}_{timestamp}.{ext}"
    file_path = os.path.join(base, filename)

    if isinstance(content, bytes):
        content = content.decode("utf-8")

    def _write() -> None:
        with open(file_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

    await asyncio.to_thread(_write)
    logger.info("Report saved: %s", file_path)
    return file_path