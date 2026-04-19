"""Tests for core/session_manager.py"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.session_manager import SessionManager
from models import SessionInfo


@pytest.fixture
def session_manager(tmp_path):
    """Create a SessionManager backed by a temp directory."""
    sm = SessionManager.__new__(SessionManager)
    sm.base_path = tmp_path
    sm.current_session = None
    return sm


@pytest.mark.asyncio
async def test_create_session_writes_metadata(session_manager, tmp_path):
    """create_session should persist metadata and return a valid SessionInfo."""
    session = await session_manager.create_session()

    assert session.session_id
    metadata_path = tmp_path / session.session_id / "session_metadata.json"
    assert metadata_path.exists()
    assert session_manager.current_session is session


@pytest.mark.asyncio
async def test_create_session_sets_expiry(session_manager):
    """Newly created session should expire roughly config.session_ttl_hours in the future."""
    from config import config
    session = await session_manager.create_session()
    now = datetime.now()

    # Allow ±5 seconds slop
    expected = now + timedelta(hours=config.session_ttl_hours)
    diff = abs((session.expires_at - expected).total_seconds())
    assert diff < 5


@pytest.mark.asyncio
async def test_get_current_session_returns_in_memory(session_manager):
    """If a session is already in memory, return it without touching disk."""
    fake = SessionInfo(
        session_id="abc123",
        expires_at=datetime.now() + timedelta(hours=1),
    )
    session_manager.current_session = fake

    result = await session_manager.get_current_session()
    assert result is fake


@pytest.mark.asyncio
async def test_get_current_session_loads_from_disk(session_manager):
    """When current_session is None, load the most recent valid session from disk."""
    # Create a real session on disk first
    session = await session_manager.create_session()
    # Clear in-memory state to simulate a restart
    session_manager.current_session = None

    loaded = await session_manager.get_current_session()
    assert loaded is not None
    assert loaded.session_id == session.session_id


@pytest.mark.asyncio
async def test_get_current_session_ignores_expired(session_manager, tmp_path):
    """An expired session on disk should not be loaded."""
    # Write a session that is already expired
    session_id = "expired01"
    session_path = tmp_path / session_id
    session_path.mkdir()

    expired_info = SessionInfo(
        session_id=session_id,
        expires_at=datetime.now() - timedelta(hours=1),
    )
    from utils import use_json, convert_to_serializable
    metadata_path = str(session_path / "session_metadata.json")
    await use_json(metadata_path, "w", convert_to_serializable(expired_info.model_dump()))

    result = await session_manager.get_current_session()
    assert result is None


@pytest.mark.asyncio
async def test_cleanup_session_removes_directory(session_manager, tmp_path):
    """cleanup_session should delete the session directory."""
    session = await session_manager.create_session()
    session_path = tmp_path / session.session_id
    assert session_path.exists()

    await session_manager.cleanup_session(session.session_id)
    assert not session_path.exists()


@pytest.mark.asyncio
async def test_update_session_auth_persists_tokens(session_manager, tmp_path):
    """update_session_auth should write tokens to disk and update in-memory session."""
    session = await session_manager.create_session()

    await session_manager.update_session_auth(
        session.session_id,
        user_id="user_42",
        id_token="tok_abc",
        refresh_token="ref_xyz",
        expires_in=3600,
    )

    updated = session_manager.current_session
    assert updated.user_id == "user_42"
    assert updated.id_token == "tok_abc"
    assert updated.refresh_token == "ref_xyz"


@pytest.mark.asyncio
async def test_get_valid_id_token_no_session(session_manager):
    """Returns (None, None) when there is no active session."""
    user_id, id_token = await session_manager.get_valid_id_token()
    assert user_id is None
    assert id_token is None


@pytest.mark.asyncio
async def test_get_valid_id_token_valid_returns_tokens(session_manager):
    """Returns tokens directly when the token is still valid."""
    session = await session_manager.create_session()
    await session_manager.update_session_auth(
        session.session_id,
        user_id="user_1",
        id_token="tok_valid",
        refresh_token="ref_1",
        expires_in=3600,
    )

    user_id, id_token = await session_manager.get_valid_id_token()
    assert user_id == "user_1"
    assert id_token == "tok_valid"


@pytest.mark.asyncio
async def test_get_valid_id_token_refreshes_expired(session_manager):
    """When token is expired, calls post_to_backend_no_auth to refresh."""
    session = await session_manager.create_session()
    # Set token as already expired
    await session_manager.update_session_auth(
        session.session_id,
        user_id="user_1",
        id_token="tok_old",
        refresh_token="ref_1",
        expires_in=-100,  # expires in the past
    )

    mock_token_data = {
        "localId": "user_1",
        "idToken": "tok_new",
        "refreshToken": "ref_new",
        "expiresIn": "3600",
    }

    with patch("core.session_manager.post_to_backend_no_auth", new=AsyncMock(return_value=mock_token_data)):
        user_id, id_token = await session_manager.get_valid_id_token()

    assert user_id == "user_1"
    assert id_token == "tok_new"