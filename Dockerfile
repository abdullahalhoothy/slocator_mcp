# Use Python 3.11 slim image for MCP Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app/MCP_Server

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
        git \
        build-essential \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Create reports directory (will be mounted as volume)
RUN mkdir -p reports

# Create sessions directory
RUN mkdir -p sessions

# Expose MCP Server port
EXPOSE 8001

# Run MCP Server with SSE transport
CMD ["uv", "run", "python", "mcp_server.py"]