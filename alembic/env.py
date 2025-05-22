from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
import os

# 将项目根目录添加到 Python 路径中，以便可以导入 app 包
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.models import Base

# --- BEGIN: Dynamically load DATABASE_URL from .env ---
from dotenv import load_dotenv

# 构建 .env 文件的绝对路径 (假设 .env 在项目根目录, 即 alembic/ 的上一级)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL")
# --- END: Dynamically load DATABASE_URL from .env ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- BEGIN: Override sqlalchemy.url if DATABASE_URL is set ---
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
# --- END: Override sqlalchemy.url if DATABASE_URL is set ---

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Function to construct the database URL from environment variables
def get_sqlalchemy_url():
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "mysql") # Default to 'mysql'
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME")
    
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        print("Warning: One or more database environment variables are not set.")
        return None

    return f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Set the sqlalchemy.url dynamically using the get_sqlalchemy_url function
db_url = get_sqlalchemy_url()
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)
else:
    print("Error: Database URL could not be constructed from environment variables.")

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    print("--- alembic/env.py: run_migrations_online() called ---") # DEBUG
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    print("--- alembic/env.py: Attempting to connect to the database... ---") # DEBUG
    with connectable.connect() as connection:
        print("--- alembic/env.py: Successfully connected to the database. ---") # DEBUG
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
