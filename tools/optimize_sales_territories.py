from mcp.server.fastmcp import FastMCP
from pydantic import Field

from all_types.request_dtypes import ReqClustersForSalesManData
from context import get_app_context
from config import config
from logging_config import get_logger
from utils import post_to_backend, require_auth, BackendError

logger = get_logger(__name__)


def register_territory_optimization_tools(mcp: FastMCP):
    """Register territory optimization tool by defining it within this function's scope."""

    defaults = config.tool_defaults.territory

    @mcp.tool(
        name="optimize_sales_territories",
        description="""Advanced sales territory optimization using spatial clustering and market analysis.

        🎯 Core Functionality:
        - Creates balanced sales territories based on population density and market potential
        - Analyzes accessibility patterns and customer distribution
        - Optimizes workload distribution across sales representatives
        - Generates territory boundaries with comprehensive business intelligence

        📊 Analysis Features:
        - Population and income-weighted clustering
        - Accessibility analysis (distance-based market reach)
        - Market potential calculation per territory
        - Territory equity and balance assessment
        - Competitive landscape analysis

        🗺️ Geographic Intelligence:
        - Spatial contiguity constraints (connected territories)
        - Distance-based accessibility modeling
        - Grid-based aggregation for precise analysis
        - Territory boundary optimization

        💼 Business Applications:
        - Sales team territory assignment
        - Service area optimization
        - Market penetration analysis
        - Resource allocation planning
        - Performance benchmarking

        Args:
            city_name: Target city for territory optimization
            num_sales_man: Number of sales territories to create
            distance_limit: Maximum travel distance customers will accept (km)
            boolean_query: Business type to analyze (e.g., 'supermarket', 'restaurant')

        Returns:
            Territory analysis handle with comprehensive BI metrics and visualizations
        """,
    )
    async def optimize_sales_territories(
        city_name: str = Field(
            description="Name of the Saudi city for territory optimization (e.g., Riyadh, Jeddah, Dammam)"
        ),
        country_name: str = Field(
            default="Saudi Arabia", description="Country name"
        ),
        num_sales_man: int = Field(
            default=defaults.num_territories,
            description="Number of sales territories to create (recommended: 3-10 for optimal balance)",
        ),
        distance_limit: float = Field(
            default=defaults.distance_limit_km,
            description="Maximum distance customers will travel to reach services (km). Typical values: 2-5km urban, 5-15km rural",
        ),
        boolean_query: str = Field(
            default="supermarket OR grocery_store OR retail",
            description="Business categories to analyze. Examples: 'supermarket', 'restaurant AND NOT fast_food', 'retail OR shopping'",
        ),
        include_raw_data: bool = Field(
            default=False,
            description="Include raw cluster geometries for advanced GIS analysis",
        ),
    ) -> str:
        """Optimize sales territories using advanced spatial analytics and market intelligence."""

        try:
            app_ctx = get_app_context(mcp)
            auth = await require_auth(app_ctx.session_manager)
            if isinstance(auth, str):
                return auth
            _session, user_id, id_token = auth

            req_body = ReqClustersForSalesManData(
                city_name=city_name,
                country_name=country_name,
                num_sales_man=num_sales_man,
                distance_limit=distance_limit,
                boolean_query=boolean_query,
                user_id=user_id,
                include_raw_data=include_raw_data,
            )

            try:
                territory_data = await post_to_backend(
                    config.backend.endpoints.temp_sales_man_problem,
                    req_body.model_dump(),
                    id_token,
                    "Optimizing sales territories using spatial clustering",
                )
            except BackendError as e:
                return f"❌ Error optimizing territories: {e.status} - {e.text}"

            if not territory_data:
                return "❌ Territory optimization failed: No data returned from endpoint."

            territory_analytics = territory_data.get("territory_analytics", [])
            business_insights = territory_data.get("business_insights", {})
            metadata = territory_data.get("metadata", {})

            handle = await app_ctx.handle_manager.store_data(
                data_type="territory_optimization",
                location=city_name.lower().replace(" ", "_"),
                data=territory_data,
            )

            territories_created = (
                len(territory_analytics) if territory_analytics else num_sales_man
            )

            return f"""✅ **Sales Territory Optimization Complete**

🎯 **Analysis Summary**:
- **City**: {city_name}, {country_name}
- **Territories Created**: {territories_created} (target: {num_sales_man})
- **Total Market**: {metadata.get('total_customers', 0):,} potential customers
- **Service Range**: {distance_limit}km maximum travel distance
- **Business Focus**: {boolean_query}

📊 **Territory Balance**:
- **Market Equity Score**: {business_insights.get('market_balance_score', 'N/A')}/100
- **Population Distribution**: {business_insights.get('population_distribution_score', 'N/A')}/100
- **Well-Served Areas**: {business_insights.get('accessibility_analysis', {}).get('well_served_territories', 'N/A')} territories
- **Service Gaps**: {business_insights.get('accessibility_analysis', {}).get('service_desert_territories', 'N/A')} underserved areas

🗺️ **Visualizations Available**:
- **Static Maps**: {len(territory_data.get('plots', {}))} PNG files for reports
- **Interactive Data**: {len(territory_data.get('data_files', {}))} GeoJSON files for DashApp visualization

📋 **Data Handle**: `{handle}`
Use this handle with:
- `generate_territory_report` for detailed business intelligence reports
- DashApp MCP client for interactive data visualization"""

        except Exception as e:
            logger.exception("Critical error in optimize_sales_territories")
            return f"❌ Error during territory optimization: {str(e)}"