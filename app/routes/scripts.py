"""
Script Routes
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict
from app.services.script_service import ScriptService
from app.services.pc_service import PCService
from app.websocket.connection_manager import manager
from app.models.request import SendScriptRequest, BroadcastScriptRequest
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scripts", tags=["Scripts"])


@router.get("")
async def list_scripts():
    """List all available scripts from filesystem"""
    scripts = await ScriptService.list_scripts()
    return {
        "total": len(scripts),
        "scripts": [script.dict() for script in scripts]
    }


@router.post("/send")
async def send_script(request: SendScriptRequest):
    """
    Send a script to a specific PC
    
    Request Body (JSON):
    {
        "pc_id": "PC_ID_HERE",
        "script_name": "script_name.py",
        "server_url": "http://server:port" (optional),
        "script_params": {
            "PARAM_NAME": "value"
        } (optional)
    }
    """
    try:
        pc_id = request.pc_id
        script_name = request.script_name
        server_url = request.server_url
        params_to_use = request.script_params
        
        logger.info(f"Attempting to send script '{script_name}' to PC '{pc_id}'")
        
        # Validate inputs
        if not pc_id:
            logger.error("Missing pc_id in request")
            raise HTTPException(status_code=400, detail="pc_id is required")
        if not script_name:
            logger.error("Missing script_name in request")
            raise HTTPException(status_code=400, detail="script_name is required")
        
        # Sync connection status between WebSocket and database
        try:
            is_ws_connected = await manager.ensure_connection_synced(pc_id)
            logger.info(f"PC '{pc_id}' connection status after sync: WebSocket={is_ws_connected}")
        except Exception as e:
            logger.error(f"Error syncing connection status for PC '{pc_id}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error checking PC connection: {str(e)}")
        
        # Only proceed if WebSocket connection is actually active
        if not is_ws_connected:
            logger.warning(f"PC '{pc_id}' is not connected (WebSocket connection not active)")
            raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
        
        # Get script content
        try:
            script_content = await ScriptService.get_script_content(script_name)
            if not script_content:
                logger.error(f"Script '{script_name}' not found or empty")
                raise HTTPException(status_code=404, detail=f"Script '{script_name}' not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading script '{script_name}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error reading script: {str(e)}")
        
        # Use Serverurl from .env if not provided, fallback to default
        try:
            server_url = server_url or settings.SERVER_URL or f"http://{settings.HOST}:{settings.PORT}"
            logger.debug(f"Using server_url: {server_url}")
        except Exception as e:
            logger.error(f"Error determining server_url: {e}", exc_info=True)
            server_url = server_url or "http://0.0.0.0:8000"  # Fallback
        
        # Send script with parameters
        try:
            success = await manager.send_script(pc_id, script_name, script_content, server_url, params_to_use)
            logger.info(f"Script send result for '{script_name}' to PC '{pc_id}': {success}")
        except Exception as e:
            logger.error(f"Error sending script '{script_name}' to PC '{pc_id}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error sending script to PC: {str(e)}")
        
        if success:
            return {
                "status": "success",
                "message": f"Script '{script_name}' sent to PC '{pc_id}'",
                "pc_id": pc_id,
                "script_name": script_name
            }
        else:
            logger.warning(f"Failed to send script '{script_name}' to PC '{pc_id}' (send_script returned False)")
            raise HTTPException(status_code=500, detail="Failed to send script - PC may have disconnected")
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in send_script endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/broadcast")
async def broadcast_script(request: BroadcastScriptRequest):
    """
    Broadcast a script to all connected PCs
    
    Request Body (JSON):
    {
        "script_name": "script_name.py",
        "server_url": "http://server:port" (optional),
        "script_params": {
            "PARAM_NAME": "value"
        } (optional)
    }
    """
    script_name = request.script_name
    server_url = request.server_url
    params_to_use = request.script_params
    
    # Get script content
    script_content = await ScriptService.get_script_content(script_name)
    if not script_content:
        raise HTTPException(status_code=404, detail=f"Script '{script_name}' not found")
    
    # Use Serverurl from .env if not provided, fallback to default
    server_url = server_url or settings.SERVER_URL or f"http://{settings.HOST}:{settings.PORT}"
    
    # Broadcast to all PCs
    connected_pcs = manager.get_connected_pc_ids()
    for pc_id in connected_pcs:
        await manager.send_script(pc_id, script_name, script_content, server_url, params_to_use)
    
    return {
        "status": "success",
        "message": f"Script '{script_name}' broadcasted to {len(connected_pcs)} PC(s)",
        "script_name": script_name,
        "recipients": len(connected_pcs)
    }

