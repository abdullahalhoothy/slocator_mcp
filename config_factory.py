"""
Configuration factory for MCP server.
"""
from pathlib import Path
from typing import Any, Dict
import json
import os
from dataclasses import dataclass

@dataclass
class ApiConfig:
    # Base configuration
    backend_base_uri: str = "/fastapi/"
    test_mode: bool = False
    secrets_dir: str = str(Path(__file__).parent / "secrets")
    api_key: str = ""

    # Google Places API URLs
    ggl_base_url: str = "https://places.googleapis.com/v1/places:"
    nearby_search_url: str = ggl_base_url + "searchNearby"
    search_text_url: str = ggl_base_url + "searchText"
    place_details_url: str = ggl_base_url[0:-1] + "/"

    # Here Maps API
    here_traffic_flow_url: str = "https://data.traffic.hereapi.com/v7/flow"
    here_api_key: str = ""

    # TomTom API
    tomtom_api_url: str = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    tomtom_api_key: str = ""

    @classmethod
    def get_conf(cls):
        conf = cls()
        
        try:
            # Load Google Maps API key
            if os.path.exists(f"{conf.secrets_dir}/secrets_gmap.json"):
                with open(f"{conf.secrets_dir}/secrets_gmap.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conf.api_key = data.get("gmaps_api", "")

            # Load HERE API key
            if os.path.exists(f"{conf.secrets_dir}/secrets_here.json"):
                with open(f"{conf.secrets_dir}/secrets_here.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conf.here_api_key = data.get("here_api_key", "")

            # Load TomTom API key
            if os.path.exists(f"{conf.secrets_dir}/secret_tomtom.json"):
                with open(f"{conf.secrets_dir}/secret_tomtom.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conf.tomtom_api_key = data.get("tomtom_api", "")

        except Exception as e:
            print(f"Error loading configuration: {e}")
        
        return conf

CONF = ApiConfig.get_conf()

if CONF.test_mode:
    print(" TEST MODE ")


class Config:
    """Configuration class for MCP server paths

    Directory Structure (Service-Specific):
    MCP_Server/
    └── reports/     # MCP-generated markdown reports (hub expansion, pharmacy analysis, etc.)

    Backend manages its own static files in backend2-1/static/
    """

    @staticmethod
    def get_reports_path():
        """Get the MCP reports directory path (markdown reports)"""
        project_root = Path(__file__).parent
        # MCP reports go to MCP_Server/reports/
        reports_path = project_root / "reports"
        return str(reports_path)
