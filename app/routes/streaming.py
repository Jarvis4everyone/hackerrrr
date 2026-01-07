"""
Streaming API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from app.services.pc_service import PCService
from app.services.streaming_service import streaming_service
from app.websocket.connection_manager import manager
from app.routes.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])


@router.post("/start/{pc_id}/{stream_type}")
async def start_stream(pc_id: str, stream_type: str, current_user: dict = Depends(get_current_user)):
    """
    Start a stream (camera, microphone, or screen) for a PC
    
    Args:
        pc_id: PC ID
        stream_type: Type of stream ('camera', 'microphone', 'screen')
    """
    if stream_type not in ['camera', 'microphone', 'screen']:
        raise HTTPException(status_code=400, detail="Invalid stream type. Must be 'camera', 'microphone', or 'screen'")
    
    # Check if PC is connected
    pc = await PCService.get_pc(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC {pc_id} not found")
    
    if not pc.connected:
        raise HTTPException(status_code=400, detail=f"PC {pc_id} is not connected")
    
    # Check if PC WebSocket is active
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=400, detail=f"PC {pc_id} WebSocket connection is not active")
    
    # Send start stream command to PC
    success = await manager.send_personal_message({
        "type": "start_stream",
        "stream_type": stream_type
    }, pc_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send start stream command to PC")
    
    logger.info(f"[Streaming] Start {stream_type} requested for {pc_id}")
    
    return {
        "success": True,
        "message": f"Start {stream_type} command sent to PC",
        "pc_id": pc_id,
        "stream_type": stream_type
    }


@router.post("/stop/{pc_id}/{stream_type}")
async def stop_stream(pc_id: str, stream_type: str, current_user: dict = Depends(get_current_user)):
    """
    Stop a stream (camera, microphone, or screen) for a PC
    
    Args:
        pc_id: PC ID
        stream_type: Type of stream ('camera', 'microphone', 'screen')
    """
    if stream_type not in ['camera', 'microphone', 'screen']:
        raise HTTPException(status_code=400, detail="Invalid stream type. Must be 'camera', 'microphone', or 'screen'")
    
    # Check if PC exists
    pc = await PCService.get_pc(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC {pc_id} not found")
    
    # Send stop stream command to PC (even if not connected, try to send)
    if manager.is_connected(pc_id):
        await manager.send_personal_message({
            "type": "stop_stream",
            "stream_type": stream_type
        }, pc_id)
    
    # Update streaming status
    await streaming_service.set_pc_streaming_status(pc_id, stream_type, False)
    
    logger.info(f"[Streaming] Stop {stream_type} requested for {pc_id}")
    
    return {
        "success": True,
        "message": f"Stop {stream_type} command sent to PC",
        "pc_id": pc_id,
        "stream_type": stream_type
    }


@router.get("/status/{pc_id}/{stream_type}")
async def get_stream_status(pc_id: str, stream_type: str, current_user: dict = Depends(get_current_user)):
    """
    Get streaming status for a PC
    
    Args:
        pc_id: PC ID
        stream_type: Type of stream ('camera', 'microphone', 'screen')
    """
    if stream_type not in ['camera', 'microphone', 'screen']:
        raise HTTPException(status_code=400, detail="Invalid stream type. Must be 'camera', 'microphone', or 'screen'")
    
    # Check if PC exists
    pc = await PCService.get_pc(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC {pc_id} not found")
    
    # Get streaming status
    is_streaming = await streaming_service.get_pc_streaming_status(pc_id, stream_type)
    
    return {
        "pc_id": pc_id,
        "stream_type": stream_type,
        "is_streaming": is_streaming,
        "pc_connected": pc.connected
    }

