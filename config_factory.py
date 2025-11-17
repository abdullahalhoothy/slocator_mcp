"""
Configuration factory for MCP server.
"""
from pathlib import Path

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
