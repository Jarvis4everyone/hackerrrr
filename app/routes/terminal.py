"""
Terminal Routes - PowerShell terminal session management
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.terminal_service import terminal_service
from app.websocket.connection_manager import manager
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminal", tags=["Terminal"])


@router.post("/start")
async def start_terminal_session(
    pc_id: str = Query(..., description="PC ID to start terminal on")
):
    """
    Start a new terminal session on a PC
    
    Args:
        pc_id: ID of the PC
    
    Returns:
        Session ID and status
    """
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        # Also check database for connection status
        from app.services.pc_service import PCService
        pc = await PCService.get_pc(pc_id)
        if not pc or not pc.connected:
            raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session
    terminal_service.create_session(pc_id, session_id)
    
    # Send start request to PC
    success = await manager.start_terminal_session(pc_id, session_id)
    
    if not success:
        terminal_service.end_session(session_id)
        raise HTTPException(status_code=500, detail="Failed to start terminal session on PC")
    
    return {
        "session_id": session_id,
        "pc_id": pc_id,
        "status": "starting"
    }


@router.post("/stop")
async def stop_terminal_session(
    session_id: str = Query(..., description="Session ID to stop"),
    pc_id: str = Query(..., description="PC ID")
):
    """
    Stop a terminal session
    
    Args:
        session_id: Session ID
        pc_id: PC ID
    
    Returns:
        Success status
    """
    # Check if session exists (don't raise error if already ended)
    session_exists = terminal_service.is_session_active(session_id)
    
    if session_exists:
        # Send stop request to PC (only if PC is still connected)
        if manager.is_connected(pc_id):
            await manager.stop_terminal_session(pc_id, session_id)
        
        # End session
        terminal_service.end_session(session_id)
    
    # Always return success, even if session was already ended
    return {
        "success": True,
        "message": "Terminal session stopped"
    }


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get terminal session information
    
    Args:
        session_id: Session ID
    
    Returns:
        Session information
    """
    session_info = terminal_service.get_session_info(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session_info

