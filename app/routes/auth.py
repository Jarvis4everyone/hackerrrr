"""
Authentication Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.config import settings
import secrets
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

# Simple in-memory token storage (in production, use Redis or database)
active_tokens = {}

# Token expiration time (24 hours)
TOKEN_EXPIRY_HOURS = 24


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None


def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)


def is_token_valid(token: str) -> bool:
    """Check if token is valid and not expired"""
    if token not in active_tokens:
        return False
    
    expires_at = active_tokens[token]
    if datetime.now() > expires_at:
        # Token expired, remove it
        del active_tokens[token]
        return False
    
    return True


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    if not is_token_valid(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return "authenticated"


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Login endpoint"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug logging (without password)
    logger.info(f"Login attempt - Username: '{login_data.username}'")
    logger.info(f"Expected username: '{settings.AUTH_USERNAME}'")
    logger.info(f"Username match: {login_data.username == settings.AUTH_USERNAME}")
    logger.info(f"Password provided: {'YES' if login_data.password else 'NO'}")
    logger.info(f"Password length: {len(login_data.password) if login_data.password else 0}")
    logger.info(f"Expected password length: {len(settings.AUTH_PASSWORD) if settings.AUTH_PASSWORD else 0}")
    logger.info(f"Password match: {login_data.password == settings.AUTH_PASSWORD}")
    logger.info(f"Settings AUTH_USERNAME: '{settings.AUTH_USERNAME}' (type: {type(settings.AUTH_USERNAME)})")
    logger.info(f"Settings AUTH_PASSWORD: {'*' * len(settings.AUTH_PASSWORD) if settings.AUTH_PASSWORD else 'NOT SET'} (type: {type(settings.AUTH_PASSWORD)})")
    
    # Strict comparison - ensure exact match
    username_match = login_data.username.strip() == settings.AUTH_USERNAME.strip() if settings.AUTH_USERNAME else False
    password_match = login_data.password.strip() == settings.AUTH_PASSWORD.strip() if settings.AUTH_PASSWORD else False
    
    logger.info(f"After strip - Username match: {username_match}, Password match: {password_match}")
    
    if not username_match or not password_match:
        logger.warning(f"Login failed for username: {login_data.username}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Generate token
    token = generate_token()
    expires_at = datetime.now() + timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    # Store token
    active_tokens[token] = expires_at
    
    return LoginResponse(
        token=token,
        expires_at=expires_at.isoformat()
    )


@router.post("/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout endpoint"""
    token = credentials.credentials
    
    if token in active_tokens:
        del active_tokens[token]
    
    return {"message": "Logged out successfully"}


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))):
    """Check authentication status"""
    try:
        if credentials and is_token_valid(credentials.credentials):
            return AuthStatusResponse(authenticated=True, username=settings.AUTH_USERNAME)
    except:
        pass
    
    return AuthStatusResponse(authenticated=False)


@router.get("/verify")
async def verify_token(user: str = Depends(get_current_user)):
    """Verify token endpoint"""
    return {"authenticated": True, "username": settings.AUTH_USERNAME}

