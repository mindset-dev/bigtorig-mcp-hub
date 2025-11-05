FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files (including README.md required by pyproject.toml)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies with UV
# Note: uv lock generates uv.lock, then sync installs from it
RUN uv lock && uv sync --frozen --no-dev

# Expose the MCP server port
EXPOSE 8000

# Health check - checks if server is responding on port 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8000)); s.close()" || exit 1

# Run the server
CMD ["uv", "run", "python", "src/server.py"]
