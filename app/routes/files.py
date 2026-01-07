"""
File Routes - File download management
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from app.services.file_service import FileService
from app.websocket.connection_manager import manager
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.post("/download")
async def request_file_download(
    pc_id: str = Query(..., description="PC ID to download from"),
    file_path: str = Query(..., description="Path to the file on the PC")
):
    """
    Request a file download from a PC
    
    Args:
        pc_id: ID of the PC to download from
        file_path: Path to the file on the PC
    
    Returns:
        Request ID for tracking the download
    """
    # Check if PC is connected
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Send download request to PC
    success = await manager.request_file_download(pc_id, file_path, request_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send download request to PC")
    
    return {
        "request_id": request_id,
        "pc_id": pc_id,
        "file_path": file_path,
        "status": "requested"
    }


@router.get("")
async def list_files(pc_id: Optional[str] = Query(None, description="Filter by PC ID")):
    """
    List all downloaded files, optionally filtered by PC ID
    
    Args:
        pc_id: Optional PC ID to filter files
    
    Returns:
        List of file information
    """
    try:
        files = FileService.list_files(pc_id=pc_id)
        total_size = FileService.get_total_size()
        
        return {
            "total": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": files
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.get("/{file_id}")
async def download_file(file_id: str, pc_id: str = Query(..., description="PC ID that owns the file")):
    """
    Download a file from the server
    
    Args:
        file_id: File ID
        pc_id: PC ID that owns the file
    
    Returns:
        File download response
    """
    try:
        file_path = FileService.get_file(file_id, pc_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=str(file_path),
            filename=file_path.name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@router.delete("/{file_id}")
async def delete_file(file_id: str, pc_id: str = Query(..., description="PC ID that owns the file")):
    """
    Delete a downloaded file
    
    Args:
        file_id: File ID
        pc_id: PC ID that owns the file
    
    Returns:
        Success status
    """
    try:
        success = FileService.delete_file(file_id, pc_id)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"success": True, "message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

