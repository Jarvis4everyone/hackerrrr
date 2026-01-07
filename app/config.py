"""
Application Configuration
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root(start_path: Path = None) -> Path:
    """
    Find the project root directory by looking for marker files/folders.
    Works regardless of where the script is run from or where the project is located.
    
    This function is completely path-independent - it will work if you:
    - Copy the entire server folder to any location
    - Run from any directory
    - Move the project to a different drive or path
    """
    if start_path is None:
        # Start from the config file location (app/config.py)
        # This is always relative to where the file actually is, not where it's run from
        start_path = Path(__file__).parent
    
    # Resolve to absolute path
    current = Path(start_path).resolve()
    
    # Markers that indicate project root (must have at least 2 of these)
    # This ensures we find the correct root even if some files are missing
    markers = {
        'run.py': False,           # Main entry point
        'app': False,              # App directory (must be a directory)
        'Scripts': False,          # Scripts directory (must be a directory)
        '.env': False              # Environment file
    }
    
    # Walk up the directory tree starting from current location
    for parent in [current] + list(current.parents):
        # Check which markers exist in this directory
        found_markers = []
        for marker_name, _ in markers.items():
            marker_path = parent / marker_name
            if marker_path.exists():
                # For 'app' and 'Scripts', ensure they're directories
                if marker_name in ['app', 'Scripts']:
                    if marker_path.is_dir():
                        found_markers.append(marker_name)
                else:
                    found_markers.append(marker_name)
        
        # If we found at least 2 markers (or 'app' + 'Scripts'), this is likely the root
        if len(found_markers) >= 2 or ('app' in found_markers and 'Scripts' in found_markers):
            return parent
    
    # Fallback: If no clear root found, use the directory containing 'app' folder
    # (since we know we're in app/config.py, the parent of app should be root)
    app_dir = current
    while app_dir.name != 'app' and app_dir.parent != app_dir:
        app_dir = app_dir.parent
    
    if app_dir.name == 'app' and app_dir.is_dir():
        return app_dir.parent
    
    # Last resort: return the directory containing this config file's parent
    # (which should be the project root if structure is correct)
    return current.parent if current.name == 'app' else current


# Find project root once at module load
# This is completely path-independent - works from any location
# Even if you copy the entire folder to C:\Users\shres\Downloads\Hacking\Server
# it will automatically detect the correct root
PROJECT_ROOT = find_project_root().resolve()

# Setup logger
import logging
logger = logging.getLogger(__name__)
try:
    logger.debug(f"Project root detected: {PROJECT_ROOT}")
except:
    pass


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=True,
        extra="ignore"
    )
    
    # Server Configuration
    APP_NAME: str = "Remote Script Server"
    APP_VERSION: str = "1.0.0"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # MongoDB Configuration
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "remote_script_server"
    
    # Scripts Directory - relative to project root
    SCRIPTS_DIR: str = str(PROJECT_ROOT / "Scripts")
    
    # CORS Configuration
    CORS_ORIGINS: list = ["*"]
    
    # WebSocket Configuration
    WS_HEARTBEAT_TIMEOUT: int = 30
    WS_PING_INTERVAL: int = 30
    
    # Server URL (from .env, used in scripts)
    # Note: .env file uses "Serverurl" (case-sensitive)
    SERVER_URL: Optional[str] = None
    
    # Authentication Configuration
    # Can be set via environment variables: AUTH_USERNAME and AUTH_PASSWORD
    # Or via .env file using "Username" and "Password" (case-sensitive, with spaces around =)
    # Defaults will be overridden by .env file reading below
    AUTH_USERNAME: str = "admin"
    AUTH_PASSWORD: str = "admin"


settings = Settings()

# Manually read from .env file to handle spaces and case sensitivity
# Pydantic Settings doesn't handle spaces around = sign well
# Priority: Environment variables > .env file > defaults
env_file_path = PROJECT_ROOT / ".env"
if env_file_path.exists():
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Handle both "KEY = VALUE" and "KEY=VALUE" formats
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Override settings with values from .env (only if not set via environment variables)
                    if key == "MONGODB_URL" and not os.getenv("MONGODB_URL"):
                        settings.MONGODB_URL = value
                    elif key == "MONGODB_DB_NAME" and not os.getenv("MONGODB_DB_NAME"):
                        settings.MONGODB_DB_NAME = value
                    elif (key == "Serverurl" or key == "SERVER_URL") and not os.getenv("SERVER_URL"):
                        settings.SERVER_URL = value
                    elif key == "Username" and not os.getenv("AUTH_USERNAME"):
                        settings.AUTH_USERNAME = value
                        logger.info(f"Loaded AUTH_USERNAME from .env file: '{value}'")
                    elif key == "Password" and not os.getenv("AUTH_PASSWORD"):
                        settings.AUTH_PASSWORD = value
                        logger.info(f"Loaded AUTH_PASSWORD from .env file (length: {len(value)})")
    except Exception as e:
        logger.warning(f"Error reading .env file: {e}")

# Override with environment variables if they exist (highest priority)
if os.getenv("AUTH_USERNAME"):
    settings.AUTH_USERNAME = os.getenv("AUTH_USERNAME")
    logger.info(f"Overriding AUTH_USERNAME from environment variable: '{settings.AUTH_USERNAME}'")
if os.getenv("AUTH_PASSWORD"):
    settings.AUTH_PASSWORD = os.getenv("AUTH_PASSWORD")
    logger.info(f"Overriding AUTH_PASSWORD from environment variable (length: {len(settings.AUTH_PASSWORD)})")

# Set default SERVER_URL if not provided
if not settings.SERVER_URL:
    settings.SERVER_URL = f"http://{settings.HOST}:{settings.PORT}"

# Log authentication settings (without password) for debugging
try:
    logger.info(f"Auth username loaded: {settings.AUTH_USERNAME}")
    logger.info(f"Auth password loaded: {'*' * len(settings.AUTH_PASSWORD) if settings.AUTH_PASSWORD else 'NOT SET'}")
    logger.info(f"MongoDB URL: {settings.MONGODB_URL}")
    logger.info(f"MongoDB DB: {settings.MONGODB_DB_NAME}")
except:
    pass

# Export project root for use in other modules
__all__ = ['settings', 'PROJECT_ROOT']

