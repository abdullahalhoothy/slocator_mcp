"""Tests for utils/http_client.py"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.http_client import post_to_backend, post_to_backend_no_auth, BackendError


def _make_mock_response(status: int, json_data: dict):
    """Build a mock aiohttp response context manager."""
    response = MagicMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data)
    response.text = AsyncMock(return_value=str(json_data))

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_mock_session(response_cm):
    """Build a mock aiohttp.ClientSession context manager."""
    session = MagicMock()
    session.post = MagicMock(return_value=response_cm)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)
    return session_cm


@pytest.mark.asyncio
async def test_post_to_backend_success():
    """Returns the inner data dict on a 200 response."""
    response_cm = _make_mock_response(200, {"data": {"key": "value"}})
    session_cm = _make_mock_session(response_cm)

    with patch("aiohttp.ClientSession", return_value=session_cm):
        result = await post_to_backend("/fastapi/test", {"x": 1}, "id_token_abc")

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_post_to_backend_raises_on_non_200():
    """Non-200 response should raise BackendError with status and text."""
    response_cm = _make_mock_response(422, {})
    response_cm.__aenter__.return_value.text = AsyncMock(return_value="Unprocessable")
    session_cm = _make_mock_session(response_cm)

    with patch("aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(BackendError) as exc_info:
            await post_to_backend("/fastapi/test", {}, "tok")

    assert exc_info.value.status == 422
    assert "Unprocessable" in exc_info.value.text


@pytest.mark.asyncio
async def test_post_to_backend_missing_data_key():
    """If response has no 'data' key, returns an empty dict."""
    response_cm = _make_mock_response(200, {"result": "ok"})
    session_cm = _make_mock_session(response_cm)

    with patch("aiohttp.ClientSession", return_value=session_cm):
        result = await post_to_backend("/fastapi/test", {}, "tok")

    assert result == {}


@pytest.mark.asyncio
async def test_post_to_backend_no_auth_success():
    """post_to_backend_no_auth omits the Authorization header and returns data."""
    response_cm = _make_mock_response(200, {"data": {"token": "abc"}})
    session_cm = _make_mock_session(response_cm)

    with patch("aiohttp.ClientSession", return_value=session_cm):
        result = await post_to_backend_no_auth("/fastapi/login", {"email": "x@y.com"})

    assert result == {"token": "abc"}


@pytest.mark.asyncio
async def test_post_to_backend_no_auth_raises_on_non_200():
    """post_to_backend_no_auth raises BackendError on failure."""
    response_cm = _make_mock_response(401, {})
    response_cm.__aenter__.return_value.text = AsyncMock(return_value="Unauthorized")
    session_cm = _make_mock_session(response_cm)

    with patch("aiohttp.ClientSession", return_value=session_cm):
        with pytest.raises(BackendError) as exc_info:
            await post_to_backend_no_auth("/fastapi/login", {})

    assert exc_info.value.status == 401


@pytest.mark.asyncio
async def test_backend_error_attributes():
    """BackendError should expose status and text."""
    err = BackendError(500, "Internal Server Error")
    assert err.status == 500
    assert err.text == "Internal Server Error"