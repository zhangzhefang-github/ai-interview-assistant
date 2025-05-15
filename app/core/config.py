from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging
import sys

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_API_BASE: Optional[str] = None
    DATABASE_URL: str

    # model_config 用于配置 Pydantic-settings 的行为
    # 在这里，我们指定从 .env 文件加载环境变量
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()

def setup_logging(level=logging.INFO):
    """
    Set up basic logging configuration.
    Outputs to stdout, includes timestamp, level, logger name, and message.
    """
    # Check if handlers are already configured to avoid adding duplicate handlers
    # if not logging.getLogger().hasHandlers(): # This check might be too broad
    # A more specific check or a flag could be used if re-configuration is an issue.
    # For now, basicConfig is idempotent if no handlers are set for root logger,
    # but if called multiple times after handlers are set, it might add more.
    # To be safe, especially if this module could be reloaded, consider a flag.
    
    # Let's try to make it safer for potential reloads or multiple calls.
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove any existing handlers from the root logger to prevent duplication
    # if this function is called multiple times (e.g., due to module reloads in tests)
    # This is a bit aggressive but ensures a clean setup for our specific diagnostic case.
    # In a production app, you might want a more nuanced approach.
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]: # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close() # Close handler before removing

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)-8s] %(name)-30s: %(message)s", # Adjusted format for better readability
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)] # Ensure logs go to stdout
    )

# Call it once when the module is imported.
# For current diagnostics, set a low level like DEBUG.
# In a real app, this might be INFO by default and configurable.
setup_logging(level=logging.DEBUG)

# Optional: Test if logging is working after setup
# test_logger = logging.getLogger(__name__)
# test_logger.debug("Core config logging initialized with DEBUG level for diagnostics from config.py.")
# test_logger.info("Info test from config.py")
# test_logger.warning("Warning test from config.py") 