"""Utility functions for MCP server."""

from .auth_helpers import require_auth
from .http_client import BackendError, post_to_backend, post_to_backend_no_auth
from .json_handler import convert_to_serializable, to_json_string_async, use_json
from .numeric import (
    assess_balance_quality,
    calculate_statistics,
    format_number,
    safe_divide,
    safe_get,
)
from .report_io import read_report_file, sanitize_content_for_llm
from .report_writer import save_report
from .secrets import get_secret

__all__ = [
    "BackendError",
    "assess_balance_quality",
    "calculate_statistics",
    "convert_to_serializable",
    "format_number",
    "get_secret",
    "post_to_backend",
    "post_to_backend_no_auth",
    "read_report_file",
    "require_auth",
    "safe_divide",
    "safe_get",
    "sanitize_content_for_llm",
    "save_report",
    "to_json_string_async",
    "use_json",
]