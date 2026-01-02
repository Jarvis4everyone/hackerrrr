"""
Streaming Routes - Agora camera, microphone, and screen streaming
"""
from fastapi import APIRouter, HTTPException
from app.websocket.connection_manager import manager
from app.services.agora_service import agora_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["Streaming"])


@router.post("/{pc_id}/camera/start")
async def start_camera_stream(pc_id: str):
    """Start camera stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    agora_service.stop_stream(pc_id)
    
    # Start camera stream
    stream_info = agora_service.start_stream(pc_id, "camera")
    
    # Send start command to PC via WebSocket with Agora credentials
    await manager.send_personal_message({
        "type": "start_stream",
        "stream_type": "camera",
        "agora": stream_info
    }, pc_id)
    
    return {
        "status": "success",
        "message": f"Camera stream started for PC '{pc_id}'",
        "pc_id": pc_id,
        "stream_type": "camera",
        "agora": stream_info
    }


@router.post("/{pc_id}/microphone/start")
async def start_microphone_stream(pc_id: str):
    """Start microphone stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    agora_service.stop_stream(pc_id)
    
    # Start microphone stream
    stream_info = agora_service.start_stream(pc_id, "microphone")
    
    # Send start command to PC via WebSocket with Agora credentials
    await manager.send_personal_message({
        "type": "start_stream",
        "stream_type": "microphone",
        "agora": stream_info
    }, pc_id)
    
    return {
        "status": "success",
        "message": f"Microphone stream started for PC '{pc_id}'",
        "pc_id": pc_id,
        "stream_type": "microphone",
        "agora": stream_info
    }


@router.post("/{pc_id}/screen/start")
async def start_screen_stream(pc_id: str):
    """Start screen share stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    agora_service.stop_stream(pc_id)
    
    # Start screen stream
    stream_info = agora_service.start_stream(pc_id, "screen")
    
    # Send start command to PC via WebSocket with Agora credentials
    await manager.send_personal_message({
        "type": "start_stream",
        "stream_type": "screen",
        "agora": stream_info
    }, pc_id)
    
    return {
        "status": "success",
        "message": f"Screen stream started for PC '{pc_id}'",
        "pc_id": pc_id,
        "stream_type": "screen",
        "agora": stream_info
    }


@router.post("/{pc_id}/stop")
async def stop_stream(pc_id: str):
    """Stop any active stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Get active stream type
    stream_type = agora_service.get_active_stream(pc_id)
    
    # Stop stream
    success = agora_service.stop_stream(pc_id)
    
    if success:
        # Notify PC to stop
        await manager.send_personal_message({
            "type": "stop_stream"
        }, pc_id)
        
        return {
            "status": "success",
            "message": f"Stream stopped for PC '{pc_id}'",
            "pc_id": pc_id,
            "stream_type": stream_type
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to stop stream")


@router.get("/{pc_id}/status")
async def get_stream_status(pc_id: str):
    """Get current stream status for a PC"""
    stream_type = agora_service.get_active_stream(pc_id)
    has_stream = agora_service.has_active_stream(pc_id)
    is_connected = manager.is_connected(pc_id)
    
    return {
        "pc_id": pc_id,
        "has_active_stream": has_stream,
        "stream_type": stream_type,
        "connected": is_connected
    }


@router.get("/{pc_id}/token")
async def get_subscriber_token(pc_id: str, stream_type: str, uid: int = 0):
    """Get Agora token for frontend to subscribe to stream"""
    if not agora_service.has_active_stream(pc_id):
        raise HTTPException(status_code=404, detail=f"No active {stream_type} stream for PC '{pc_id}'")
    
    token_info = agora_service.get_subscriber_token(pc_id, stream_type, uid)
    
    return {
        "status": "success",
        "pc_id": pc_id,
        "stream_type": stream_type,
        "agora": token_info
    }

