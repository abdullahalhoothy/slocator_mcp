"""Read and sanitize markdown report content for downstream LLM analysis."""

import os
from typing import Optional

from config import config
from logging_config import get_logger

logger = get_logger(__name__)

_UNICODE_REPLACEMENTS = {
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "±": "+/-",
    "−": "-",
    "–": "-",
    "—": "--",
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "•": "*",
}


def sanitize_content_for_llm(content: str) -> str:
    for src, dst in _UNICODE_REPLACEMENTS.items():
        content = content.replace(src, dst)
    return content


def read_report_file(file_path: str) -> Optional[str]:
    if not os.path.isabs(file_path):
        file_path = os.path.join(config.paths.reports_dir, file_path)

    if not os.path.exists(file_path):
        logger.error("Report file not found: %s", file_path)
        return None
    if not file_path.endswith(".md"):
        logger.error("Not a markdown file: %s", file_path)
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        return sanitize_content_for_llm(f.read())