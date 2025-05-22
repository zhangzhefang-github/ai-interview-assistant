FROM python:3.13

# Set desired locale (no longer C.UTF-8 directly here, will be set after generation)
# ENV LANG C.UTF-8
# ENV LC_ALL C.UTF-8

WORKDIR /app

# Install locales package, generate zh_CN.UTF-8, then set it as default
RUN apt-get update && apt-get install -y locales curl && \
    echo "zh_CN.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen zh_CN.UTF-8 && \
    update-locale LANG=zh_CN.UTF-8 LC_ALL=zh_CN.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
ENV LANGUAGE zh_CN:en # You can keep en here as a fallback

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
COPY ./app ./app
COPY ./static ./static
# If your streamlit_app needs files from static/, uncomment and adjust:
# COPY ./static ./static

# DO NOT COPY .env file into the image for security reasons.
# Environment variables are passed via docker-compose.yaml.

# Explicitly create and permission a temp directory for uploads (test)
RUN mkdir -p /app/tmp_uploads && chown -R app:app /app/tmp_uploads && chmod -R 755 /app/tmp_uploads
RUN chmod 777 /tmp # Ensure /tmp is world-writable (test)

ENV TMPDIR=/app/tmp_uploads

# Change ownership to the app user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

CMD ["streamlit", "run", "streamlit_app/app_navigator.py", "--server.port=8501", "--server.address=0.0.0.0", "--logger.level=debug"]
