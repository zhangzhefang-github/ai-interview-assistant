import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Optional debug logs
print(f"DEBUG main.py after load_dotenv: OPENAI_API_KEY is set: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"DEBUG main.py after load_dotenv: OPENAI_API_BASE from env: {os.getenv('OPENAI_API_BASE')}")
print(f"DEBUG main.py after load_dotenv: DATABASE_URL from env: {os.getenv('DATABASE_URL')}")

import importlib.util
from contextlib import asynccontextmanager

print("---- Uvicorn Python Environment ----")
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("sys.path:")
for p in sys.path:
    print(f"  - {p}")

print("\nAttempting to find mysqlclient spec:")
mysqlclient_spec = importlib.util.find_spec("MySQLdb")
if mysqlclient_spec:
    print(f"MySQLdb (mysqlclient) spec found at: {mysqlclient_spec.origin}")
else:
    print("MySQLdb (mysqlclient) spec NOT found by importlib.util.find_spec.")

print("----------------------------------")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.endpoints import jobs as jobs_router
from app.api.v1.endpoints import candidates as candidates_router # Import candidates router
from app.api.v1.endpoints import interviews as interviews_router # Import interviews router
from app.db.session import create_db_and_tables, SQLALCHEMY_DATABASE_URL # For startup event

# Create database tables on startup if they don't exist
# In a production environment, you would typically use Alembic migrations.
# For this example, we'll call it directly.
# IMPORTANT: Ensure your database server is running and the database itself (e.g., ai_interview_assistant_db)
# has been created manually before running this for the first time with MySQL.

# Lifespan context manager
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Code to run on startup
    # print(f"Attempting to create database tables for URL: {SQLALCHEMY_DATABASE_URL}") # Commented out
    # try:
    #     create_db_and_tables() # This function is synchronous, run it directly # Commented out
    #     print("Database tables checked/created during startup.") # Commented out
    # except Exception as e:
    #     print(f"Error creating database tables during startup: {e}") # Commented out
        # Handle error appropriately, maybe raise to stop app or log critical error
    print("Application startup: Database schema management is now fully handled by Alembic.")
    yield
    # Code to run on shutdown (if any)
    print("Application shutdown.")

app = FastAPI(
    title="AI Interview Assistant API",
    lifespan=lifespan # Pass the lifespan context manager
)

# Add CORS middleware
# IMPORTANT: This should be placed before any routers are included if you want CORS headers to apply to them.
origins = [
    "http://localhost",              # For local development if you use localhost
    "http://localhost:3000",         # Common port for React dev servers
    "http://127.0.0.1",              # For local development if you use 127.0.0.1
    "http://127.0.0.1:3000",         # Common port for Streamlit/other Python web apps dev servers
    "http://localhost:8501",         # Default Streamlit port if run directly
    "http://127.0.0.1:8501",         # Default Streamlit port if run directly
    # Add any other origins your frontend might be served from
    # For development, you might use "*" to allow all origins, but be more restrictive in production.
    # "*" # Allow all origins - USE WITH CAUTION IN PRODUCTION
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],  # MODIFIED: Explicitly specify frontend origins
    allow_credentials=True,
    allow_methods=["*"], # Allow all methods (GET, POST, etc.)
    allow_headers=["*"]  # Allow all headers
)

# @app.on_event("startup") # This is now handled by lifespan
# async def startup_event():

app.include_router(jobs_router.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(candidates_router.router, prefix="/api/v1/candidates", tags=["Candidates"]) # Include candidates router
app.include_router(interviews_router.router, prefix="/api/v1/interviews", tags=["Interviews"]) # Include interviews router

# app.mount("/static", StaticFiles(directory="static"), name="static") # Commented out as per user confirmation

@app.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong!"}

# To run this app (from the project root directory):
# uvicorn app.main:app --reload 