# --- START OF FILE pharmacy_report_tool.py ---

import aiohttp
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import Field, BaseModel

# Add parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from context import get_app_context
from logging_config import get_logger

# Import Config for proper directory paths
from config_factory import Config


logger = get_logger(__name__)

# API URL - Use BACKEND_URL env var for Docker, default to localhost:8000 for local dev
API_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Report URL: Hardcoded to localhost:8000 for browser-accessible links
REPORT_BASE_URL = "http://localhost:8000"

# Hardcoded report path using project root pattern like config.py (Legacy - kept for reference)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HARDCODED_REPORT_PATH = PROJECT_ROOT / "reports" / "pharmacy_report" / "report.md"

# Define models for tool parameters
class Coordinate(BaseModel):
    """Coordinate model for locations"""
    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")

class EvaluationMetrics(BaseModel):
    """Evaluation metrics for pharmacy site scoring"""
    traffic: float = Field(default=25.0, description="Traffic score weight (default: 25.0)")
    demographics: float = Field(default=30.0, description="Demographics score weight (default: 30.0)")
    competition: float = Field(default=15.0, description="Competition score weight (default: 15.0)")
    healthcare: float = Field(default=20.0, description="Healthcare score weight (default: 20.0)")
    complementary: float = Field(default=10.0, description="Complementary businesses score weight (default: 10.0)")

def register_pharmacy_report_tools(mcp: FastMCP):
    """Register pharmacy report generation tool."""

    logger.info("Registering pharmacy report tool with MCP server")

    async def call_pharmacy_report_api(request_body: Dict[str, Any], jwt_token: str) -> Dict[str, Any]:
        """Call the pharmacy report API internally"""
        url = f"{API_BASE_URL}/fastapi/smart_pharmacy_report"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jwt_token}"
        }

        request_payload = {
            "message": "Pharmacy site analysis via MCP tool",
            "request_info": {},
            "request_body": request_body
        }

        logger.info(f"Calling pharmacy report API: {url}")
        logger.info(f"Request body: {json.dumps(request_body, indent=2)}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=request_payload, headers=headers) as response:
                    logger.info(f"Pharmacy API response status: {response.status}")

                    if response.status == 200:
                        response_data = await response.json()
                        logger.info("Pharmacy API call successful")
                        return response_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Pharmacy API error: {response.status} - {error_text}")
                        return {"error": f"API returned {response.status}", "details": error_text}

        except Exception as e:
            logger.error(f"Error calling pharmacy API: {e}")
            return {"error": "Request failed", "details": str(e)}

    def generate_dynamic_markdown_report(city_name: str, html_file_path: str) -> str:
        """Generate markdown report with dynamic link extracted from API response"""
        try:
            current_date = datetime.now().strftime("%B %d, %Y")

            # Convert file system path to web-accessible URL with full backend URL
            # Extract the relative path from the reports directory
            if "reports" in html_file_path:
                # Find the reports directory and get everything after it
                parts = html_file_path.split("reports")
                if len(parts) > 1:
                    relative_path = parts[-1].replace("\\", "/").lstrip("/")
                    # Use hardcoded localhost:8000 for browser-accessible URLs
                    web_url = f"{REPORT_BASE_URL}/static/reports/{relative_path}"
                else:
                    web_url = html_file_path
            else:
                web_url = html_file_path

            logger.info(f"Generated web URL: {web_url} from file path: {html_file_path}")
            logger.info(f"Using API URL: {API_BASE_URL}, Report URL: {REPORT_BASE_URL}")

            # Generate report with clickable link to full report
            report = f"""# Pharmacy Site Analysis Report - {city_name}

Analysis completed for {city_name} on {current_date}.

[Click here to see full report]({web_url})

---
Generated by Geospatial Intelligence Platform
"""
            return report

        except Exception as e:
            logger.error(f"Error generating dynamic markdown report: {str(e)}")
            return f"# Pharmacy Report Error\n\nFailed to generate report: {str(e)}"


    async def save_report_to_file(report_content: str, city_name: str, timestamp: str) -> tuple[str, str]:
        """Save the markdown report to the reports directory"""
        try:
            reports_dir = Config.get_reports_path()
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename
            safe_city_name = city_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_city_name = ''.join(c for c in safe_city_name if c.isalnum() or c in '_-')
            
            filename = f"{safe_city_name}_pharmacy_report_{timestamp}.md"
            file_path = os.path.join(reports_dir, filename)
            
            # Save the report
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"Report saved successfully: {filename}")
            return filename, f"Report saved: {filename}"
                
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            return "", f"Error saving report: {str(e)}"

    @mcp.tool(
        name="generate_pharmacy_report",
        description="""Generate comprehensive pharmacy site selection reports with real-time analysis.

        Analyzes locations based on multiple criteria including traffic, demographics, competition,
        healthcare ecosystem, and complementary businesses. Supports custom locations and evaluation metrics.

        Returns a detailed pharmacy site analysis report with rankings and investment recommendations.
        """,
    )
    async def generate_pharmacy_report(
        city_name: str = Field(
            default="Riyadh",
            description="Target city for pharmacy site analysis"
        ),
        country_name: str = Field(
            default="Saudi Arabia",
            description="Target country"
        ),
        traffic_weight: float = Field(
            default=25.0,
            description="Weight for traffic score (0-100)"
        ),
        demographics_weight: float = Field(
            default=30.0,
            description="Weight for demographics score (0-100)"
        ),
        competition_weight: float = Field(
            default=15.0,
            description="Weight for competition score (0-100)"
        ),
        healthcare_weight: float = Field(
            default=20.0,
            description="Weight for healthcare ecosystem score (0-100)"
        ),
        complementary_weight: float = Field(
            default=10.0,
            description="Weight for complementary businesses score (0-100)"
        ),
        custom_locations_json: Optional[str] = Field(
            default=None,
            description='Optional JSON string of custom locations to analyze, e.g., \'[{"lat": 24.7136, "lng": 46.6753}]\''
        ),
        current_location_json: Optional[str] = Field(
            default=None,
            description='Optional JSON string of current location to analyze, e.g., \'{"lat": 24.7136, "lng": 46.6753}\''
        ),
    ) -> str:
        """Generate pharmacy site selection analysis using real-time API."""

        try:
            # Authentication check
            app_ctx = get_app_context(mcp)
            session_manager = app_ctx.session_manager
            user_id, id_token = await session_manager.get_valid_id_token()
            if not id_token or not user_id:
                return "Error: You are not logged in. Please use the `user_login` tool first."

            logger.info(f"Generating pharmacy report for {city_name}, {country_name}")
            logger.info(f"Evaluation weights: traffic={traffic_weight}, demographics={demographics_weight}, competition={competition_weight}, healthcare={healthcare_weight}, complementary={complementary_weight}")

            # Parse custom locations if provided
            custom_locations = None
            if custom_locations_json:
                try:
                    custom_locations_data = json.loads(custom_locations_json)
                    custom_locations = [{"lat": loc["lat"], "lng": loc["lng"]} for loc in custom_locations_data]
                    logger.info(f"Parsed {len(custom_locations)} custom locations")
                except Exception as e:
                    logger.error(f"Error parsing custom_locations_json: {e}")

            # Parse current location if provided
            current_location = None
            if current_location_json:
                try:
                    current_location = json.loads(current_location_json)
                    logger.info(f"Parsed current location: {current_location}")
                except Exception as e:
                    logger.error(f"Error parsing current_location_json: {e}")

            # Build request body matching Reqsmartreport schema
            request_body = {
                "user_id": user_id,
                "city_name": city_name,
                "country_name": country_name,
                "potential_business_type": "pharmacy",
                "ecosystem_string_name": "healthcare",
                "target_income_level": "medium",
                "target_age": 30,
                "analysis_radius": 1000,
                "complementary_categories": ["hospital", "dentist"],
                "optimal_num_complementary_businesses_per_category": 2,
                "cross_shopping_categories": ["grocery_store", "supermarket"],
                "optimal_num_cross_shopping_businesses_per_category": 3,
                "competition_categories": ["pharmacy"],
                "max_competition_threshold_per_category": 1,
                "evaluation_metrics": {
                    "traffic": traffic_weight / 100.0,  # Convert from 0-100 to 0-1 scale
                    "demographics": demographics_weight / 100.0,
                    "competition": competition_weight / 100.0,
                    "complementary": (healthcare_weight + complementary_weight) / 200.0,  # Combine for now
                    "cross_shopping": 0.1  # Default value
                }
            }

            # Add optional parameters if provided
            if custom_locations:
                request_body["custom_locations"] = custom_locations
            if current_location:
                request_body["current_location"] = current_location

            # Call the pharmacy report API
            logger.info("Calling pharmacy report API...")
            api_response = await call_pharmacy_report_api(request_body, id_token)

            # Check for API errors
            if "error" in api_response:
                error_result = {
                    "report_file": "",
                    "data_files": {},
                    "response": f"❌ API Error: {api_response['error']}\nDetails: {api_response.get('details', 'No details')}",
                    "metadata": {
                        "error": True,
                        "analysis_type": "pharmacy_site_selection",
                        "city": city_name
                    }
                }
                return json.dumps(error_result, ensure_ascii=False, indent=2)

            # Extract html_file_path from API response
            # The API returns: {'data': {'html_file_path': ...}, 'message': ..., 'request_id': ...}
            html_file_path = api_response.get("data", {}).get("html_file_path", "")

            if not html_file_path:
                logger.warning("No html_file_path found in API response, using default")
                html_file_path = str(HARDCODED_REPORT_PATH)

            # Convert Path object to string if necessary
            html_file_path = str(html_file_path)

            logger.info(f"Extracted HTML file path: {html_file_path}")

            # Generate timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Generate the report content with dynamic link
            report_content = generate_dynamic_markdown_report(city_name, html_file_path)

            # Save the report to file
            report_filename, save_message = await save_report_to_file(report_content, city_name, timestamp)
            
            if not report_filename:
                error_result = {
                    "report_file": "",
                    "data_files": {},
                    "response": f"❌ Error: {save_message}",
                    "metadata": {
                        "error": True,
                        "analysis_type": "pharmacy_site_selection",
                        "city": city_name
                    }
                }
                return json.dumps(error_result, ensure_ascii=False, indent=2)
            
            # Build response
            analysis_summary = f"✅ Pharmacy site analysis report generated for {city_name}, {country_name}.\n"
            analysis_summary += f"📄 Report: {report_filename}\n"
            analysis_summary += f"🔗 {save_message}\n"
            analysis_summary += f"📊 HTML Report: {html_file_path}"

            # Get full path to the saved report
            reports_dir = Config.get_reports_path()
            full_report_path = os.path.join(reports_dir, report_filename)

            # Return structured JSON format compatible with DashApp
            result = {
                "report_file": str(full_report_path),  # Full path for DashApp to read
                "data_files": {},
                "response": analysis_summary,
                "metadata": {
                    "analysis_type": "pharmacy_site_selection",
                    "city": city_name,
                    "country": country_name,
                    "report_generated": True,
                    "hardcoded_report": False,
                    "html_file_path": html_file_path,
                    "api_call": True,
                    "evaluation_weights": {
                        "traffic": traffic_weight,
                        "demographics": demographics_weight,
                        "competition": competition_weight,
                        "healthcare": healthcare_weight,
                        "complementary": complementary_weight
                    }
                }
            }
            return json.dumps(result, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.exception(f"Error serving pharmacy report: {str(e)}")
            error_result = {
                "report_file": "",
                "data_files": {},
                "response": f"❌ Error: Failed to serve pharmacy report: {str(e)}",
                "metadata": {
                    "error": True,
                    "analysis_type": "pharmacy_site_selection",
                    "city": city_name
                }
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)