FROM python:3.13-slim

WORKDIR /app

# Create a non-root user and group
RUN groupadd --system app && \
    useradd --system --gid app --shell /bin/bash --home /app app

# Copy only necessary files for dependency installation first
COPY pyproject.toml uv.lock ./

# Install dependencies
# Using --system to install into the system site-packages, which is fine for a container
# Clean up caches to reduce image size
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e ".[test]" && \
    rm -rf /root/.cache/pip

# Copy application code
# Copy only what's needed for the backend to run
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .
# If your app/main.py or other parts of app/ need files from static/, uncomment and adjust:
# COPY ./static ./static

# Set PYTHONPATH if necessary (though with WORKDIR /app, it might not be needed for direct imports)
ENV PYTHONPATH=/app

# Change ownership to the app user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
