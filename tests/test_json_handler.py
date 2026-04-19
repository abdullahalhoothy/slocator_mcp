"""Tests for utils/json_handler.py"""
import pytest
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.json_handler import use_json, convert_to_serializable, to_json_string_async


@pytest.mark.asyncio
async def test_write_and_read_roundtrip(tmp_path):
    """Writing then reading JSON should return the original data."""
    path = str(tmp_path / "test.json")
    data = {"city": "Riyadh", "count": 42, "nested": {"key": "value"}}

    await use_json(path, "w", data)
    result = await use_json(path, "r")

    assert result == data


@pytest.mark.asyncio
async def test_read_nonexistent_returns_none(tmp_path):
    """Reading a file that doesn't exist should return None."""
    path = str(tmp_path / "missing.json")
    result = await use_json(path, "r")
    assert result is None


@pytest.mark.asyncio
async def test_write_overwrites_existing(tmp_path):
    """Writing twice to the same path should overwrite."""
    path = str(tmp_path / "overwrite.json")
    await use_json(path, "w", {"version": 1})
    await use_json(path, "w", {"version": 2})

    result = await use_json(path, "r")
    assert result["version"] == 2


@pytest.mark.asyncio
async def test_invalid_mode_raises(tmp_path):
    """An invalid mode should raise ValueError."""
    path = str(tmp_path / "test.json")
    with pytest.raises(ValueError, match="Invalid mode"):
        await use_json(path, "x")


@pytest.mark.asyncio
async def test_concurrent_writes_are_safe(tmp_path):
    """Multiple concurrent writes should not corrupt the file."""
    import asyncio
    path = str(tmp_path / "concurrent.json")

    async def write(i):
        await use_json(path, "w", {"value": i})

    await asyncio.gather(*[write(i) for i in range(10)])
    result = await use_json(path, "r")
    # One of the values should have won — file must be valid JSON
    assert "value" in result
    assert isinstance(result["value"], int)


def test_convert_to_serializable_datetime():
    """Datetime objects should be converted to ISO strings."""
    dt = datetime(2024, 1, 15, 12, 0, 0)
    result = convert_to_serializable({"ts": dt})
    assert result["ts"] == "2024-01-15T12:00:00"


def test_convert_to_serializable_nested():
    """Nested dicts and lists should be serialized recursively."""
    data = {"list": [{"dt": datetime(2024, 6, 1)}], "num": 42}
    result = convert_to_serializable(data)
    assert result["list"][0]["dt"] == "2024-06-01T00:00:00"
    assert result["num"] == 42


def test_convert_to_serializable_plain_dict():
    """Plain serializable dicts should pass through unchanged."""
    data = {"key": "value", "num": 1}
    result = convert_to_serializable(data)
    assert result == data


@pytest.mark.asyncio
async def test_to_json_string_async_compact():
    """Default (no indent) should produce compact JSON without newlines."""
    result = await to_json_string_async({"a": 1, "b": 2})
    assert "\n" not in result
    assert '"a":1' in result or '"a": 1' not in result  # compact form has no space


@pytest.mark.asyncio
async def test_to_json_string_async_pretty():
    """With indent=2, output should be multi-line."""
    result = await to_json_string_async({"a": 1}, indent=2)
    assert "\n" in result