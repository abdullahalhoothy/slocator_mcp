"""
Request data models for MCP tools.
Copied from all_types/request_dtypes.py with only the models we need.
"""

from typing import Optional
from pydantic import BaseModel


# ===== Base Models =====

class Coordinate(BaseModel):
    """Geographic coordinate."""
    lat: Optional[float] = None
    lng: Optional[float] = None


class ReqCityCountry(BaseModel):
    """City and country specification."""
    city_name: Optional[str] = None
    country_name: Optional[str] = None


class UserId(BaseModel):
    """User identification."""
    user_id: str


class BooleanQuery(BaseModel):
    """Boolean query for searching."""
    boolean_query: Optional[str] = ""


# ===== Derived Models =====

class ReqFetchDataset(ReqCityCountry, Coordinate):
    """Request model for fetching geospatial datasets."""

    # Search parameters
    boolean_query: Optional[str] = ""
    action: Optional[str] = ""
    page_token: Optional[str] = ""
    search_type: Optional[str] = "category_search"
    text_search: Optional[str] = ""

    # Geographic parameters
    zoom_level: Optional[int] = 0
    radius: Optional[float] = 30000.0
    bounding_box: Optional[list[float]] = []

    # Filter parameters
    included_types: Optional[list[str]] = []
    excluded_types: Optional[list[str]] = []

    # Output parameters
    ids_and_location_only: Optional[bool] = False
    include_rating_info: Optional[bool] = False
    include_only_sub_properties: Optional[bool] = True
    full_load: Optional[bool] = False

    # User context
    user_id: Optional[str] = "default_user"
    layer_id: Optional[str] = ""


class ReqClustersForSalesManData(BooleanQuery, UserId, ReqCityCountry):
    """Request model for sales territory optimization."""

    num_sales_man: int
    distance_limit: float = 2.5
    include_raw_data: bool = False