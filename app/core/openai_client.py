from openai import AsyncOpenAI
from app.core.config import settings

_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """
    Returns a singleton instance of the AsyncOpenAI client, configured with
    API key and base URL from settings.
    """
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE, # base_url can be None, AsyncOpenAI handles it
            timeout=60.0  # Added default timeout of 60 seconds
        )
    return _openai_client

# Optional: Add a function to explicitly close the client if needed,
# for example, during application shutdown, though for many serverless/short-lived
# scenarios, it might not be strictly necessary as connections are typically
# managed by the underlying HTTP library.
# async def close_openai_client():
#     global _openai_client
#     if _openai_client is not None:
#         await _openai_client.close()
#         _openai_client = None 