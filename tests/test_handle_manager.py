"""Tests for core/handle_manager.py"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.handle_manager import HandleManager
from core.session_manager import SessionManager
from models import SessionInfo


@pytest.fixture
async def handle_manager(tmp_path):
    """Return a HandleManager with a real SessionManager backed by tmp_path."""
    sm = SessionManager.__new__(SessionManager)
    sm.base_path = tmp_path
    sm.current_session = None
    # Pre-create a session so tests have one
    await sm.create_session()
    hm = HandleManager(sm)
    return hm


@pytest.mark.asyncio
async def test_store_and_read_roundtrip(handle_manager):
    """Stored data should be retrievable via read_data."""
    payload = {"city": "Riyadh", "count": 42}
    handle = await handle_manager.store_data("geospatial_data", "riyadh", payload)

    assert handle.endswith(".json")
    result = await handle_manager.read_data(handle)
    assert result["city"] == "Riyadh"
    assert result["count"] == 42


@pytest.mark.asyncio
async def test_store_returns_unique_handles(handle_manager):
    """Two store calls should produce different handles."""
    h1 = await handle_manager.store_data("test", "riyadh", {"x": 1})
    h2 = await handle_manager.store_data("test", "riyadh", {"x": 2})
    assert h1 != h2


@pytest.mark.asyncio
async def test_read_nonexistent_handle_returns_none(handle_manager):
    """Reading an unknown handle should return None without raising."""
    result = await handle_manager.read_data("nonexistent_handle.json")
    assert result is None


@pytest.mark.asyncio
async def test_list_session_data_shows_stored_files(handle_manager):
    """list_session_data should include files created by store_data."""
    await handle_manager.store_data("territory_optimization", "jeddah", {"data": []})
    await handle_manager.store_data("geospatial_data", "dammam", {"features": []})

    sm = handle_manager.session_manager
    session = await sm.get_current_session()
    files = await handle_manager.list_session_data(session.session_id)

    handles = [f["handle"] for f in files]
    assert len(handles) == 2
    assert all(h.endswith(".json") for h in handles)


@pytest.mark.asyncio
async def test_list_session_data_excludes_metadata(handle_manager):
    """session_metadata.json should not appear in list_session_data output."""
    sm = handle_manager.session_manager
    session = await sm.get_current_session()
    files = await handle_manager.list_session_data(session.session_id)

    handles = [f["handle"] for f in files]
    assert "session_metadata.json" not in handles
    assert "session_info.json" not in handles


@pytest.mark.asyncio
async def test_remove_data_deletes_file(handle_manager):
    """remove_data should delete the underlying file."""
    handle = await handle_manager.store_data("test", "riyadh", {"v": 1})
    sm = handle_manager.session_manager
    session = await sm.get_current_session()
    file_path = sm.base_path / session.session_id / handle

    assert file_path.exists()
    removed = await handle_manager.remove_data(handle)
    assert removed is True
    assert not file_path.exists()


@pytest.mark.asyncio
async def test_store_creates_session_if_missing(tmp_path):
    """store_data should create a new session automatically if none exists."""
    sm = SessionManager.__new__(SessionManager)
    sm.base_path = tmp_path
    sm.current_session = None
    hm = HandleManager(sm)

    handle = await hm.store_data("test", "riyadh", {"auto": True})
    assert handle
    assert sm.current_session is not None