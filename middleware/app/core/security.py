import secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# Extract Authorization: Bearer ... without raising if absent (we validate in get_current_user).
security = HTTPBearer(auto_error=False)


def _bearer_matches(provided: str, expected: str) -> bool:
    """Constant-time comparison for API keys."""
    if len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    """
    Resolves the caller when API_KEY is configured: requires a valid Bearer token.
    If API_KEY is unset, returns a fixed dev user (not suitable for exposed networks).
    """
    key = (settings.API_KEY or "").strip()
    if not key:
        return "development_user"

    if credentials is None or (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header (expected Bearer token).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _bearer_matches(credentials.credentials, key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "default_user"
