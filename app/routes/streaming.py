"""
Streaming Routes - WebRTC camera, microphone, and screen streaming
"""
from fastapi import APIRouter, HTTPException
from app.websocket.connection_manager import manager
from app.services.webrtc_service import webrtc_service
import logging

logger = logging.getLogger(__name__)


async def send_ice_candidate_to_pc(pc_id: str, candidate):
    """Helper to send ICE candidate to PC via WebSocket"""
    await manager.send_personal_message({
        "type": "webrtc_ice_candidate",
        "candidate": {
            "candidate": candidate.candidate,
            "sdpMLineIndex": candidate.sdpMLineIndex,
            "sdpMid": candidate.sdpMid
        }
    }, pc_id)

router = APIRouter(prefix="/api/streaming", tags=["Streaming"])


@router.post("/{pc_id}/camera/start")
async def start_camera_stream(pc_id: str):
    """Start camera stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    await webrtc_service.stop_stream(pc_id)
    
    # Start camera stream with ICE candidate handler
    success = await webrtc_service.start_camera_stream(
        pc_id,
        on_ice_candidate=send_ice_candidate_to_pc
    )
    
    if success:
        # Send start command to PC via WebSocket
        await manager.send_personal_message({
            "type": "start_stream",
            "stream_type": "camera"
        }, pc_id)
        
        return {
            "status": "success",
            "message": f"Camera stream started for PC '{pc_id}'",
            "pc_id": pc_id,
            "stream_type": "camera"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start camera stream")


@router.post("/{pc_id}/microphone/start")
async def start_microphone_stream(pc_id: str):
    """Start microphone stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    await webrtc_service.stop_stream(pc_id)
    
    # Start microphone stream with ICE candidate handler
    success = await webrtc_service.start_microphone_stream(
        pc_id,
        on_ice_candidate=send_ice_candidate_to_pc
    )
    
    if success:
        # Send start command to PC via WebSocket
        await manager.send_personal_message({
            "type": "start_stream",
            "stream_type": "microphone"
        }, pc_id)
        
        return {
            "status": "success",
            "message": f"Microphone stream started for PC '{pc_id}'",
            "pc_id": pc_id,
            "stream_type": "microphone"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start microphone stream")


@router.post("/{pc_id}/screen/start")
async def start_screen_stream(pc_id: str):
    """Start screen share stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Stop any existing stream first
    await webrtc_service.stop_stream(pc_id)
    
    # Start screen stream with ICE candidate handler
    success = await webrtc_service.start_screen_stream(
        pc_id,
        on_ice_candidate=send_ice_candidate_to_pc
    )
    
    if success:
        # Send start command to PC via WebSocket
        await manager.send_personal_message({
            "type": "start_stream",
            "stream_type": "screen"
        }, pc_id)
        
        return {
            "status": "success",
            "message": f"Screen stream started for PC '{pc_id}'",
            "pc_id": pc_id,
            "stream_type": "screen"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to start screen stream")


@router.post("/{pc_id}/stop")
async def stop_stream(pc_id: str):
    """Stop any active stream for a PC"""
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Get active stream type
    stream_type = webrtc_service.get_active_stream(pc_id)
    
    # Stop stream
    success = await webrtc_service.stop_stream(pc_id)
    
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
    # Don't require PC to be connected - just check if stream exists
    # This allows checking status even if WebSocket connection is temporarily down
    stream_type = webrtc_service.get_active_stream(pc_id)
    has_stream = webrtc_service.has_active_stream(pc_id)
    is_connected = manager.is_connected(pc_id)
    
    # Get connection state info
    pc_connection = webrtc_service.peer_connections.get(pc_id)
    connection_state = None
    ice_state = None
    has_tracks = False
    
    if pc_connection:
        connection_state = pc_connection.connectionState
        ice_state = pc_connection.iceConnectionState
        pc_tracks = webrtc_service.get_pc_tracks(pc_id)
        has_tracks = len(pc_tracks) > 0
    
    return {
        "pc_id": pc_id,
        "has_active_stream": has_stream,
        "stream_type": stream_type,
        "connected": is_connected,
        "connection_state": connection_state,
        "ice_connection_state": ice_state,
        "has_tracks": has_tracks
    }

