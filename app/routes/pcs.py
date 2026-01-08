"""
PC Routes
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.pc_service import PCService
from app.websocket.connection_manager import manager
from app.models.pc import PCInDB

router = APIRouter(prefix="/api/pcs", tags=["PCs"])


@router.get("", response_model=dict)
async def list_pcs(connected_only: bool = Query(False, description="Filter by connection status")):
    """Get list of all PCs"""
    pcs = await PCService.get_all_pcs(connected_only=connected_only)
    connected_count = await PCService.get_connected_count()
    
    return {
        "total": len(pcs),
        "connected": connected_count,
        "pcs": [pc.dict() for pc in pcs]
    }


@router.get("/{pc_id}", response_model=PCInDB)
async def get_pc(pc_id: str):
    """Get a specific PC by ID"""
    pc = await PCService.get_pc(pc_id)
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' not found")
    return pc


@router.delete("/{pc_id}")
async def delete_pc(pc_id: str):
    """Delete a PC"""
    success = await PCService.delete_pc(pc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' not found")
    return {"status": "success", "message": f"PC '{pc_id}' deleted"}


@router.get("/{pc_id}/connected")
async def check_connection(pc_id: str):
    """Check if a PC is connected"""
    is_connected = manager.is_connected(pc_id)
    return {
        "pc_id": pc_id,
        "connected": is_connected
    }


@router.post("/{pc_id}/stop")
async def stop_pc(pc_id: str):
    """
    Stop a PC client completely (one-time action)
    
    This sends a stop command to the PC client, which will:
    - Terminate all running processes
    - Close all connections
    - Exit the PC client completely
    
    Note: This is a one-time action. If the PC client restarts
    (e.g., via auto-start), it will need to be stopped again.
    """
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Send stop command
    success = await manager.send_stop_command(pc_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Stop command sent to PC '{pc_id}'. The PC client will terminate shortly.",
            "pc_id": pc_id
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send stop command to PC '{pc_id}'. The PC may have disconnected."
        )
