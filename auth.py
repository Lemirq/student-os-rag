from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from config import settings

# Define API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API key",
        )
    return api_key
