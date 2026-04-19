"""
Configuration for MCP server.
Loads all settings from config.json; environment variables can override values.
"""

import json
import os
from pathlib import Path

_ROOT = Path(__file__).parent
_CONFIG_FILE = _ROOT / "config.json"


def _load() -> dict:
    base: dict = {}
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE) as f:
            base = json.load(f)
    return base


class _EndpointsConfig:
    def __init__(self, endpoints: dict) -> None:
        self.login: str = endpoints["login"]
        self.refresh_token: str = endpoints["refresh_token"]
        self.fetch_dataset: str = endpoints["fetch_dataset"]
        self.temp_sales_man_problem: str = endpoints["temp_sales_man_problem"]
        self.hub_expansion_analysis: str = endpoints["hub_expansion_analysis"]
        self.smart_pharmacy_report: str = endpoints["smart_pharmacy_report"]


class Config:
    def __init__(self, cfg: dict) -> None:
        self.backend_url: str = str(cfg["backend_url"])
        self.server_host: str = str(cfg["server_host"])
        self.server_port: int = int(cfg["server_port"])
        self.cors_origins: list[str] = str(cfg["cors_origins"]).split(",")
        self.session_ttl_hours: int = int(cfg["session_ttl_hours"])
        self.cleanup_interval_hours: int = int(cfg["cleanup_interval_hours"])
        self.sessions_path: str = str(_ROOT / str(cfg["sessions_path"]))
        self.reports_path: str = str(_ROOT / str(cfg["reports_path"]))
        self.endpoints: _EndpointsConfig = _EndpointsConfig(cfg["endpoints"])


config = Config(_load())