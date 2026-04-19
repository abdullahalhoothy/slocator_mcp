"""
Shared async HTTP client for backend API calls.

All tools use this single helper to POST to the backend, ensuring
consistent request wrapping, auth headers, and error handling.
"""

import aiohttp
from logging_config import get_logger
from config import config

logger = get_logger(__name__)


class BackendError(Exception):
    """Raised when the backend returns a non-200 response."""

    def __init__(self, status: int, text: str):
        self.status = status
        self.text = text
        super().__init__(f"Backend error {status}: {text}")


async def post_to_backend(
    endpoint: str,
    request_body: dict,
    id_token: str,
    message: str = "MCP request",
) -> dict:
    """
    POST to a backend endpoint with the standard request envelope.

    Wraps the payload in the required {message, request_info, request_body}
    structure and attaches the Bearer token header.

    Args:
        endpoint: Path relative to config.backend_url (e.g. "/fastapi/login").
        request_body: The actual payload to send as request_body.
        id_token: JWT Bearer token for Authorization header.
        message: Human-readable description of the request (for logging).

    Returns:
        The parsed "data" field from the JSON response.

    Raises:
        BackendError: If the backend returns a non-200 status.
    """
    url = f"{config.backend_url}{endpoint}"
    payload = {
        "message": message,
        "request_info": {},
        "request_body": request_body,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {id_token}",
    }

    logger.info("POST %s", url)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                text = await response.text()
                logger.error("Backend error %s from %s: %s", response.status, url, text)
                raise BackendError(response.status, text)
            result = await response.json()
            return result.get("data", {})


async def post_to_backend_no_auth(
    endpoint: str,
    request_body: dict,
    message: str = "MCP request",
) -> dict:
    """
    POST to a backend endpoint without an auth token (e.g. login, token refresh).

    Returns:
        The parsed "data" field from the JSON response.

    Raises:
        BackendError: If the backend returns a non-200 status.
    """
    url = f"{config.backend_url}{endpoint}"
    payload = {
        "message": message,
        "request_info": {},
        "request_body": request_body,
    }

    logger.info("POST (no-auth) %s", url)

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                logger.error("Backend error %s from %s: %s", response.status, url, text)
                raise BackendError(response.status, text)
            result = await response.json()
            return result.get("data", {})