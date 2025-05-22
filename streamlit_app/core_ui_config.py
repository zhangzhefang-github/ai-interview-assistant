# streamlit_app/core_ui_config.py
import os

# Get the Backend API URL from environment variable, with a fallback for local development
# Ensure to strip any trailing slashes from the env var before appending /api/v1
raw_backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_API_URL = raw_backend_url.rstrip('/') + "/api/v1" 