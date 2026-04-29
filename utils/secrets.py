"""Secrets loader. Path comes from config.paths.secrets_file; values are cached in-memory."""

import json
from typing import Optional

from config import config

_cache: Optional[dict] = None


def get_secret(key: str) -> str:
    global _cache
    if _cache is None:
        with open(config.paths.secrets_file, "r") as f:
            _cache = json.load(f)
    return _cache[key]