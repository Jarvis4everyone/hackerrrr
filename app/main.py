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
from app.routes import pcs, scripts, executions, health, code
from app.websocket.handlers import handle_websocket_connection
from app.services.script_service import ScriptService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



async def cleanup_stale_connections():
    """Periodically clean up stale connections"""
    import asyncio
    from datetime import datetime, timedelta
    from app.services.pc_service import PCService
    from app.services.streaming_service import streaming_service
    from app.websocket.connection_manager import manager
    
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            # Mark PCs as offline if they haven't sent a heartbeat in 1 minute (60 seconds)
            # But only if they're not actively streaming
            cutoff_time = datetime.utcnow() - timedelta(seconds=60)  # 1 minute
            
            # Get all PCs marked as connected in DB
            from app.database import get_database
            db = get_database()
            
            stale_pcs = await db.pcs.find({
                "connected": True,
                "last_seen": {"$lt": cutoff_time}
            }).to_list(length=100)
            
            for pc_data in stale_pcs:
                pc_id = pc_data.get("pc_id")
                if pc_id:
                    # Check if PC is actively streaming (camera, microphone, or screen)
                    is_streaming = False
                    try:
                        is_streaming = await streaming_service.get_pc_streaming_status(pc_id, "camera") or \
                                      await streaming_service.get_pc_streaming_status(pc_id, "microphone") or \
                                      await streaming_service.get_pc_streaming_status(pc_id, "screen")
                    except:
                        pass
                    
                    # If PC is streaming, keep it online (don't mark as offline)
                    if is_streaming:
                        logger.debug(f"PC {pc_id} is actively streaming - keeping online despite stale heartbeat")
                        # Update last_seen to keep it online
                        await PCService.update_last_seen(pc_id)
                        continue
                    
                    # Check if WebSocket is still active
                    if not manager.is_connected(pc_id):
                        logger.info(f"Marking stale PC as offline: {pc_id} (last_seen: {pc_data.get('last_seen')}, no active streams)")
                        await PCService.update_connection_status(pc_id, connected=False)
                    else:
                        # WebSocket is active but no heartbeat - update last_seen to keep it online
                        logger.debug(f"PC {pc_id} has active WebSocket but stale heartbeat - updating last_seen")
                        await PCService.update_last_seen(pc_id)
            
            # Also sync active WebSocket connections with DB
            for pc_id in list(manager.active_connections.keys()):
                # Ensure all active WebSocket connections are marked as online
                await PCService.update_last_seen(pc_id)
                
        except Exception as e:
            logger.error(f"Error in cleanup_stale_connections: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    import asyncio
    
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
    
    # Start background task for connection cleanup
    cleanup_task = asyncio.create_task(cleanup_stale_connections())
    logger.info("Started background task for connection cleanup")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await close_mongo_connection()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Remote Script Server with MongoDB",
    lifespan=lifespan
)

# Enable CORS - Allow all origins
# Using explicit configuration to ensure CORS headers are always sent
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(health.router)
from app.routes import auth
app.include_router(auth.router)
app.include_router(pcs.router)
app.include_router(scripts.router)
app.include_router(code.router)
app.include_router(executions.router)

# Import and include logs router
from app.routes import logs
app.include_router(logs.router)

# Import and include files router
from app.routes import files
app.include_router(files.router)

# Import and include terminal router
from app.routes import terminal
app.include_router(terminal.router)

# Import and include streaming router
from app.routes import streaming
app.include_router(streaming.router)


# WebSocket endpoint for PC connections
@app.websocket("/ws/{pc_id}")
async def websocket_endpoint(websocket: WebSocket, pc_id: str):
    """WebSocket endpoint for PC connections"""
    await handle_websocket_connection(websocket, pc_id)

# WebSocket endpoint for frontend terminal sessions
@app.websocket("/ws/terminal/{pc_id}/{session_id}")
async def frontend_terminal_endpoint(websocket: WebSocket, pc_id: str, session_id: str):
    """WebSocket endpoint for frontend terminal sessions"""
    from app.websocket.terminal_handlers import handle_frontend_terminal
    await handle_frontend_terminal(websocket, pc_id, session_id)

# WebSocket endpoints for frontend streaming connections
@app.websocket("/ws/stream/{pc_id}/{stream_type}")
async def frontend_stream_endpoint(websocket: WebSocket, pc_id: str, stream_type: str):
    """WebSocket endpoint for frontend streaming connections"""
    if stream_type not in ['camera', 'microphone', 'screen']:
        await websocket.close(code=1008, reason="Invalid stream type")
        return
    
    from app.websocket.streaming_handlers import handle_frontend_stream
    await handle_frontend_stream(websocket, pc_id, stream_type)


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

