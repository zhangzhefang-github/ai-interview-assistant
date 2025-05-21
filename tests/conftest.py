import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import importlib
import sys
import logging # Import logging
import traceback # Keep for explicit traceback printing if needed by logger
import os # Added os import
from pathlib import Path # Added Path import
from asgi_lifespan import LifespanManager # Ensure this import is added
import httpx # Added httpx import for AsyncClient

# Add project root to sys.path
# conftest.py is in 'tests/' directory, so project_root is parent of parent
project_root = Path(__file__).resolve().parent.parent
# Ensure project_root is a string for sys.path operations
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)
    # Use logger if available, otherwise print
    # print(f"DEBUG: Added to sys.path in conftest: {project_root_str}") 
    if 'logger' in globals() and logger:
        logger.debug(f"Added to sys.path in conftest: {project_root_str}")
    else:
        print(f"DEBUG: Added to sys.path in conftest: {project_root_str}")
else:
    # print(f"DEBUG: Already in sys.path: {project_root_str}")
    if 'logger' in globals() and logger:
        logger.debug(f"Already in sys.path: {project_root_str}")
    else:
        print(f"DEBUG: Already in sys.path: {project_root_str}")

# Attempt to ensure logging is configured early.
# If app.core.config.setup_logging is called, it might reconfigure.
# For tests, we want to ensure DEBUG level is active if possible.
# A simple basicConfig here can be a fallback or initial setup.
logging.basicConfig(level=logging.DEBUG, 
                    format="%(asctime)s [%(levelname)-8s] %(name)-30s: %(message)s", 
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[logging.StreamHandler(sys.stdout)],
                    force=True) # Use force=True to allow re-configuration if already set by another module

logger = logging.getLogger(__name__) # Logger for conftest itself

# Remove module-level imports of endpoint modules, they will be imported dynamically
# from app.api.v1.endpoints import interviews as interviews_router_module # REMOVE
# from app.api.v1.endpoints import jobs as jobs_router_module           # REMOVE
# from app.api.v1.endpoints import candidates as candidates_router_module # REMOVE
import app.main as main_module

from app.db.session import get_db
from app.db.models import Base

# --- Test Database Setup ---
# Using MySQL for tests, configured via environment variable
TEST_MYSQL_DATABASE_URL = os.environ.get("TEST_MYSQL_DATABASE_URL")
if not TEST_MYSQL_DATABASE_URL:
    raise RuntimeError("TEST_MYSQL_DATABASE_URL environment variable not set. Please set it to your MySQL connection string for testing (e.g., mysql+pymysql://user:pass@host:port/dbname)")

SQLALCHEMY_DATABASE_URL_TEST = TEST_MYSQL_DATABASE_URL

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST
    # Removed SQLite-specific connect_args and poolclass
)
SessionTesting = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# --- Pytest Fixture for Database Session ---
# This fixture will be responsible for:
# 1. Creating all database tables before a test runs.
# 2. Providing a database session to the test.
# 3. Dropping all database tables after a test finishes.
@pytest.fixture(scope="function")
def db_session_test():
    Base.metadata.create_all(bind=engine_test)  # Create tables
    db = SessionTesting()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)  # Drop tables

# --- Pytest Fixture for API Test Client ---
# This fixture will:
# 1. Depend on the db_session_test fixture to ensure DB is set up.
# 2. Override the application's get_db dependency to use the test_db session.
# 3. Provide an instance of TestClient.
# 4. Clean up dependency overrides after the test.
@pytest.fixture(scope="function")
def client(db_session_test):
    logger.info("Client fixture setup started.")
    # Define module names
    interviews_module_name = "app.api.v1.endpoints.interviews"
    jobs_module_name = "app.api.v1.endpoints.jobs"
    candidates_module_name = "app.api.v1.endpoints.candidates"
    main_app_module_name = "app.main"

    # Clean slate for modules
    for module_name in [interviews_module_name, jobs_module_name, candidates_module_name, main_app_module_name]:
        if module_name in sys.modules:
            logger.debug(f"Deleting module {module_name} from sys.modules")
            del sys.modules[module_name]

    # Dynamically import endpoint modules
    logger.debug(f"Importing module: {jobs_module_name}")
    jobs_router_module = importlib.import_module(jobs_module_name)
    logger.debug(f"Importing module: {candidates_module_name}")
    candidates_router_module = importlib.import_module(candidates_module_name)
    
    interviews_router_module = None # Initialize to None
    try:
        logger.debug(f"Attempting to import: {interviews_module_name}")
        interviews_router_module = importlib.import_module(interviews_module_name)
        logger.info(f"Successfully imported: {interviews_module_name}")

        if interviews_router_module and hasattr(interviews_router_module, '__file__'):
            module_path = interviews_router_module.__file__
            logger.debug(f"Path to imported '{interviews_module_name}': {module_path}")
            try:
                with open(module_path, 'r') as f:
                    content = f.read()
                logger.debug(f"---- Content of {module_path} ----\\n{content}\\n---- End Content of {module_path} ----")
            except Exception as e_read:
                logger.error(f"Could not read content of {module_path}: {e_read}")
        elif interviews_router_module:
            logger.warning(f"Module '{interviews_module_name}' imported but has no __file__ attribute.")
        else:
            logger.warning(f"Module '{interviews_module_name}' was not imported, cannot read its content.")

    except Exception as e:
        logger.error(f"ERROR IMPORTING {interviews_module_name}: {type(e).__name__} - {e}", exc_info=True)

    logger.debug("---- Routes in (potentially partially) imported interviews_router_module.router ----")
    if interviews_router_module and hasattr(interviews_router_module, "router") and hasattr(interviews_router_module.router, "routes"):
        for route in interviews_router_module.router.routes:
            if hasattr(route, "path"):
                logger.debug(f"  Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', 'N/A')}")
            else:
                logger.debug(f"  Route object: {route}")
    elif interviews_router_module:
        logger.warning("  interviews_router_module was imported, but 'router' or 'router.routes' not found.")
    else:
        logger.warning("  interviews_router_module failed to import or is None.")
    logger.debug("----------------------------------------------------------------------------------")

    logger.debug(f"Importing main app module: {main_app_module_name}")
    current_main_module = importlib.import_module(main_app_module_name)
    current_app = current_main_module.app
    logger.info("Main app module imported and app instance obtained.")

    def override_get_db_for_testing():
        try:
            yield db_session_test
        finally:
            pass

    current_app.dependency_overrides[get_db] = override_get_db_for_testing
    
    logger.debug("---- Registered Routes (in conftest.py client fixture after fresh import) ----")
    for route_idx, route in enumerate(current_app.routes):
        if hasattr(route, "path"):
            logger.debug(f"  App Route [{route_idx}]: Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', 'N/A')}")
        elif hasattr(route, "routes") and route.routes: # Handle APIRouter mounts
             logger.debug(f"  App Route [{route_idx}]: Router Mount: {route.path_format if hasattr(route, 'path_format') else 'N/A'}")
             for sub_idx, sub_route in enumerate(route.routes):
                 if hasattr(sub_route, "path"):
                    logger.debug(f"    -> Sub-Path [{sub_idx}]: {sub_route.path}, Name: {sub_route.name}, Methods: {getattr(sub_route, 'methods', 'N/A')}")
                 else:
                    logger.debug(f"    -> Sub-Route [{sub_idx}]: {sub_route}")
        else:
            logger.debug(f"  App Route [{route_idx}]: Other Route Type: {route}")
    logger.debug("----------------------------------------------------------------------")

    with TestClient(current_app) as test_client:
        logger.info("TestClient created, yielding client.")
        yield test_client
    
    current_app.dependency_overrides.clear()
    logger.info("Client fixture teardown: DB dependency override cleared.")

# Note: If you have any application startup/shutdown events in app.main.app
# that interact with the database, you might need to adjust how and when
# tables are created/dropped, or how the TestClient is initialized,
# for example, by managing the lifespan of the TestClient more explicitly
# if startup events need a DB. For now, this setup is standard. 

# --- New Fixture for App Lifespan Management ---
# Import the main app instance. Adjust if your app instance is located elsewhere.
# from app.main import app as main_fastapi_app # We will get app from main_module in fixture

@pytest.fixture(scope="function") # Or "session" if app startup is expensive and safe to share
async def app_lifespan_context(db_session_test): # Depends on db_session_test to ensure DB is ready
    """
    Provides the FastAPI app instance within its lifespan context.
    Ensures startup and shutdown events are run.
    """
    logger.info("app_lifespan_context fixture setup started.")
    
    # Dynamically import main_module to get the app instance
    # This aligns with how the 'client' fixture does it, ensuring fresh state
    main_app_module_name = "app.main"
    if main_app_module_name in sys.modules:
        logger.debug(f"Deleting module {main_app_module_name} from sys.modules for app_lifespan_context")
        del sys.modules[main_app_module_name]
    
    logger.debug(f"Importing main app module for app_lifespan_context: {main_app_module_name}")
    current_main_module = importlib.import_module(main_app_module_name)
    the_app = current_main_module.app # Get the app instance

    # Override DB dependency for the app instance used in this context
    def override_get_db_for_lifespan():
        try:
            yield db_session_test
        finally:
            pass # db_session_test handles its own close
            
    the_app.dependency_overrides[get_db] = override_get_db_for_lifespan
    logger.debug("Applied dependency_overrides for app_lifespan_context.")

    async with LifespanManager(the_app) as manager:
        logger.info("LifespanManager entered for app_lifespan_context.")
        yield manager.app # Yield the app instance from the manager
    
    logger.info("LifespanManager exited for app_lifespan_context. Cleaning up dependency override.")
    the_app.dependency_overrides.clear()

# Fixture to provide an httpx.AsyncClient configured with the app from app_lifespan_context
@pytest.fixture(scope="function")
async def async_app_client(app_lifespan_context):
    """
    Provides an httpx.AsyncClient configured to talk to the app
    managed by app_lifespan_context.
    """
    # app_lifespan_context yields the app instance itself after entering LifespanManager
    the_managed_app = app_lifespan_context 
    async with httpx.AsyncClient(app=the_managed_app, base_url="http://testserver") as client:
        logger.info("httpx.AsyncClient created for async_app_client.")
        yield client
    logger.info("httpx.AsyncClient closed for async_app_client.") 