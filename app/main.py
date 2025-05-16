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
    print(f"Attempting to create database tables for URL: {SQLALCHEMY_DATABASE_URL}")
    try:
        create_db_and_tables() # This function is synchronous, run it directly
        print("Database tables checked/created during startup.")
    except Exception as e:
        print(f"Error creating database tables during startup: {e}")
        # Handle error appropriately, maybe raise to stop app or log critical error
    yield
    # Code to run on shutdown (if any)
    print("Application shutdown.")

app = FastAPI(
    title="AI Interview Assistant API",
    lifespan=lifespan # Pass the lifespan context manager
)

# @app.on_event("startup") # This is now handled by lifespan
# async def startup_event():
#     create_tables_on_startup()

app.include_router(jobs_router.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(candidates_router.router, prefix="/api/v1/candidates", tags=["Candidates"]) # Include candidates router
app.include_router(interviews_router.router, prefix="/api/v1/interviews", tags=["Interviews"]) # Include interviews router

@app.get("/ping", tags=["Health"])
async def ping():
    return {"ping": "pong!"}

# To run this app (from the project root directory):
# uvicorn app.main:app --reload 