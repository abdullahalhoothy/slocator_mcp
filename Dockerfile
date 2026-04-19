# Use Python 3.13 slim image for MCP Server (matches requires-python in pyproject.toml)
FROM python:3.13-slim

# Install system dependencies (curl needed for health check)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        gcc \
        g++ \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml ./

# Install dependencies (fall back to pip if uv.lock is absent)
RUN uv pip install --system -e . 2>/dev/null || pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Create runtime directories
RUN mkdir -p sessions reports logs

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose MCP Server port
EXPOSE 8001

# Health check via SSE endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/sse || exit 1

# Run MCP Server with SSE transport
CMD ["python", "mcp_server.py"]