"""
WebSocket Connection Manager
"""
from typing import Dict, Optional
from fastapi import WebSocket
from app.services.pc_service import PCService
from app.services.execution_service import ExecutionService
from app.models.execution import ExecutionCreate
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store active WebSocket connections
        # Format: {pc_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, pc_id: str, pc_name: str = None, 
                     ip_address: str = None, hostname: str = None):
        """Accept and register a new WebSocket connection"""
        # Handle reconnection: if PC already has a connection, disconnect the old one first
        if pc_id in self.active_connections:
            old_websocket = self.active_connections[pc_id]
            logger.info(f"[!] PC {pc_id} reconnecting - closing old connection")
            try:
                # Try to close old connection gracefully
                await old_websocket.close()
            except:
                pass
            # Remove old connection
            del self.active_connections[pc_id]
        
        # Accept new connection
        await websocket.accept()
        self.active_connections[pc_id] = websocket
        
        # Extract IP address from WebSocket if not provided
        if not ip_address:
            try:
                client_host = websocket.client.host if websocket.client else None
                ip_address = client_host
            except Exception as e:
                logger.warning(f"Could not extract IP address for {pc_id}: {e}")
        
        # Update PC in database with IP and hostname
        await PCService.create_or_update_pc(
            pc_id=pc_id,
            name=pc_name,
            ip_address=ip_address,
            hostname=hostname
        )
        await PCService.update_connection_status(pc_id, connected=True)
        
        logger.info(f"[+] PC connected: {pc_id} ({pc_name or 'Unknown'}) | IP: {ip_address or 'Unknown'} | Hostname: {hostname or 'Unknown'}")
        return pc_id
    
    async def disconnect(self, pc_id: str):
        """Remove a WebSocket connection"""
        was_connected = pc_id in self.active_connections
        
        if was_connected:
            # Try to close WebSocket gracefully
            try:
                websocket = self.active_connections[pc_id]
                await websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket for {pc_id}: {e}")
            finally:
                del self.active_connections[pc_id]
        
        # Always update database, even if not in active_connections
        # This ensures DB is in sync
        await PCService.update_connection_status(pc_id, connected=False)
        
        if was_connected:
            logger.info(f"[-] PC disconnected: {pc_id}")
        else:
            logger.debug(f"[-] PC {pc_id} disconnect called but was not in active connections")
    
    async def send_personal_message(self, message: dict, pc_id: str) -> bool:
        """Send a message to a specific PC"""
        if pc_id in self.active_connections:
            websocket = self.active_connections[pc_id]
            try:
                await websocket.send_json(message)
                
                # Update last_seen
                await PCService.update_last_seen(pc_id)
                
                logger.debug(f"Message sent successfully to {pc_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending message to {pc_id}: {e}")
                # Disconnect and mark as disconnected in DB
                await self.disconnect(pc_id)
                return False
        else:
            logger.warning(f"PC {pc_id} not in active connections, cannot send message")
            # Check if PC is still marked as connected in DB
            pc = await PCService.get_pc(pc_id)
            if pc and pc.connected:
                logger.warning(f"PC {pc_id} is marked as connected in DB but not in active connections - marking as disconnected")
                await PCService.update_connection_status(pc_id, connected=False)
            return False
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected PCs"""
        disconnected = []
        for pc_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
                await PCService.update_last_seen(pc_id)
            except Exception as e:
                logger.error(f"Error broadcasting to {pc_id}: {e}")
                disconnected.append(pc_id)
        
        # Clean up disconnected clients
        for pc_id in disconnected:
            await self.disconnect(pc_id)
    
    async def send_script(self, pc_id: str, script_name: str, script_content: str, 
                         server_url: str, script_params: Optional[Dict[str, str]] = None) -> bool:
        """Send a script to a PC and create execution record"""
        # Create execution record
        execution = ExecutionCreate(
            pc_id=pc_id,
            script_name=script_name,
            status="pending"
        )
        execution_record = await ExecutionService.create_execution(execution)
        
        # Prepare message
        message = {
            "type": "script",
            "script_name": script_name,
            "script_content": script_content,
            "server_url": server_url,
            "execution_id": str(execution_record.id)
        }
        
        # Add script parameters if provided
        if script_params:
            message["script_params"] = script_params
        
        # Update execution status to executing
        await ExecutionService.update_execution_status(
            str(execution_record.id),
            "executing"
        )
        
        # Send script
        return await self.send_personal_message(message, pc_id)
    
    def is_connected(self, pc_id: str) -> bool:
        """Check if a PC is connected (WebSocket only)"""
        if pc_id not in self.active_connections:
            return False
        
        # Verify the WebSocket is still valid
        websocket = self.active_connections[pc_id]
        try:
            # Check if WebSocket is still open by checking its state
            # FastAPI WebSocket has a client_state attribute
            if hasattr(websocket, 'client_state'):
                # If client_state is None or DISCONNECTED, connection is dead
                if websocket.client_state is None:
                    return False
            return True
        except:
            # If we can't check, assume it's disconnected
            return False
    
    def get_connection(self, pc_id: str) -> Optional[WebSocket]:
        """Get WebSocket connection for a PC"""
        return self.active_connections.get(pc_id)
    
    async def ensure_connection_synced(self, pc_id: str) -> bool:
        """Ensure connection is properly synced between WebSocket and database"""
        is_ws_connected = self.is_connected(pc_id)
        pc = await PCService.get_pc(pc_id)
        is_db_connected = pc and pc.connected if pc else False
        
        # If WebSocket says connected but DB says not, update DB
        if is_ws_connected and not is_db_connected:
            logger.info(f"Syncing connection status for {pc_id}: WebSocket=True, DB=False -> updating DB")
            await PCService.update_connection_status(pc_id, connected=True)
            return True
        
        # If DB says connected but WebSocket says not, update DB
        if not is_ws_connected and is_db_connected:
            logger.info(f"Syncing connection status for {pc_id}: WebSocket=False, DB=True -> updating DB")
            await PCService.update_connection_status(pc_id, connected=False)
            return False
        
        return is_ws_connected
    
    def get_connected_count(self) -> int:
        """Get count of connected PCs"""
        return len(self.active_connections)
    
    def get_connected_pc_ids(self) -> list:
        """Get list of connected PC IDs"""
        return list(self.active_connections.keys())
    
    async def request_file_download(self, pc_id: str, file_path: str, request_id: str) -> bool:
        """
        Request a file download from a PC
        
        Args:
            pc_id: ID of the PC to download from
            file_path: Path to the file on the PC
            request_id: Unique request ID for tracking
        
        Returns:
            True if request was sent successfully
        """
        message = {
            "type": "download_file",
            "file_path": file_path,
            "request_id": request_id,
            "max_size": 100 * 1024 * 1024  # 100 MB
        }
        return await self.send_personal_message(message, pc_id)
    
    async def start_terminal_session(self, pc_id: str, session_id: str) -> bool:
        """
        Start a terminal session on a PC
        
        Args:
            pc_id: ID of the PC
            session_id: Unique session ID
        
        Returns:
            True if request was sent successfully
        """
        message = {
            "type": "start_terminal",
            "session_id": session_id
        }
        return await self.send_personal_message(message, pc_id)
    
    async def send_terminal_command(self, pc_id: str, session_id: str, command: str) -> bool:
        """
        Send a command to an active terminal session
        
        Args:
            pc_id: ID of the PC
            session_id: Session ID
            command: Command to execute
        
        Returns:
            True if command was sent successfully
        """
        message = {
            "type": "terminal_command",
            "session_id": session_id,
            "command": command
        }
        return await self.send_personal_message(message, pc_id)
    
    async def send_terminal_interrupt(self, pc_id: str, session_id: str) -> bool:
        """
        Send interrupt signal (Ctrl+C) to an active terminal session
        
        Args:
            pc_id: ID of the PC
            session_id: Session ID
        
        Returns:
            True if interrupt was sent successfully
        """
        message = {
            "type": "terminal_interrupt",
            "session_id": session_id
        }
        return await self.send_personal_message(message, pc_id)
    
    async def stop_terminal_session(self, pc_id: str, session_id: str) -> bool:
        """
        Stop a terminal session on a PC
        
        Args:
            pc_id: ID of the PC
            session_id: Session ID
        
        Returns:
            True if request was sent successfully
        """
        message = {
            "type": "stop_terminal",
            "session_id": session_id
        }
        return await self.send_personal_message(message, pc_id)


# Global connection manager instance
manager = ConnectionManager()

