"""Shared backend-call wrapper used by all tools."""

from typing import Any, Dict

from config import config
from logging_config import get_logger
from utils import BackendError, post_to_backend

logger = get_logger(__name__)


async def call_backend(
    endpoint_key: str,
    request_body: Dict[str, Any],
    id_token: str,
    log_msg: str = "MCP backend call",
) -> Dict[str, Any]:
    """Call a backend endpoint by config key. Returns {"data": ...} or {"error": ..., "details": ...}."""
    endpoint = getattr(config.backend.endpoints, endpoint_key)
    try:
        data = await post_to_backend(endpoint, request_body, id_token, log_msg)
        return {"data": data}
    except BackendError as e:
        logger.error("%s API error %s: %s", endpoint_key, e.status, e.text)
        return {"error": f"API returned {e.status}", "details": e.text}
    except Exception as e:
        logger.error("%s call failed: %s", endpoint_key, e)
        return {"error": "Request failed", "details": str(e)}