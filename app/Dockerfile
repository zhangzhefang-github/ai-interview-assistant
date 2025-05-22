FROM python:3.13-slim

WORKDIR /app

# Create a non-root user and group
RUN groupadd --system app && \
    useradd --system --gid app --shell /bin/bash --home /app app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
# Ensure uv is in PATH for this RUN command, /usr/local/bin should be.
RUN uv sync && \
    rm -rf /root/.cache # Clean uv cache

ENV PATH="/app/.venv/bin:$PATH"

# Verify installations and PATH
RUN echo "--- Checking installations and PATH (after uv sync and PATH update) ---" && \
    echo "Current PATH: $PATH" && \
    echo "Verifying alembic:" && \
    (which alembic && alembic --version) || echo "Alembic not found or --version failed" && \
    echo "Verifying uvicorn:" && \
    (which uvicorn && uvicorn --version) || echo "Uvicorn not found or --version failed" && \
    echo "Listing /app/.venv/bin to see available executables:" && \
    ls -l /app/.venv/bin || echo "/app/.venv/bin not found or is empty" && \
    echo "--- Finished checking ---"

# 初始化数据库表
COPY ./app/wait_for_db.py /app/wait_for_db.py

# Copy application code
# Copy only what's needed for the backend to run
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Set PYTHONPATH if necessary (though with WORKDIR /app, it might not be needed for direct imports)
ENV PYTHONPATH=/app

# Copy the entrypoint script and give it execution permissions
COPY ./app/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Change ownership to the app user
# Ensure the entrypoint script is also owned by app user if it needs to operate in that context primarily,
# or keep it root-owned if it needs root privileges for some initial setup before switching to app user in script.
# For now, let's make sure /app is fully owned by app user.
RUN chown -R app:app /app

# Switch to the non-root user
USER app

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl --fail http://localhost:8000/docs || exit 1

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
# CMD is not strictly needed if ENTRYPOINT is an executable script that runs the main process.
# If CMD were present, it would be passed as arguments to ENTRYPOINT.
