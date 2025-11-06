"""
Configuration for MCP server.
Contains endpoint URLs and constants without external dependencies.
"""

import os
from pathlib import Path
from pydantic import BaseModel


class MCPConfig(BaseModel):
    """MCP Server configuration."""

    # Session settings
    session_ttl_hours: int = 8
    cleanup_interval_hours: int = 1
    temp_storage_path: str = str(Path(__file__).parent / "sessions")


class EndpointConfig:
    """
    Backend API endpoint configuration.
    Replaces dependency on config_factory.CONF
    """

    def __init__(self):
        # Base URL from environment or default
        self.backend_base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        self.base_uri = "/fastapi/"

    @property
    def login(self) -> str:
        """Login endpoint."""
        return self.base_uri + "login"

    @property
    def refresh_token(self) -> str:
        """Token refresh endpoint."""
        return self.base_uri + "token/refresh"

    @property
    def fetch_dataset(self) -> str:
        """Fetch geospatial dataset endpoint."""
        return self.base_uri + "fetch_dataset"

    @property
    def temp_sales_man_problem(self) -> str:
        """Territory optimization endpoint."""
        return self.base_uri + "temp_sales_man_problem"

    @property
    def hub_expansion_analysis(self) -> str:
        """Hub expansion analysis endpoint."""
        return self.base_uri + "hub_expansion_analysis"

    @property
    def smart_pharmacy_report(self) -> str:
        """Smart pharmacy report endpoint."""
        return self.base_uri + "smart_pharmacy_report"


# Global instances
config = MCPConfig()
ENDPOINTS = EndpointConfig()

# Convenience constant
BACKEND_BASE_URL = ENDPOINTS.backend_base_url