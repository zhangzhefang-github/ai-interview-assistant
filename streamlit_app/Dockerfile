FROM python:3.13-slim

WORKDIR /app

# Create a non-root user and group
RUN groupadd --system app && \
    useradd --system --gid app --shell /bin/bash --home /app app

# Copy only necessary files for dependency installation first
COPY ./pyproject.toml ./uv.lock ./

# Install dependencies
# Using --system to install into the system site-packages
# Clean up caches to reduce image size
RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e . && \
    rm -rf /root/.cache/pip

# Copy only the Streamlit application code
COPY ./streamlit_app ./streamlit_app
# If your streamlit_app needs files from static/, uncomment and adjust:
# COPY ./static ./static

# DO NOT COPY .env file into the image for security reasons.
# Environment variables are passed via docker-compose.yaml.

# Change ownership to the app user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

CMD ["streamlit", "run", "streamlit_app/app_navigator.py", "--server.port=8501", "--server.address=0.0.0.0"]
