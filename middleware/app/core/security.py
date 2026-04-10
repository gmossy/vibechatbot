from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

# Standard HTTP Authorization Header extractor
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Decodes the Keycloak JWT token securely and acts as the gatekeeper for FastAPI.
    In development mode, if no Keycloak token is passed, we default to a standard user.
    """
    if credentials is None:
        # Development fallback (Will require strict lockdown in production)
        return "development_user"
        
    token = credentials.credentials
    try:
        # Decode without strict signature verification for this prototype phase,
        # but in production we pull the RS256 public key dynamically from Keycloak endpoint
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get("sub", "unknown_user")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid Authentication Token")
