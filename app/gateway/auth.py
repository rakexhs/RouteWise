from fastapi import Header, HTTPException

from app.config import get_settings


def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    settings = get_settings()
    if not x_api_key or x_api_key != settings.demo_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key
