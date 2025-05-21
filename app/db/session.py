import logging # Import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Base # Import Base from models to create tables

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
logger.info(f"Database URL from settings: {SQLALCHEMY_DATABASE_URL}")

engine = None
try:
    logger.info("Attempting to create SQLAlchemy engine...")
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=True,  # Enable SQLAlchemy engine logging for more verbosity
        # connect_args={"check_same_thread": False} # Only needed for SQLite
    )
    logger.info("SQLAlchemy engine created successfully.")
except Exception as e:
    logger.error(f"Error creating SQLAlchemy engine: {e}", exc_info=True)
    # Optionally re-raise or handle as appropriate for your application
    raise


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create all tables in the database
# Call this once when your application starts up if tables don't exist
# For production, you'd typically use migrations (e.g., Alembic)
def create_db_and_tables():
    if engine is None:
        logger.error("Engine is not initialized. Cannot create tables.")
        return
    logger.info("Attempting to create database tables (Base.metadata.create_all)...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Base.metadata.create_all() completed.")
    except Exception as e:
        logger.error(f"Error during Base.metadata.create_all(): {e}", exc_info=True)
        raise

# Example of how you might call it in your main.py or a startup script:
# if __name__ == "__main__":
#     print(f"Creating database tables for URL: {SQLALCHEMY_DATABASE_URL}")
#     # Make sure your database server is running and the database specified in DATABASE_URL exists.
#     # For MySQL, the database itself must be created manually first (e.g., CREATE DATABASE ai_interview_assistant_db;)
#     create_db_and_tables()
#     print("Database tables should be created if they didn't exist.")

# Asynchronous engine and session setup (NEW)
logger.info("Attempting to create SQLAlchemy async engine...")
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("mysql+pymysql://", "mysql+aiomysql://")
# Or if using asyncpg for PostgreSQL: ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
logger.info(f"Async Database URL: {ASYNC_DATABASE_URL}")


try:
    async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine, 
        class_=AsyncSession, 
        autocommit=False, 
        autoflush=False, 
        expire_on_commit=False
    )
    logger.info("SQLAlchemy async engine and AsyncSessionLocal created successfully.")
except Exception as e:
    logger.error(f"Error creating SQLAlchemy async engine or AsyncSessionLocal: {e}", exc_info=True)
    async_engine = None
    AsyncSessionLocal = None # type: ignore

async def get_async_db() -> AsyncSession: # type: ignore
    if AsyncSessionLocal is None:
        logger.error("AsyncSessionLocal is not initialized. Cannot get async DB session.")
        raise RuntimeError("Async database session factory not initialized.")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # By default, we might not want to commit here. 
            # The endpoint should decide when to commit.
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
        # finally block not strictly needed if using 'async with'
        # as it handles closing, but can be added for explicit logging if desired.
        # finally:
        #     await session.close() # Handled by 'async with' 