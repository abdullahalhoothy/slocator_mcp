import json
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from config import config
from context import get_app_context
from logging_config import get_logger
from tools._base import call_backend
from utils import require_auth, save_report

logger = get_logger(__name__)


def _format_short_response(response_data: Dict[str, Any]) -> str:
    if "error" in response_data:
        return f" Error: {response_data['error']}\nDetails: {response_data.get('details', 'No details')}"
    if "data" not in response_data:
        return f" Unexpected response format: {json.dumps(response_data, indent=2, ensure_ascii=False)}"

    data = response_data["data"]
    out = " **HUB EXPANSION ANALYSIS RESULTS**\n" + "=" * 50 + "\n\n"

    summary = data.get("analysis_summary") or {}
    if summary:
        out += " **ANALYSIS SUMMARY**\n"
        out += f"• Scope: {summary.get('scope', 'N/A')}\n"
        out += f"• Methodology: {summary.get('methodology', 'N/A')}\n"
        out += f"• Qualified Locations: {summary.get('total_qualified_locations', 0)}\n"
        out += f"• Target Type: {summary.get('target_type', 'N/A')}\n"
        out += f"• Competitor: {summary.get('competitor_analyzed', 'N/A')}\n\n"

    primary = (data.get("primary_recommendation") or {}).get("hub_details") or {}
    if primary:
        location = primary.get("location") or {}
        specs = primary.get("specifications") or {}
        metrics = primary.get("performance_metrics") or {}
        out += " **PRIMARY RECOMMENDATION**\n"
        out += f"• Hub ID: {primary.get('hub_id', 'N/A')}\n"
        out += f"• Address: {location.get('address', 'N/A')}\n"
        out += f"• District: {location.get('district', 'N/A')}\n"
        coords = location.get("coordinates") or {}
        if coords:
            out += f"• Coordinates: {coords.get('lat', 'N/A')}, {coords.get('lng', 'N/A')}\n"
        out += f"• Size: {specs.get('size_m2', 0):,} m²\n"
        out += f"• Monthly Rent: {specs.get('monthly_rent', 0):,} SAR\n"
        out += f"• Rent per m²: {specs.get('rent_per_m2', 0)} SAR\n"
        out += f"• **Total Score: {metrics.get('total_score', 0)}/10**\n"
        components = metrics.get("component_scores") or {}
        if components:
            out += "• Component Scores:\n"
            for name, score in components.items():
                out += f"  - {name.replace('_', ' ').title()}: {score}/10\n"
        out += "\n"

    alternatives = data.get("alternative_locations") or []
    if alternatives:
        out += "🔄 **ALTERNATIVE LOCATIONS**\n"
        for i, alt in enumerate(alternatives[:3], 1):
            loc = alt.get("location") or {}
            mtr = alt.get("performance_metrics") or {}
            out += f"{i}. {alt.get('hub_id', 'N/A')} - Score: {mtr.get('total_score', 0)}/10\n"
            out += f"   Address: {loc.get('address', 'N/A')}\n"
        out += "\n"

    market = data.get("market_competitive_analysis") or {}
    if market:
        out += " **MARKET ANALYSIS**\n"
        out += f"• Population Centers: {market.get('total_population_centers', 0)}\n"
        out += f"• Target Locations: {market.get('total_target_locations', 0)}\n"
        out += f"• Competitor Locations: {market.get('total_competitor_locations', 0)}\n"
        out += f"• Min Population Threshold: {market.get('min_population_threshold', 0):,}\n\n"

    return out


def _build_markdown_report(
    response_data: Dict[str, Any], request_params: Dict[str, Any]
) -> str:
    if "error" in response_data or "data" not in response_data:
        return "# Error Report\n\nFailed to generate analysis report due to API errors."

    data = response_data["data"]
    city_name = str(request_params.get("city_name", "Unknown City"))
    target_search = str(request_params.get("target_search", ""))
    competitor_name = str(request_params.get("competitor_name", ""))
    target_display = target_search.replace("@", "") or "supermarkets"
    competitor_display = competitor_name.replace("@", "") or "competitor"
    hub_type = str(request_params.get("hub_type", "warehouse"))
    current_date = datetime.now().strftime("%B %d, %Y")

    primary = (data.get("primary_recommendation") or {}).get("hub_details") or {}
    hub_id = str(primary.get("hub_id", "N/A"))
    location_info = primary.get("location") or {}
    district = str(location_info.get("district") or "Unknown District")

    metrics = primary.get("performance_metrics") or {}
    target_access = metrics.get("target_access") or {}
    competitive_pos = metrics.get("competitive_positioning") or {}
    population_access = metrics.get("population_access") or {}
    rent_details = metrics.get("rent_details") or {}
    coverage_analysis = metrics.get("coverage_analysis") or {}
    component_scores = metrics.get("component_scores") or {}

    target_time = target_access.get("time_minutes", "N/A")
    nearest_target = target_access.get("nearest_target", "N/A")
    competitor_distance = competitive_pos.get("distance_km", "N/A")
    nearest_competitor = competitive_pos.get("nearest_competitor_name", "N/A")
    avg_time_to_centers = population_access.get("avg_time_to_centers", "N/A")
    accessible_population = population_access.get("accessible_population", 0)

    coordinates = location_info.get("coordinates") or {}
    lat = coordinates.get("lat", 0)
    lng = coordinates.get("lng", 0)
    address = location_info.get("address", "N/A")

    specifications = primary.get("specifications") or {}
    size_m2 = specifications.get("size_m2", 0)
    monthly_rent = specifications.get("monthly_rent", 0)
    rent_per_m2 = specifications.get("rent_per_m2", 0)

    primary_score = metrics.get("total_score", 0)
    comp_score = component_scores.get("competitive_advantage_score", 0)
    rent_score = component_scores.get("rent_efficiency_score", 0)
    rent_percentile = rent_details.get("percentile", "N/A")
    total_coverage = coverage_analysis.get("total_coverage", 0)
    coverage_percentage = coverage_analysis.get("coverage_percentage", 0)

    market_analysis = data.get("market_competitive_analysis") or {}
    total_competitors = market_analysis.get("total_competitor_locations", 0)
    total_targets = market_analysis.get("total_target_locations", 0)
    total_population_centers = market_analysis.get("total_population_centers", 0)

    report = f"""# **Logistics Expansion Analysis Report: {city_name} Market Entry Strategy**

**Prepared for:** [Client Name]
**Prepared by:** Geospatial Intelligence Platform
**Date:** {current_date}
**Project Code:** {city_name.upper()}-LOG-2025-001

---

## **Executive Summary**

**Bottom Line Up Front:** We recommend establishing your primary logistics hub at **{hub_type.title()} Location {hub_id}** in the {district} district. This strategic positioning achieves {target_time}-minute average proximity to {target_display} locations, {avg_time_to_centers}-minute access to major population centers, and provides {comp_score}% delivery time advantage over nearest competitors.

**Key Findings:**
- **Market Opportunity:** {accessible_population:,} potential customers within optimal delivery zones
- **Competitive Advantage:** {competitor_distance}km distance from nearest competitor ({nearest_competitor})
- **Coverage Optimization:** {coverage_percentage}% of target population reachable within service window

---

## **Market Intelligence Analysis**

### **Competitor Landscape Analysis**

- **Primary Competitor Tracked:** {competitor_display} — {total_competitors} locations identified in this market
- **{target_display} Locations Indexed:** {total_targets}
- **Population Centers Considered:** {total_population_centers}

---

## **Site Selection Analysis**

### **Multi-Criteria Scoring Results**

We evaluated {data.get('analysis_summary', {}).get('total_qualified_locations', 0)} {hub_type} locations.

| **Rank** | **Location ID** | **District** | **Total Score** | **{target_display} Proximity** | **Population Access** | **Rent Efficiency** |
|----------|-----------------|--------------|-----------------|--------------------------------|----------------------|---------------------|
| 1 | {hub_id} | {district} | {primary_score} | {target_time} min | {avg_time_to_centers} min | SAR {rent_per_m2}/m² |"""

    for i, alt in enumerate((data.get("alternative_locations") or [])[:4], 2):
        alt_id = alt.get("hub_id", f"HUB-{i:03d}")
        alt_loc = alt.get("location") or {}
        alt_mtr = alt.get("performance_metrics") or {}
        alt_specs = alt.get("specifications") or {}
        report += (
            f"\n| {i} | {alt_id} | "
            f"{alt_loc.get('district') or 'Various'} | "
            f"{alt_mtr.get('total_score', 0)} | "
            f"{(alt_mtr.get('target_access') or {}).get('time_minutes', 'N/A')} min | "
            f"{(alt_mtr.get('population_access') or {}).get('avg_time_to_centers', 'N/A')} min | "
            f"SAR {alt_specs.get('rent_per_m2', 0)}/m² |"
        )

    report += f"""

### **Detailed Site Analysis: Primary Recommendation**

**{hub_type.title()} {hub_id} ({district} District)**

- Address: {address}
- Coordinates: {lat:.4f}°N, {lng:.4f}°E
- Facility Size: {size_m2:,} m²
- Monthly Rent: SAR {monthly_rent:,} (SAR {rent_per_m2}/m²)
- Nearest {target_display}: {nearest_target} ({target_time} minutes)
- Nearest Competitor: {nearest_competitor} ({competitor_distance} km)

---

## **Economic Viability Assessment**

- **Rent Efficiency Score:** {rent_score}/10 (Percentile: {rent_percentile})
- **Population Coverage:** {total_coverage:,} people within service range
- **Cost per Potential Customer:** SAR {monthly_rent / max(accessible_population, 1):.2f}/month
- **Initial Setup Cost:** SAR {monthly_rent * 6:,} (6 months advance + setup)

---

## **Conclusion**

Strategic positioning at {hub_id} in {district} provides optimal balance of market access and operational efficiency.

---

**Report prepared using advanced geospatial intelligence platform. All projections based on current market conditions as of {current_date}.**"""

    return report


def register_natural_language_hub_analyzer_tools(mcp: FastMCP):
    logger.info("Registering natural language hub analyzer tool with MCP server")

    defaults = config.tool_defaults.hub
    weights = defaults.scoring_weights

    @mcp.tool(
        name="hub_expansion_analyzer",
        description="""Analyze potential hub locations for business expansion with comprehensive scoring.

        Analysis Capabilities:
        - Multi-criteria location scoring and ranking
        - Target destination proximity analysis (supermarkets, الحلقه)
        - Competitor positioning and market gaps
        - Population accessibility and demographics
        - Cost efficiency and ROI calculations

        Scoring Factors:
        - Target proximity (35%): Distance to key destinations
        - Population access (30%): Accessibility to customer base
        - Rent efficiency (10%): Cost per square meter analysis
        - Competitive advantage (15%): Positioning vs competitors
        - Population coverage (10%): Demographic reach
        """,
    )
    async def hub_expansion_analyzer(
        city_name: str = Field(default=defaults.city_name, description="Target city for hub expansion analysis"),
        country_name: str = Field(default=defaults.country_name, description="Target country"),
        target_search: str = Field(default=defaults.target_search, description="Target destinations to analyze proximity to"),
        competitor_name: str = Field(default=defaults.competitor_name, description="Competitor name to analyze against"),
        hub_type: str = Field(default=defaults.hub_type, description="Type of hub to search for"),
        max_target_distance_km: float = Field(default=defaults.max_target_distance_km, description="Maximum distance to target destinations in kilometers"),
        max_population_center_time_minutes: int = Field(default=defaults.max_population_center_time_minutes, description="Maximum travel time to population centers in minutes"),
        top_results_count: int = Field(default=defaults.top_results_count, description="Number of top-ranked locations to return"),
        min_facility_size_m2: Optional[int] = Field(default=None, description="Minimum facility size in square meters"),
        max_rent_per_m2: Optional[float] = Field(default=None, description="Maximum rent per square meter"),
        generate_report: bool = Field(default=False, description="Generate and save a comprehensive markdown report"),
    ) -> str:
        try:
            app_ctx = get_app_context(mcp)
            auth = await require_auth(app_ctx.session_manager)
            if isinstance(auth, str):
                return auth
            _session, user_id, id_token = auth

            logger.info("Processing hub expansion analysis for %s for user: %s", city_name, user_id)

            request_body = {
                "city_name": city_name,
                "country_name": country_name,
                "analysis_bounds": {},
                "target_search": target_search,
                "max_target_distance_km": max_target_distance_km,
                "max_target_time_minutes": defaults.max_target_time_minutes,
                "competitor_name": competitor_name,
                "competitor_analysis_radius_km": defaults.competitor_analysis_radius_km,
                "hub_type": hub_type,
                "min_facility_size_m2": min_facility_size_m2,
                "max_rent_per_m2": max_rent_per_m2,
                "max_population_center_distance_km": defaults.max_population_center_distance_km,
                "max_population_center_time_minutes": max_population_center_time_minutes,
                "min_population_threshold": defaults.min_population_threshold,
                "scoring_weights": {
                    "target_proximity": weights.target_proximity,
                    "population_access": weights.population_access,
                    "rent_efficiency": weights.rent_efficiency,
                    "competitive_advantage": weights.competitive_advantage,
                    "population_coverage": weights.population_coverage,
                },
                "top_results_count": top_results_count,
                "include_route_optimization": defaults.include_route_optimization,
                "include_market_analysis": defaults.include_market_analysis,
                "include_success_metrics": defaults.include_success_metrics,
                "user_id": user_id,
            }

            response_data = await call_backend(
                "hub_expansion_analysis",
                request_body,
                id_token,
                "Hub expansion analysis via natural language MCP tool",
            )

            if "error" in response_data:
                return json.dumps(
                    {
                        "report_file": "",
                        "data_files": {},
                        "response": _format_short_response(response_data),
                        "metadata": {"error": True, "analysis_type": "hub_expansion", "city": city_name},
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            handle = await app_ctx.handle_manager.store_data(
                data_type="hub_expansion",
                location=city_name.lower().replace(" ", "_"),
                data=response_data,
            )

            saved_report_file = ""
            if generate_report:
                request_params = {
                    "city_name": city_name,
                    "country_name": country_name,
                    "target_search": target_search,
                    "competitor_name": competitor_name,
                    "hub_type": hub_type,
                    "max_target_distance_km": max_target_distance_km,
                    "max_population_center_time_minutes": max_population_center_time_minutes,
                }
                report_content = _build_markdown_report(response_data, request_params)
                if report_content.strip():
                    saved_report_file = await save_report(report_content, city_name, "hub_expansion")

            analysis_summary = (
                f" **Analysis Parameters**:\n"
                f" **Location**: {city_name}, {country_name}\n"
                f" **Target**: {target_search}\n"
                f" **Hub Type**: {hub_type}\n"
                f" **Competitor**: {competitor_name}\n"
                f" **Results**: Top {top_results_count} locations\n\n"
                + _format_short_response(response_data)
                + f"\n **Data Handle**: `{handle}`"
            )

            if generate_report and saved_report_file:
                analysis_summary += f"\n\n**Report saved to**: {saved_report_file}"

            return json.dumps(
                {
                    "report_file": saved_report_file,
                    "data_files": {},
                    "response": analysis_summary,
                    "metadata": {
                        "analysis_type": "hub_expansion",
                        "city": city_name,
                        "country": country_name,
                        "target": target_search,
                        "competitor": competitor_name,
                        "hub_type": hub_type,
                        "handle": handle,
                        "top_results_count": top_results_count,
                        "report_generated": bool(saved_report_file),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )

        except Exception as e:
            logger.exception("Critical error in hub_expansion_analyzer")
            return json.dumps(
                {
                    "report_file": "",
                    "data_files": {},
                    "response": f" Error processing analysis: {e}",
                    "metadata": {"error": True, "analysis_type": "hub_expansion", "city": city_name},
                },
                ensure_ascii=False,
                indent=2,
            )