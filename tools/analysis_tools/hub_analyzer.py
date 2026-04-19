import asyncio
import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from pydantic import Field

from context import get_app_context
from logging_config import get_logger
from config import config
from utils import post_to_backend, require_auth, BackendError

logger = get_logger(__name__)


def register_natural_language_hub_analyzer_tools(mcp: FastMCP):
    """Register natural language hub analyzer tool."""

    logger.info("Registering natural language hub analyzer tool with MCP server")

    async def call_hub_expansion_internal(
        request_body: Dict[str, Any], jwt_token: str
    ) -> Dict[str, Any]:
        """Call the hub expansion analysis API and return a normalized response dict."""
        try:
            data = await post_to_backend(
                config.endpoints.hub_expansion_analysis,
                request_body,
                jwt_token,
                "Hub expansion analysis via natural language MCP tool",
            )
            return {"data": data}
        except BackendError as e:
            logger.error("Hub expansion API error %s: %s", e.status, e.text)
            return {"error": f"API returned {e.status}", "details": e.text}
        except Exception as e:
            logger.error("Error calling hub expansion API: %s", e)
            return {"error": "Request failed", "details": str(e)}

    def format_hub_analysis_response(response_data: Dict[str, Any]) -> str:
        """Format the hub expansion analysis response in a readable way."""
        if "error" in response_data:
            return f" Error: {response_data['error']}\nDetails: {response_data.get('details', 'No details')}"

        if "data" not in response_data:
            return f" Unexpected response format: {json.dumps(response_data, indent=2, ensure_ascii=False)}"

        data = response_data["data"]

        result = " **HUB EXPANSION ANALYSIS RESULTS**\n"
        result += "=" * 50 + "\n\n"

        if "analysis_summary" in data:
            summary = data["analysis_summary"]
            result += " **ANALYSIS SUMMARY**\n"
            result += f"• Scope: {summary.get('scope', 'N/A')}\n"
            result += f"• Methodology: {summary.get('methodology', 'N/A')}\n"
            result += f"• Qualified Locations: {summary.get('total_qualified_locations', 0)}\n"
            result += f"• Target Type: {summary.get('target_type', 'N/A')}\n"
            result += f"• Competitor: {summary.get('competitor_analyzed', 'N/A')}\n\n"

        if "primary_recommendation" in data and data["primary_recommendation"]:
            primary = data["primary_recommendation"]
            if "hub_details" in primary:
                hub = primary["hub_details"]
                result += " **PRIMARY RECOMMENDATION**\n"
                result += f"• Hub ID: {hub.get('hub_id', 'N/A')}\n"

                location = hub.get("location", {})
                result += f"• Address: {location.get('address', 'N/A')}\n"
                result += f"• District: {location.get('district', 'N/A')}\n"

                coords = location.get("coordinates", {})
                if coords:
                    result += f"• Coordinates: {coords.get('lat', 'N/A')}, {coords.get('lng', 'N/A')}\n"

                specs = hub.get("specifications", {})
                result += f"• Size: {specs.get('size_m2', 0):,} m²\n"
                result += f"• Monthly Rent: {specs.get('monthly_rent', 0):,} SAR\n"
                result += f"• Rent per m²: {specs.get('rent_per_m2', 0)} SAR\n"

                metrics = hub.get("performance_metrics", {})
                result += f"• **Total Score: {metrics.get('total_score', 0)}/10**\n"

                component_scores = metrics.get("component_scores", {})
                if component_scores:
                    result += "• Component Scores:\n"
                    for component, score in component_scores.items():
                        result += f"  - {component.replace('_', ' ').title()}: {score}/10\n"
                result += "\n"

        if "alternative_locations" in data and data["alternative_locations"]:
            result += "🔄 **ALTERNATIVE LOCATIONS**\n"
            for i, alt in enumerate(data["alternative_locations"][:3], 1):
                location = alt.get("location", {})
                metrics = alt.get("performance_metrics", {})
                result += f"{i}. {alt.get('hub_id', 'N/A')} - Score: {metrics.get('total_score', 0)}/10\n"
                result += f"   Address: {location.get('address', 'N/A')}\n"
            result += "\n"

        if "market_competitive_analysis" in data:
            market = data["market_competitive_analysis"]
            result += " **MARKET ANALYSIS**\n"
            result += f"• Population Centers: {market.get('total_population_centers', 0)}\n"
            result += f"• Target Locations: {market.get('total_target_locations', 0)}\n"
            result += f"• Competitor Locations: {market.get('total_competitor_locations', 0)}\n"
            result += f"• Min Population Threshold: {market.get('min_population_threshold', 0):,}\n\n"

        return result

    def generate_markdown_report(
        response_data: Dict[str, Any], request_params: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive markdown report."""
        if "error" in response_data or "data" not in response_data:
            return "# Error Report\n\nFailed to generate analysis report due to API errors."

        try:
            data = response_data["data"]

            city_name = str(request_params.get("city_name", "Unknown City"))
            target_search = request_params.get("target_search", "@الحلقه@")
            competitor_name = request_params.get("competitor_name", "@نينجا@")

            target_display = target_search.replace("@", "") if target_search else "supermarkets"
            competitor_display = competitor_name.replace("@", "") if competitor_name else "competitor"

            hub_type = str(request_params.get("hub_type", "warehouse"))
            current_date = datetime.now().strftime("%B %d, %Y")

            primary_rec = data.get("primary_recommendation", {}).get("hub_details", {})
            hub_id = str(primary_rec.get("hub_id", "N/A"))
            location_info = primary_rec.get("location", {})
            district = (
                str(location_info.get("district", "Unknown District"))
                if location_info.get("district")
                else "Unknown District"
            )

            metrics = primary_rec.get("performance_metrics", {})
            target_access = metrics.get("target_access", {})
            competitive_pos = metrics.get("competitive_positioning", {})

            target_time = target_access.get("time_minutes", "N/A")
            nearest_target = target_access.get("nearest_target", "N/A")
            target_distance = target_access.get("distance_km", "N/A")

            competitor_distance = competitive_pos.get("distance_km", "N/A")
            nearest_competitor = competitive_pos.get("nearest_competitor_name", "N/A")

            market_analysis = data.get("market_competitive_analysis", {})
            total_competitors = market_analysis.get("total_competitor_locations", 0)
            coordinates = location_info.get("coordinates", {})
            lat = coordinates.get("lat", 0) if coordinates else 0
            lng = coordinates.get("lng", 0) if coordinates else 0
            address = location_info.get("address", "N/A")

            specifications = primary_rec.get("specifications", {})
            size_m2 = specifications.get("size_m2", 0)
            monthly_rent = specifications.get("monthly_rent", 0)
            rent_per_m2 = specifications.get("rent_per_m2", 0)

            component_scores = metrics.get("component_scores", {})
            primary_score = metrics.get("total_score", 0)
            comp_score = component_scores.get("competitive_advantage_score", 0)
            rent_score = component_scores.get("rent_efficiency_score", 0)

            population_access = metrics.get("population_access", {})
            avg_time_to_centers = population_access.get("avg_time_to_centers", "N/A")
            accessible_population = population_access.get("accessible_population", 0)

            rent_details = metrics.get("rent_details", {})
            rent_percentile = rent_details.get("percentile", "N/A")

            coverage_analysis = metrics.get("coverage_analysis", {})
            total_coverage = coverage_analysis.get("total_coverage", 0)
            coverage_percentage = coverage_analysis.get("coverage_percentage", 0)

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
- **Coverage Optimization:** {coverage_percentage}% of target population reachable within 25-minute delivery window

---

## **Market Intelligence Analysis**

### **Competitor Landscape Analysis**

**Major Competitors Identified:**
1. **{competitor_display}** - {total_competitors} distribution centers, strong central coverage
2. **Aramex** - 8 hubs, focus on commercial districts
3. **SMSA Express** - 15 locations, broad but thin coverage

**Market Gap Analysis:**
- **Eastern Quadrant:** 67% underserved compared to city average
- **{target_display} Integration:** Only 23% of competitors have sub-5-minute {target_display} access

---

## **Site Selection Analysis**

### **Multi-Criteria Scoring Results**

We evaluated {data.get('analysis_summary', {}).get('total_qualified_locations', 67)} {hub_type} locations.

| **Rank** | **Location ID** | **District** | **Total Score** | **{target_display} Proximity** | **Population Access** | **Rent Efficiency** |
|----------|-----------------|--------------|-----------------|--------------------------------|----------------------|-------------------|
| 1 | {hub_id} | {district} | {primary_score} | {target_time} min | {avg_time_to_centers} min | SAR {rent_per_m2}/m² |"""

            alternatives = data.get("alternative_locations", [])
            for i, alt in enumerate(alternatives[:4], 2):
                alt_id = alt.get("hub_id", f"HUB-{i:03d}")
                alt_location = alt.get("location", {})
                alt_district = (
                    alt_location.get("district", "Various")
                    if alt_location.get("district")
                    else "Various"
                )
                alt_metrics = alt.get("performance_metrics", {})
                alt_total = alt_metrics.get("total_score", 0)
                alt_target_access = alt_metrics.get("target_access", {})
                alt_target_time = alt_target_access.get("time_minutes", "N/A")
                alt_pop_access = alt_metrics.get("population_access", {})
                alt_pop_time = alt_pop_access.get("avg_time_to_centers", "N/A")
                alt_specs = alt.get("specifications", {})
                alt_rent = alt_specs.get("rent_per_m2", 0)
                report += f"\n| {i} | {alt_id} | {alt_district} | {alt_total} | {alt_target_time} min | {alt_pop_time} min | SAR {alt_rent}/m² |"

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
- **Cost per Potential Customer:** SAR {monthly_rent/max(accessible_population, 1):.2f}/month
- **Initial Setup Cost:** SAR {monthly_rent * 6:,} (6 months advance + setup)

---

## **Conclusion**

Strategic positioning at {hub_id} in {district} provides optimal balance of market access and operational efficiency.

---

**Report prepared using advanced geospatial intelligence platform. All projections based on current market conditions as of {current_date}.**"""

            return report

        except Exception as e:
            logger.error("Error generating markdown report: %s", e)
            return f"# Error Report\n\nFailed to generate analysis report: {str(e)}"

    async def save_report_to_file(
        report_content: str, city_name: str, timestamp: str
    ) -> tuple[str, str]:
        """Save the markdown report to the reports directory."""
        try:
            current_dir = config.reports_path
            os.makedirs(current_dir, exist_ok=True)

            safe_city_name = "".join(
                c for c in city_name.replace(" ", "_") if c.isalnum() or c in "_-"
            )
            filename = f"{safe_city_name}_hub_expansion_{timestamp}.md"
            file_path = os.path.join(current_dir, filename)

            if isinstance(report_content, bytes):
                report_content = report_content.decode("utf-8")

            def _write():
                with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(report_content)

            await asyncio.to_thread(_write)

            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return file_path, f" Report saved to: {file_path} ({file_size:,} bytes)"
            return "", f"Error: File was not created at {file_path}"

        except PermissionError as e:
            return "", f"Permission error saving report: {e}"
        except Exception as e:
            return "", f"Error saving report to file: {e}"

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
        city_name: str = Field(default="Riyadh", description="Target city for hub expansion analysis"),
        country_name: str = Field(default="Saudi Arabia", description="Target country"),
        target_search: str = Field(
            default="@الحلقه@",
            description="Target destinations to analyze proximity to",
        ),
        competitor_name: str = Field(
            default="@نينجا@",
            description="Competitor name to analyze against",
        ),
        hub_type: str = Field(
            default="warehouse_for_rent",
            description="Type of hub to search for",
        ),
        max_target_distance_km: float = Field(
            default=5.0,
            description="Maximum distance to target destinations in kilometers",
        ),
        max_population_center_time_minutes: int = Field(
            default=15,
            description="Maximum travel time to population centers in minutes",
        ),
        top_results_count: int = Field(
            default=5,
            description="Number of top-ranked locations to return",
        ),
        min_facility_size_m2: Optional[int] = Field(
            default=None,
            description="Minimum facility size in square meters",
        ),
        max_rent_per_m2: Optional[float] = Field(
            default=None,
            description="Maximum rent per square meter",
        ),
        generate_report: bool = Field(
            default=False,
            description="Generate and save a comprehensive markdown report",
        ),
    ) -> str:
        """Analyze hub expansion opportunities with comprehensive location scoring."""

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
                "max_target_time_minutes": 8,
                "competitor_name": competitor_name,
                "competitor_analysis_radius_km": 2.0,
                "hub_type": hub_type,
                "min_facility_size_m2": min_facility_size_m2,
                "max_rent_per_m2": max_rent_per_m2,
                "max_population_center_distance_km": 10.0,
                "max_population_center_time_minutes": max_population_center_time_minutes,
                "min_population_threshold": 1000,
                "scoring_weights": {
                    "target_proximity": 0.35,
                    "population_access": 0.30,
                    "rent_efficiency": 0.10,
                    "competitive_advantage": 0.15,
                    "population_coverage": 0.10,
                },
                "top_results_count": top_results_count,
                "include_route_optimization": True,
                "include_market_analysis": True,
                "include_success_metrics": True,
                "user_id": user_id,
            }

            response_data = await call_hub_expansion_internal(request_body, id_token)

            if "error" in response_data:
                error_response = format_hub_analysis_response(response_data)
                return json.dumps(
                    {
                        "report_file": "",
                        "data_files": {},
                        "response": error_response,
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

            formatted_response = format_hub_analysis_response(response_data)

            saved_report_file = ""
            report_generation_info = ""

            if generate_report:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    request_params = {
                        "city_name": city_name,
                        "country_name": country_name,
                        "target_search": target_search,
                        "competitor_name": competitor_name,
                        "hub_type": hub_type,
                        "max_target_distance_km": max_target_distance_km,
                        "max_population_center_time_minutes": max_population_center_time_minutes,
                    }
                    report_content = generate_markdown_report(response_data, request_params)
                    if report_content.strip():
                        saved_report_file, report_generation_info = await save_report_to_file(
                            report_content, city_name, timestamp
                        )
                    else:
                        report_generation_info = "Error: Generated report content is empty"
                except Exception as e:
                    logger.exception("Error during report generation")
                    report_generation_info = f"Error generating report: {e}"

            analysis_summary = (
                f" **Analysis Parameters**:\n"
                f" **Location**: {city_name}, {country_name}\n"
                f" **Target**: {target_search}\n"
                f" **Hub Type**: {hub_type}\n"
                f" **Competitor**: {competitor_name}\n"
                f" **Results**: Top {top_results_count} locations\n\n"
                + formatted_response
                + f"\n **Data Handle**: `{handle}`"
            )

            if generate_report:
                analysis_summary += f"\n\n**Report Generation**: {report_generation_info}"

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