\
[简体中文](README_zh.md)

# AI Interview Assistant

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add more badges as needed: build status, coverage, etc. -->

AI Interview Assistant is a platform designed to help streamline the interview process by leveraging AI for tasks such as job description analysis, resume parsing, interview question generation, multi-turn interview logging, and comprehensive interview report generation including structured capability assessment.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
  - [Using Docker Compose (Recommended)](#using-docker-compose-recommended)
  - [Local Development (Without Docker)](#local-development-without-docker)
    - [FastAPI Backend](#fastapi-backend)
    - [Streamlit Frontend](#streamlit-frontend)
- [Running Tests](#running-tests)
- [Database Migrations](#database-migrations)
- [Key Development Highlights & Workflow](#key-development-highlights--workflow)
- [Project Structure](#project-structure)
- [Potential Future Enhancements](#potential-future-enhancements)
- [Contributing](#contributing)
- [License](#license)

## Features

-   **Job Management**: Create, read, update, and delete job postings.
-   **Candidate Management**: Create, read, update, and delete candidate profiles, including AI-powered resume parsing for structured data extraction.
-   **Interview Scheduling & Management**: Schedule and manage interview lifecycles (e.g., status updates from pending questions to report generated).
-   **AI-Powered Question Generation**: Automatically generate interview questions based on AI-analyzed job descriptions and candidate resumes.
-   **Interactive Interview Logging**: A chat-style interface for recording multi-turn interview dialogues, associating dialogue with pre-generated questions or ad-hoc inputs.
-   **AI-Powered Interview Reports**: Generate comprehensive interview assessment reports based on interview dialogues, JD, and resume. Includes:
    -   Overall assessment.
    -   Capability dimension analysis with 1-5 scoring.
    -   Strengths and areas for development.
    -   Automated extraction of structured capability scores (e.g., for radar charts).
-   **Report Viewing & Visualization**: Display generated reports and associated radar charts for capability assessment.
-   **Dynamic UI Elements**: Features like dynamically loaded "common follow-up questions" via `st.popover` for enhanced UX.

## Tech Stack

-   **Backend**: FastAPI, Python 3.13+
-   **Frontend**: Streamlit
-   **Database**: MySQL
-   **ORM**: SQLAlchemy
-   **Database Migrations**: Alembic
-   **Dependency Management**: uv
-   **Python Version Management**: pyenv (optional, for consistency)
-   **Testing**: Pytest, `pytest-dotenv`
-   **AI Integrations**: Langchain, OpenAI (or compatible APIs)
-   **Environment Variable Management**: `python-dotenv`

## Prerequisites

-   Python 3.13+ (managed via `pyenv` is recommended for consistency)
-   `pyenv` installed (if used, see [pyenv installation guide](https://github.com/pyenv/pyenv#installation))
-   `uv` installed (see [uv installation guide](https://github.com/astral-sh/uv#installation))
-   MySQL server running and accessible.
-   An OpenAI API key and potentially a base URL if using a proxy or custom endpoint.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <YOUR_REPOSITORY_URL> # Replace with your actual repo URL
    cd ai-interview-assistant
    ```

2.  **Set up Python version using pyenv (recommended):**
    ```bash
    # Ensure .python-version file exists with the target Python version (e.g., 3.13.0)
    pyenv install $(cat .python-version)
    pyenv local $(cat .python-version)
    ```

3.  **Install dependencies using uv:**
    ```bash
    uv pip install -e ".[test]" # Installs main and test dependencies from pyproject.toml
    ```
    *Dependencies are managed via `pyproject.toml` and `uv.lock`.*

## Environment Setup

This project uses a `.env` file for environment variables.

1.  **`.env` File:**
    This file stores sensitive credentials and environment-specific configurations. It is **not** committed to version control (`.gitignore` should list `.env`).
    Create a `.env` file in the project root:
    ```bash
    cp env.example .env # If you provide an env.example, otherwise create manually
    ```
    Populate `.env` with the necessary variables. Key variables include:
    ```ini
    OPENAI_API_KEY="sk-your_openai_api_key_here"
    OPENAI_API_BASE="https://api.openai.com/v1" # Or your custom base URL if applicable

    # Database URL for the main application (FastAPI)
    DATABASE_URL="mysql+pymysql://user:password@host:port/dbname"

    # Database URL for testing (pytest uses this via pytest-dotenv)
    TEST_MYSQL_DATABASE_URL="mysql+pymysql://testuser:testpass@localhost:3306/testdb"

    # Example: API_LOG_LEVEL="INFO"
    ```
    **Important**:
    - Replace placeholders with your actual credentials and database connection strings.
    - Ensure the databases specified (e.g., `dbname`, `testdb`) exist and the users have the necessary permissions.
    - The backend application (`app/main.py`) uses `python-dotenv` to load these variables.
    - Pytest uses `pytest-dotenv` to load these variables during tests, especially `TEST_MYSQL_DATABASE_URL`.
    - When using Docker Compose, these variables are primarily managed through the `docker-compose.yaml` file's `environment` or `env_file` sections for each service.

## Running the Application

### Using Docker Compose (Recommended)

This is the recommended way to run the application as it sets up all services (backend, frontend, database) in isolated containers.

1.  **Ensure Docker and Docker Compose are installed.**
2.  **Build and start the services:**
    From the project root directory:
    ```bash
    docker compose up --build
    ```
    - To run in detached mode (in the background):
      ```bash
      docker compose up --build -d
      ```
3.  **Accessing the services:**
    -   **FastAPI Backend**: `http://localhost:8000`
        -   Swagger UI: `http://localhost:8000/docs`
        -   ReDoc: `http://localhost:8000/redoc`
    -   **Streamlit Frontend**: `http://localhost:8501`
    -   **MySQL Database**: Accessible on `localhost:33066` (as per default `docker-compose.yaml`) by database tools or other services.

4.  **Database Migrations (Alembic):**
    When the application starts for the first time, or if there are new database schema changes, migrations need to be applied. The `backend` service in `docker-compose.yaml` is configured with a command that attempts to run migrations on startup.
    If you need to run migrations manually while the services are running:
    ```bash
    docker compose exec backend alembic upgrade head
    ```
    To generate a new migration (usually done in a local development environment first):
    ```bash
    docker compose exec backend alembic revision --autogenerate -m "Your migration message"
    ```
    Then, after reviewing the script, apply it.

5.  **Viewing logs:**
    ```bash
    docker compose logs -f <service_name> # e.g., backend, frontend, db
    ```

6.  **Stopping the services:**
    ```bash
    docker compose down
    ```

### Local Development (Without Docker)

#### FastAPI Backend

1.  **Ensure your virtual environment (if explicitly managed) is active and `.env` is populated.**
2.  **Run database migrations (if this is the first time or if there are new migrations):**
    ```bash
    alembic upgrade head
    ```
3.  **Start the FastAPI development server using Uvicorn:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    - The API will typically be available at `http://localhost:8000`.
    - Auto-generated API documentation (Swagger UI) will be at `http://localhost:8000/docs`.
    - Alternative documentation (ReDoc) at `http://localhost:8000/redoc`.

### Streamlit Frontend

1.  **Ensure your virtual environment (if explicitly managed) is active and `.env` is populated.** (Streamlit also benefits from `OPENAI_API_KEY` if any direct client-side calls were made, though typically it interacts via the FastAPI backend).
2.  **Run the Streamlit application:**
    ```bash
    python -m streamlit run streamlit_app/app_navigator.py --server.port 8501
    ```
    - The Streamlit app will typically be available at `http://localhost:8501`.

## Running Tests

1.  **Ensure `TEST_MYSQL_DATABASE_URL` in `.env` is correctly configured for your test database.** The `pytest-dotenv` plugin will automatically load variables from `.env`.
2.  **Run the tests using Pytest:**
    ```bash
    pytest
    ```
    - You can run specific tests by specifying the path or markers:
      ```bash
      pytest tests/api/v1/test_interviews.py
      pytest -m "marker_name" # If you use pytest markers
      ```

## Database Migrations

This project uses Alembic for database schema migrations.

-   **To generate a new migration script after making changes to SQLAlchemy models (`app/db/models.py`):**
    It's crucial to use `--autogenerate` to let Alembic detect model changes.
    ```bash
    alembic revision --autogenerate -m "Describe your changes here, e.g., add_conversation_log_to_interviews"
    ```
    Then, review the generated script in the `alembic/versions/` directory. Usually, autogenerated scripts are sufficient, but complex changes might need manual adjustments.

-   **To apply migrations to your database:**
    ```bash
    alembic upgrade head
    ```

-   **To downgrade to a specific version (use with caution):**
    ```bash
    alembic downgrade <version_identifier_or_relative_step_like_-1>
    ```

-   **To see the current database revision:**
    ```bash
    alembic current
    ```

## Key Development Highlights & Workflow

This project evolved through several key stages and problem-solving steps, including recent architectural upgrades and bug fixes:

*   **Enhanced Environment & Testing Setup**:
    *   Integrated `pytest-dotenv` to automatically load environment variables (like `TEST_MYSQL_DATABASE_URL`) from the `.env` file during `pytest` execution. This resolved initial test setup failures and streamlined environment management for testing.
*   **Improved Database & Model Integrity**:
    *   Addressed `sqlalchemy.exc.DataError` for the `Interview.status` field by ensuring that only valid `InterviewStatus` enum members were used during updates (e.g., correcting invalid values like "SCHEDULED").
    *   Rectified Pydantic schema definitions by adding the `updated_at` field to `app.api.v1.schemas.InterviewInDBBase` (and subsequently to `InterviewOutputSchema`), aligning API responses with test assertions and preventing `AssertionError`s due to missing fields.
*   **Increased Test Suite Robustness**:
    *   Corrected `unittest.mock.patch` targets in API tests (e.g., in `tests/api/v1/test_interviews.py`). Mocks for AI services (like `analyze_jd`) were updated to target the path where the function is looked up (e.g., `'app.api.v1.endpoints.interviews.analyze_jd'`) rather than where it's defined, ensuring effective isolation of services during tests.
    *   Refined timestamp assertions, for instance in `test_update_interview_success`, by parsing datetime strings from API responses into timezone-aware `datetime` objects before comparison. This made tests more resilient to minor formatting differences and ensured accurate checks (e.g., `updated_at > created_at`).
*   **LangChain v0.3.x Adaptation**: Updated LangChain usage to align with v0.3.x standards, primarily involving the adoption of the `Runnable` interface and methods like `ainvoke()` for asynchronous chain executions. This enhances compatibility with the latest LangChain features and often improves performance for I/O-bound AI calls. (This complements the existing point on "Asynchronous Operations").
*   **Pydantic V2 Migration**: Upgraded the project to use Pydantic V2. This involves leveraging its improved performance, stricter validation rules, and updated API (e.g., changes in model configuration and field definitions). This ensures the project benefits from the latest data validation and serialization capabilities.

1.  **Initial Setup & Testing**: Ensured basic LLM calls and `pytest` setup. Encountered and resolved test database URL issues by integrating `pytest-dotenv`.
2.  **Core Interview Logic**: Fixed data truncation errors (`DataError` for status) and assertion errors in API tests by aligning test payloads with database schema (e.g., `InterviewStatus` enum) and Pydantic schemas.
3.  **AI Service Mocking**: Corrected mock paths for AI service calls in unit tests to ensure proper isolation.
4.  **Timestamp Handling**: Addressed timestamp comparison issues in tests by parsing strings to timezone-aware datetime objects.
5.  **Environment Variables for Backend**: Resolved OpenAI authentication errors by ensuring `load_dotenv()` is called in `app/main.py` to make `.env` variables available to the backend.
6.  **Structured Interview Logging**:
    -   Evolved from a single `conversation_log` text field to a structured `InterviewLog` table for multi-turn dialogues.
    -   This involved Pydantic schema updates, new API endpoints for log creation/retrieval, and Alembic migrations (`--autogenerate` was key).
7.  **AI Report Generation & Data Extraction**:
    -   Enhanced prompts in `app/core/prompts.py` to instruct AI for Chinese output and structured JSON for capability scores.
    -   Implemented logic in the backend to extract this JSON from the AI's text response and store it separately (e.g., `radar_data` in the `Interview` model).
    -   Refined prompts to constrain AI scoring (1-5 scale) and minimize extraneous text around the JSON block.
8.  **Frontend UX Enhancements (`streamlit_app/`)**:
    -   **Interview Management**: Improved loading indicators and feedback messages (using candidate names, avoiding duplicate icons).
    -   **Interview Logging**:
        -   Transformed the logging page from a single `st.text_area` to an interactive chat interface using `st.chat_message` and `st.chat_input`.
        -   Dynamically loaded "common follow-up questions" from `app/core/prompts.py` and displayed them using `st.popover` to avoid UI clutter.
        -   Improved display of interview selection (showing candidate/job names, Chinese status).
    -   **Report Viewing**: Ensured correct display of AI-generated report text and associated radar chart data.
9.  **Database Schema Evolution**: Handled foreign key constraints (e.g., `ondelete="SET NULL"` for `InterviewLog.question_id`) during schema changes and question regeneration.
10. **Asynchronous Operations**: Migrated AI service calls (e.g., report generation) to use `async` and `await chain.ainvoke()` for better performance and responsiveness, particularly in the FastAPI backend.

## Project Structure

    .
    ├── .dockerignore             # Specifies intentionally untracked files that Docker should ignore
    ├── .git/                     # Git version control metadata
    ├── .gitignore                # Specifies intentionally untracked files that Git should ignore
    ├── .pytest_cache/            # Cache directory for pytest
    ├── .venv/                    # Python virtual environment (if used locally)
    ├── alembic/                  # Alembic migration scripts and environment configuration
    ├── app/                      # Main application source code (FastAPI backend)
    │   ├── api/                  # API specific modules
    │   │   └── v1/               # Version 1 of the API
    │   │       ├── endpoints/    # API route definitions (FastAPI routers)
    │   │       └── schemas.py    # Pydantic schemas for request/response validation and serialization
    │   ├── core/                 # Core application logic, configuration, and prompts
    │   │   ├── config.py         # Application settings (e.g., loading from environment variables)
    │   │   └── prompts.py        # Prompts for AI services (e.g., for Langchain)
    │   ├── db/                   # Database interaction layer
    │   │   ├── models.py         # SQLAlchemy ORM models defining database tables
    │   │   ├── session.py        # Database session management (SQLAlchemy SessionLocal)
    │   │   └── crud/             # CRUD (Create, Read, Update, Delete) operations for models
    │   ├── services/             # Business logic layer, AI service integrations
    │   │   ├── ai_services.py    # Client for interacting with LLMs (e.g., OpenAI via Langchain)
    │   │   └── ai_report_generator.py # Logic for AI report generation
    │   ├── utils/                # Utility functions for the backend
    │   └── main.py               # FastAPI application entry point (creates FastAPI app instance, mounts routers)
    ├── streamlit_app/            # Streamlit frontend application
    │   ├── pages/                # Individual pages of the Streamlit app
    │   ├── utils/                # Frontend specific utilities (e.g., API client)
    │   ├── assets/               # Static assets for the frontend (e.g., images, CSS - if any)
    │   └── app_navigator.py      # Main Streamlit application navigator/entry point
    ├── static/                   # Static files (currently minimal, e.g., test_sse_client.html - may be deprecated or for backend specific static files if any)
    ├── streamlit_tmp/            # Temporary directory, possibly for Streamlit uploads (ensure .gitignore)
    ├── tests/                    # Test suite (Pytest)
    │   ├── api/                  # API tests (testing FastAPI endpoints)
    │   ├── conftest.py           # Pytest fixtures and global test configurations
    │   └── ...                   # Other test modules (e.g., unit tests for services)
    ├── .conda-env                # Conda environment file (if using Conda)
    ├── .envrc                    # direnv environment configuration file (if using direnv)
    ├── .python-version           # pyenv Python version for the project
    ├── alembic.ini               # Alembic configuration file
    ├── docker-compose.yaml       # Docker Compose configuration for running multi-container application
    ├── Dockerfile                # Dockerfile for the backend service (referenced in docker-compose.yaml)
    ├── env.example               # Example environment variables file
    ├── init.sql                  # Initial SQL script for database setup (e.g. for MySQL)
    ├── LICENSE.md / LICENSE      # Project license file(s)
    ├── main.py                   # Minimal top-level main.py (if any, role to be clarified or removed if app.main:app is sole entry)
    ├── migration_sanity_check.py # Script for checking migrations (developer tool)
    ├── pytest.ini                # Pytest configuration file
    ├── pyproject.toml            # Project metadata and dependencies (for Poetry/PEP 517 builds, used by uv)
    ├── README.md                 # This file (English README)
    ├── README_zh.md              # Chinese README
    ├── requirements.txt          # Requirements file (potentially for specific contexts or generated by pip freeze)
    └── uv.lock                   # Lock file for uv, ensuring reproducible builds

## Potential Future Enhancements

-   **Centralize `