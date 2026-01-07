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
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["Files"])


def validate_file_path(file_path: str) -> None:
    """
    Validate that file path is relative to executable directory and not from user folders.
    
    Args:
        file_path: Path to validate
    
    Raises:
        HTTPException: If path is invalid
    """
    # Check if path is absolute (reject absolute paths)
    if os.path.isabs(file_path):
        raise HTTPException(
            status_code=400,
            detail="File path must be relative to executable directory, not absolute. "
                   "Do not use paths like C:\\Users\\... or /home/user/..."
        )
    
    # Reject user folder paths
    user_folder_indicators = ['Users', 'Documents', 'Pictures', 'Music', 'Downloads', 'Desktop', 'Videos']
    file_path_lower = file_path.lower()
    for indicator in user_folder_indicators:
        if indicator.lower() in file_path_lower:
            raise HTTPException(
                status_code=400,
                detail=f"File path must be from executable directory, not user folders. "
                       f"Found '{indicator}' in path. Only use paths from: Audios/, build/, logs/"
            )
    
    # Validate path is in allowed folders (relative to exe directory)
    allowed_folders = ['build', 'Audios', 'Photos', 'logs']
    # Get first part of path (handle both / and \ separators)
    first_part = file_path.replace('\\', '/').split('/')[0]
    if first_part not in allowed_folders:
        raise HTTPException(
            status_code=400,
            detail=f"File path must be in one of these folders (relative to executable directory): {allowed_folders}. "
                   f"Got: '{first_part}'. Example: 'Audios/audio (1).mp3', 'Photos/1.jpg', or 'build/WindowsMalwareProtection/file.pkg'"
        )
    
    # Reject path traversal attempts
    if '..' in file_path:
        raise HTTPException(
            status_code=400,
            detail="Path traversal (..) is not allowed. Use paths relative to executable directory only."
        )


@router.post("/download")
async def request_file_download(
    pc_id: str = Query(..., description="PC ID to download from"),
    file_path: str = Query(..., description="Path to the file on the PC (relative to executable directory)")
):
    """
    Request a file download from a PC
    
    Args:
        pc_id: ID of the PC to download from
        file_path: Path to the file on the PC (must be relative to executable directory)
                   Examples: "Audios/audio (1).mp3", "build/WindowsMalwareProtection/file.pkg"
    
    Returns:
        Request ID for tracking the download
    """
    # Validate file path
    try:
        validate_file_path(file_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating file path: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid file path: {str(e)}")
    
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

