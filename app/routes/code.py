"""
Code Execution Routes
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.models.request import ExecuteCodeRequest
from app.services.pc_service import PCService
from app.websocket.connection_manager import manager
from app.services.execution_service import ExecutionService
from app.models.execution import ExecutionCreate
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/code", tags=["Code"])


@router.post("/execute")
async def execute_code(request: ExecuteCodeRequest):
    """
    Execute custom Python code on a specific PC
    
    Request Body (JSON):
    {
        "pc_id": "PC_ID_HERE",
        "code": "print('Hello World')",
        "requirements": "pip install pyqt5" (optional),
        "server_url": "http://server:port" (optional)
    }
    """
    try:
        pc_id = request.pc_id
        code = request.code
        requirements = request.requirements
        server_url = request.server_url
        
        logger.info(f"Attempting to execute custom code on PC '{pc_id}'")
        
        # Validate inputs
        if not pc_id:
            logger.error("Missing pc_id in request")
            raise HTTPException(status_code=400, detail="pc_id is required")
        if not code or not code.strip():
            logger.error("Missing or empty code in request")
            raise HTTPException(status_code=400, detail="code is required and cannot be empty")
        
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
        
        # Use Serverurl from .env if not provided, fallback to default
        try:
            server_url = server_url or settings.SERVER_URL or f"http://{settings.HOST}:{settings.PORT}"
            logger.debug(f"Using server_url: {server_url}")
        except Exception as e:
            logger.error(f"Error determining server_url: {e}", exc_info=True)
            server_url = server_url or "http://0.0.0.0:8000"  # Fallback
        
        # Create execution record
        try:
            execution = ExecutionCreate(
                pc_id=pc_id,
                script_name="custom_code.py",  # Use generic name for custom code
                status="pending"
            )
            execution_record = await ExecutionService.create_execution(execution)
            logger.debug(f"Created execution record {execution_record.id} for custom code on PC '{pc_id}'")
        except Exception as e:
            logger.error(f"Error creating execution record for custom code on PC '{pc_id}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error creating execution record: {str(e)}")
        
        # Prepare message
        try:
            message = {
                "type": "custom_code",
                "code": code,
                "server_url": server_url,
                "execution_id": str(execution_record.id)
            }
            
            # Add requirements if provided
            if requirements and requirements.strip():
                message["requirements"] = requirements.strip()
                logger.debug(f"Including requirements: {requirements}")
            
            logger.debug(f"Prepared custom code message for PC '{pc_id}': execution_id={execution_record.id}, has_requirements={bool(requirements)}")
        except Exception as e:
            logger.error(f"Error preparing custom code message for PC '{pc_id}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error preparing code message: {str(e)}")
        
        # Update execution status to executing
        try:
            await ExecutionService.update_execution_status(
                str(execution_record.id),
                "executing"
            )
            logger.debug(f"Updated execution {execution_record.id} status to 'executing'")
        except Exception as e:
            logger.warning(f"Error updating execution status (non-fatal): {e}", exc_info=True)
            # Continue even if status update fails
        
        # Send code to PC
        try:
            success = await manager.send_personal_message(message, pc_id)
            if success:
                logger.info(f"Custom code sent successfully to PC '{pc_id}' (execution_id: {execution_record.id})")
            else:
                logger.warning(f"Failed to send custom code to PC '{pc_id}' - WebSocket message send failed")
                raise HTTPException(status_code=500, detail="Failed to send code to PC - PC may have disconnected")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending custom code message to PC '{pc_id}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error sending code to PC: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Code sent to PC '{pc_id}' for execution",
            "pc_id": pc_id,
            "execution_id": str(execution_record.id),
            "has_requirements": bool(requirements)
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error in execute_code endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

