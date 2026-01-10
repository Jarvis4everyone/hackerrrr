"""
Request Models
"""
from typing import Optional, Dict
from pydantic import BaseModel


class SendScriptRequest(BaseModel):
    """Request model for sending script to PC"""
    pc_id: str
    script_name: str
    server_url: Optional[str] = None
    script_params: Optional[Dict[str, str]] = None  # Script parameters


class BroadcastScriptRequest(BaseModel):
    """Request model for broadcasting script"""
    script_name: str
    server_url: Optional[str] = None
    script_params: Optional[Dict[str, str]] = None  # Script parameters


class ExecuteCodeRequest(BaseModel):
    """Request model for executing custom Python code"""
    pc_id: str
    code: str  # Python code to execute
    requirements: Optional[str] = None  # pip install commands (e.g., "pip install pyqt5")
    server_url: Optional[str] = None
