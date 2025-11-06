"""
JSON handling utilities for MCP server.
Simplified version with only the functions needed from backend_common.
"""

import json
import asyncio
import aiofiles
import os
from datetime import datetime, date
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel


class FileLock:
    """Simple file locking mechanism for async file operations."""

    def __init__(self):
        self.locks = {}

    @asynccontextmanager
    async def acquire(self, filename):
        if filename not in self.locks:
            self.locks[filename] = asyncio.Lock()
        async with self.locks[filename]:
            yield


# Global file lock manager
file_lock_manager = FileLock()


def to_serializable(obj: Any) -> Any:
    """
    Convert a Pydantic model or any other object to a JSON-serializable format.

    Args:
        obj: Object to convert

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(to_serializable(item) for item in obj)
    elif isinstance(obj, BaseModel):
        return to_serializable(obj.dict(by_alias=True))
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, "__dict__"):
        return to_serializable(obj.__dict__)
    else:
        return obj


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert an object to a JSON-serializable format and verify serializability.

    Args:
        obj: Object to convert

    Returns:
        Verified JSON-serializable object

    Raises:
        ValueError: If object cannot be serialized to JSON
    """
    try:
        serializable_obj = to_serializable(obj)
        json.dumps(serializable_obj)  # Verify it's actually serializable
        return serializable_obj
    except (TypeError, OverflowError, ValueError) as e:
        raise ValueError(f"Object is not JSON serializable: {str(e)}")


async def to_json_string_async(
    data_obj: Any,
    indent: Optional[int] = None,
    ensure_ascii: bool = False
) -> str:
    """
    Asynchronously converts a Python object to a compact JSON string.

    This function uses asyncio.to_thread to run the CPU-bound json.dumps
    in a separate thread, preventing it from blocking the main event loop.
    By default, `indent` is None, creating a compact string for maximum performance.

    Args:
        data_obj: The Python object to serialize
        indent: For debugging, can be set to 2 for pretty-printing
        ensure_ascii: If False, allows non-ASCII characters

    Returns:
        A JSON formatted string (compact by default)
    """
    # Compact representation by default
    separators = (',', ':') if indent is None else None
    return await asyncio.to_thread(
        json.dumps,
        data_obj,
        indent=indent,
        ensure_ascii=ensure_ascii,
        separators=separators
    )


async def use_json(
    file_path: str,
    mode: str,
    json_content: dict = None
) -> Optional[dict]:
    """
    Async JSON file read/write with file locking.

    Args:
        file_path: Path to JSON file
        mode: 'r' for read, 'w' for write
        json_content: Content to write (required for mode='w')

    Returns:
        Dict content for read mode, None for write mode

    Raises:
        ValueError: If mode is invalid
        IOError: If file operations fail
    """
    async with file_lock_manager.acquire(file_path):
        if mode == "w":
            try:
                # Write compact JSON for speed
                content_to_write = await to_json_string_async(json_content)
                async with aiofiles.open(file_path, mode="w", encoding="utf-8") as file:
                    await file.write(content_to_write)
            except IOError as e:
                raise IOError(f"Error writing data file: {str(e)}")

        elif mode == "r":
            try:
                if os.path.exists(file_path):
                    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as file:
                        content = await file.read()
                        return json.loads(content)
                return None
            except json.JSONDecodeError as e:
                raise IOError(f"Error parsing data file: {str(e)}")
            except IOError as e:
                raise IOError(f"Error reading data file: {str(e)}")
        else:
            raise ValueError("Invalid mode. Use 'r' for read or 'w' for write.")