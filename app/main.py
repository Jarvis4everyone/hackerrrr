"""
FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
import logging

from app.config import settings, PROJECT_ROOT, PROJECT_ROOT
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import pcs, scripts, executions, health
from app.websocket.handlers import handle_websocket_connection
from app.services.script_service import ScriptService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Reduce verbosity of aioice (WebRTC ICE) logs - these are just informational
logging.getLogger('aioice.ice').setLevel(logging.WARNING)

# Suppress noisy aioice warnings about link-local addresses
logging.getLogger('aioice.ice').setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting application...")
    await connect_to_mongo()
    
    # Verify scripts directory exists
    scripts_dir = Path(settings.SCRIPTS_DIR)
    if not scripts_dir.exists():
        logger.warning(f"Scripts directory does not exist: {scripts_dir}")
        logger.info(f"Project root: {PROJECT_ROOT}")
        logger.info(f"Expected scripts directory: {scripts_dir}")
        logger.info(f"Current working directory: {os.getcwd()}")
    else:
        logger.info(f"Scripts directory found: {scripts_dir}")
        logger.info(f"Project root: {PROJECT_ROOT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Remote Script Server with MongoDB",
    lifespan=lifespan
)

# Enable CORS
# Handle CORS origins - if ["*"] is used, we can't use allow_credentials
cors_origins = settings.CORS_ORIGINS
if cors_origins == ["*"] or "*" in cors_origins:
    # Allow all origins but without credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Specific origins with credentials support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(health.router)
from app.routes import auth
app.include_router(auth.router)
app.include_router(pcs.router)
app.include_router(scripts.router)
app.include_router(executions.router)

# Import and include streaming router
from app.routes import streaming
app.include_router(streaming.router)

# Import and include logs router
from app.routes import logs
app.include_router(logs.router)

# Import and include files router
from app.routes import files
app.include_router(files.router)

# Import and include terminal router
from app.routes import terminal
app.include_router(terminal.router)


# WebSocket endpoint for PC connections
@app.websocket("/ws/{pc_id}")
async def websocket_endpoint(websocket: WebSocket, pc_id: str):
    """WebSocket endpoint for PC connections"""
    await handle_websocket_connection(websocket, pc_id)

# WebSocket endpoint for frontend WebRTC signaling
@app.websocket("/ws/frontend/{pc_id}/{stream_type}")
async def frontend_websocket_endpoint(websocket: WebSocket, pc_id: str, stream_type: str):
    """WebSocket endpoint for frontend WebRTC signaling"""
    from app.websocket.frontend_handlers import handle_frontend_websocket
    await handle_frontend_websocket(websocket, pc_id, stream_type)

# WebSocket endpoint for frontend terminal sessions
@app.websocket("/ws/terminal/{pc_id}/{session_id}")
async def frontend_terminal_endpoint(websocket: WebSocket, pc_id: str, session_id: str):
    """WebSocket endpoint for frontend terminal sessions"""
    from app.websocket.terminal_handlers import handle_frontend_terminal
    await handle_frontend_terminal(websocket, pc_id, session_id)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} - Starting...")
    logger.info("=" * 60)
    logger.info(f"Scripts directory: {settings.SCRIPTS_DIR}")
    logger.info(f"WebSocket endpoint: ws://{settings.HOST}:{settings.PORT}/ws/{{pc_id}}")
    logger.info(f"API endpoint: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"MongoDB: {settings.MONGODB_URL}/{settings.MONGODB_DB_NAME}")
    logger.info("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

