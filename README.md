\
[简体中文](README.zh-CN.md) <!-- Placeholder, will be verified/added later -->

# AI Interview Assistant

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
<!-- Add more badges as needed: build status, coverage, etc. -->

<YOUR_PROJECT_DESCRIPTION_HERE>

AI Interview Assistant is a platform designed to help streamline the interview process by leveraging AI for tasks such as question generation, job description analysis, resume parsing, and interview report generation.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Running the Application](#running-the-application)
  - [FastAPI Backend](#fastapi-backend)
  - [Streamlit Frontend](#streamlit-frontend)
- [Running Tests](#running-tests)
- [Database Migrations](#database-migrations)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Features

-   **Job Management**: Create, read, update, and delete job postings.
-   **Candidate Management**: Create, read, update, and delete candidate profiles, including resume parsing.
-   **Interview Scheduling & Management**: Schedule and manage interviews.
-   **AI-Powered Question Generation**: Automatically generate interview questions based on job descriptions and candidate resumes.
-   **AI-Powered Interview Reports**: Generate comprehensive interview assessment reports.
-   **Interactive Frontend**: A Streamlit-based frontend for easy interaction (if applicable).

## Tech Stack

-   **Backend**: FastAPI, Python 3.13+
-   **Frontend**: Streamlit (if applicable, describe its role)
-   **Database**: MySQL
-   **ORM**: SQLAlchemy
-   **Database Migrations**: Alembic
-   **Dependency Management**: uv
-   **Python Version Management**: pyenv
-   **Testing**: Pytest
-   **AI Integrations**: Langchain, OpenAI

## Prerequisites

-   Python 3.13+ (managed via `pyenv` is recommended)
-   `pyenv` installed (see [pyenv installation guide](https://github.com/pyenv/pyenv#installation))
-   `uv` installed (see [uv installation guide](https://github.com/astral-sh/uv#installation))
-   MySQL server running and accessible.
-   An OpenAI API key.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <YOUR_REPOSITORY_URL>
    cd ai-interview-assistant
    ```

2.  **Set up Python version using pyenv:**
    ```bash
    pyenv install $(cat .python-version) # Install the version specified in .python-version
    pyenv local $(cat .python-version)   # Set the local Python version for the project
    ```

3.  **Create and activate a virtual environment (optional but recommended, uv can manage this):**
    `uv` can work with or without an explicitly activated virtual environment. If you prefer to create one:
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows: .venv\\Scripts\\activate
    ```
    Alternatively, you can let `uv` manage its own environment implicitly.

4.  **Install dependencies using uv:**
    ```bash
    # uv pip install -r requirements.txt # requirements.txt is now in .gitignore
    uv pip install . # Installs dependencies from pyproject.toml
    uv pip install -e ".[test]" # To install optional test dependencies
    ```
    *Note: Dependencies are primarily managed via `pyproject.toml` and `uv.lock`.*

## Environment Setup

This project uses `.envrc` for `direnv` (optional) and a `.env` file for environment variables.

1.  **`direnv` (Optional):**
    If you use `direnv`, it will automatically activate the Python virtual environment (if configured in `.envrc`) when you `cd` into the project directory. Ensure your `.envrc` is set up appropriately (e.g., to source the `.venv/bin/activate` script or manage `pyenv`).
    Example `.envrc` content (if not already present and correct):
    ```bash
    # Example .envrc content
    # layout python # if you use pyenv with direnv
    # OR
    # source .venv/bin/activate # if using a .venv
    echo "Activated project environment."
    ```
    Remember to run `direnv allow` after creating or modifying `.envrc`.

2.  **`.env` File:**
    This file stores sensitive credentials and environment-specific configurations. It is **not** committed to version control.
    Create a `.env` file in the project root by copying the example (if you create one) or by creating it manually:
    ```bash
    cp env.example .env # If you provide an env.example
    # OR create .env manually
    ```
    Populate `.env` with the necessary variables. Minimally, you will need:
    ```ini
    OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"
    # Database URL for the main application
    DATABASE_URL="mysql+pymysql://user:pass@host:port/dbname"
    # Database URL for testing (pytest uses this via pytest-dotenv)
    TEST_MYSQL_DATABASE_URL="mysql+pymysql://testuser:testpass@localhost:3306/testdb"
    # Other environment variables as needed by your application
    ```
    **Important**: Replace placeholders with your actual credentials and database connection strings. Ensure the databases specified exist and the users have the necessary permissions.

## Running the Application

### FastAPI Backend

1.  **Ensure your virtual environment is active (if you created one explicitly) and `.env` is populated.**
2.  **Run database migrations (if this is the first time or if there are new migrations):**
    ```bash
    alembic upgrade head
    ```
3.  **Start the FastAPI development server using Uvicorn:**
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```
    The API will typically be available at `http://localhost:8000`.
    The auto-generated API documentation will be at `http://localhost:8000/docs`.

### Streamlit Frontend (If Applicable)

1.  **Ensure your virtual environment is active and `.env` is populated.**
2.  **Navigate to the Streamlit app directory (if it's separate):**
    ```bash
    cd streamlit_app # Or your Streamlit app's directory
    ```
3.  **Run the Streamlit application:**
    ```bash
    streamlit run main_streamlit.py # Replace main_streamlit.py with your entry point script
    ```
    The Streamlit app will typically be available at `http://localhost:8501`.

## Running Tests

1.  **Ensure your virtual environment is active and `TEST_MYSQL_DATABASE_URL` in `.env` is correctly configured for your test database.**
    The `pytest-dotenv` plugin will automatically load variables from `.env`.
2.  **Run the tests using Pytest:**
    ```bash
    pytest
    ```
    You can run specific tests by specifying the path or markers:
    ```bash
    pytest tests/api/v1/test_interviews.py
    pytest -m "marker_name"
    ```

## Database Migrations

This project uses Alembic for database schema migrations.

-   **To generate a new migration script after making changes to SQLAlchemy models:**
    ```bash
    alembic revision -m "short_description_of_changes"
    ```
    Then, edit the generated script in the `alembic/versions/` directory to define the upgrade and downgrade operations.

-   **To apply migrations to your database:**
    ```bash
    alembic upgrade head
    ```

-   **To downgrade to a specific version:**
    ```bash
    alembic downgrade <version_identifier>
    ```

-   **To see the current database revision:**
    ```bash
    alembic current
    ```

## Project Structure

    .
    ├── alembic/                  # Alembic migration scripts
    ├── app/                      # Main application source code (FastAPI)
    │   ├── api/                  # API specific modules (routers, schemas)
    │   │   └── v1/
    │   ├── core/                 # Core logic, configuration
    │   ├── db/                   # Database models, session management
    │   ├── services/             # Business logic, AI service integrations
    │   └── main.py               # FastAPI application entry point
    ├── streamlit_app/            # Streamlit frontend application (if applicable)
    ├── tests/                    # Test suite
    ├── env.example               # Example environment file (optional, good practice)
    ├── .envrc                    # Direnv configuration (optional)
    ├── .gitignore                # Files and directories to ignore in Git
    ├── .python-version           # pyenv Python version for the project
    ├── alembic.ini               # Alembic configuration file
    ├── pyproject.toml            # Project metadata and dependencies (for uv/PEP 517 tools)
    ├── pytest.ini                # Pytest configuration
    ├── README.md                 # This file
    └── uv.lock                   # uv lock file for reproducible dependencies

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Ensure tests pass (`pytest`).
5.  Commit your changes (`git commit -m 'Add some feature'`).
6.  Push to the branch (`git push origin feature/your-feature-name`).
7.  Open a Pull Request.

Please ensure your code adheres to any linting and formatting standards used in the project (e.g., Ruff, Black - consider adding these if not already used).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.md) file for details (You'll need to create a LICENSE.md file with the MIT license text if you choose this license).
