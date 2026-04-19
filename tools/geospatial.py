from mcp.server.fastmcp import FastMCP
from pydantic import Field

from all_types.request_dtypes import ReqFetchDataset
from context import get_app_context
from config import config
from logging_config import get_logger
from utils import post_to_backend, require_auth, BackendError

logger = get_logger(__name__)


def register_geospatial_tools(mcp: FastMCP):
    """Register all geospatial tools by defining them within this function's scope."""

    logger.info("Registering geospatial tools with MCP server")

    @mcp.tool(
        name="fetch_geospatial_data",
        description="""Universal geospatial data fetcher for Saudi Arabia that ALWAYS returns GeoJSON format.

        🎯 Data Sources Available:
        - Real estate properties (warehouses, commercial, residential)
        - Points of Interest (POI): restaurants, gas stations, mosques, مطاعم, محطات وقود
        - Demographics and population centers
        - Commercial properties and rental listings
        - Traffic patterns and accessibility data
        - Competitor locations and market data

        📍 Geographic Coverage:
        - Cities: Riyadh, Jeddah, Dammam, Mecca, Medina, Khobar
        - Regions: All Saudi provinces and major districts
        - Coordinate-based queries with bounding boxes

        ⚡ PERFORMANCE: Returns lightweight data handle + summary.
        Full GeoJSON dataset stored server-side for analysis tools.

        Args:
            city_name: Saudi city name (Riyadh, Jeddah, Dammam, etc.)
            boolean_query: Search query using OR/AND operators
            data_source: Data source type (poi, real_estate, demographics)

        Returns:
            Data handle ID and summary information
        """,
    )
    async def fetch_geospatial_data(
        lat: float = Field(description="Latitude of the search center point"),
        lng: float = Field(description="Longitude of the search center point"),
        radius: float = Field(
            default=5000, description="Search radius in meters"
        ),
        boolean_query: str = Field(
            description="Boolean search query. Examples: 'warehouse OR logistics', 'restaurant AND NOT fast_food', 'gas_station'"
        ),
        city_name: str = Field(
            description="Name of the Saudi city (e.g., Riyadh, Jeddah, Dammam)"
        ),
        country_name: str = Field(
            default="Saudi Arabia", description="Country name"
        ),
        action: str = Field(
            default="sample",
            description="'sample' for quick preview (20 records) or 'full data' for complete dataset",
        ),
        user_id: str = Field(
            default="default_user", description="User ID for the request"
        ),
        include_only_sub_properties: bool = Field(
            default=True,
            description="If true, returns only essential properties for each feature",
        ),
        include_rating_info: bool = Field(
            default=False,
            description="If true, includes detailed rating and review information",
        ),
    ) -> str:
        """Fetch user-specific geospatial data. Requires user to be logged in."""

        try:
            app_ctx = get_app_context(mcp)
            auth = await require_auth(app_ctx.session_manager)
            if isinstance(auth, str):
                return auth
            _session, user_id, id_token = auth

            req_body = ReqFetchDataset(
                lat=lat,
                lng=lng,
                radius=radius,
                boolean_query=boolean_query,
                city_name=city_name,
                country_name=country_name,
                action=action,
                user_id=user_id,
                include_only_sub_properties=include_only_sub_properties,
                include_rating_info=include_rating_info,
                page_token="",
                ids_and_location_only=False,
                search_type="category_search",
            )

            try:
                dataset = await post_to_backend(
                    config.endpoints.fetch_dataset,
                    req_body.model_dump(),
                    id_token,
                    "Fetching Saudi location data via MCP",
                )
            except BackendError as e:
                return f"Error fetching data: {e.status} - {e.text}"

            if not dataset or not dataset.get("features"):
                return f"No data returned from the backend for query: '{boolean_query}' in {city_name}."

            features = dataset.get("features", [])
            districts = {
                f.get("properties", {}).get("district")
                for f in features
                if f.get("properties", {}).get("district")
            }
            property_types = {
                f.get("properties", {}).get("primaryType")
                for f in features
                if f.get("properties", {}).get("primaryType")
            }

            handle = await app_ctx.handle_manager.store_data(
                data_type="geospatial_data",
                location=city_name.lower().replace(" ", "_"),
                data=dataset,
            )

            count = len(features)
            return (
                f"✅ Data fetched. Handle: `{handle}`. "
                f"Summary: {count} records found for '{boolean_query}' in {city_name}. "
                f"Districts: {list(districts)[:10]}. Types: {list(property_types)[:10]}."
            )

        except Exception as e:
            logger.exception("Critical error in fetch_geospatial_data")
            return f"Error during data fetch: {str(e)}"
