"""
WebSocket Connection Manager
"""
from typing import Dict, Optional
from fastapi import WebSocket
from app.services.pc_service import PCService
from app.services.execution_service import ExecutionService
from app.models.execution import ExecutionCreate
import logging
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Store active WebSocket connections
        # Format: {pc_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        # Lock to prevent simultaneous connection attempts for same PC
        self._connection_locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()
    
    async def _get_lock(self, pc_id: str) -> asyncio.Lock:
        """Get or create a lock for a PC ID"""
        async with self._locks_lock:
            if pc_id not in self._connection_locks:
                self._connection_locks[pc_id] = asyncio.Lock()
            return self._connection_locks[pc_id]
    
    async def connect(self, websocket: WebSocket, pc_id: str, pc_name: str = None, 
                     ip_address: str = None, hostname: str = None):
        """Accept and register a new WebSocket connection"""
        # Use lock to prevent simultaneous connections for same PC
        lock = await self._get_lock(pc_id)
        async with lock:
            # Handle reconnection: if PC already has a connection, disconnect the old one first
            if pc_id in self.active_connections:
                old_websocket = self.active_connections[pc_id]
                logger.info(f"[!] PC {pc_id} reconnecting - closing old connection")
                try:
                    # Check if old WebSocket is still open before closing
                    try:
                        # Try to close old connection gracefully
                        if hasattr(old_websocket, 'client_state') and old_websocket.client_state.name != "DISCONNECTED":
                            await old_websocket.close(code=1000, reason="Reconnecting")
                    except Exception as e:
                        logger.debug(f"Error closing old WebSocket for {pc_id}: {e}")
                except Exception as e:
                    logger.debug(f"Error checking old WebSocket state for {pc_id}: {e}")
                finally:
                    # Always remove old connection from dict, even if close failed
                    if pc_id in self.active_connections:
                        del self.active_connections[pc_id]
            
            # Verify WebSocket is in correct state before accepting
            try:
                # Check if WebSocket is already accepted or in wrong state
                if hasattr(websocket, 'client_state'):
                    state = websocket.client_state.name
                    if state == "CONNECTED":
                        logger.warning(f"WebSocket for {pc_id} already connected, skipping accept")
                        # Still add to active connections if not already there
                        if pc_id not in self.active_connections:
                            self.active_connections[pc_id] = websocket
                    elif state == "DISCONNECTED":
                        logger.error(f"WebSocket for {pc_id} is already disconnected, cannot accept")
                        raise Exception("WebSocket is already disconnected")
                    else:
                        # Accept new connection
                        await websocket.accept()
                        # Verify it was accepted
                        if hasattr(websocket, 'client_state'):
                            new_state = websocket.client_state.name
                            if new_state != "CONNECTED":
                                raise Exception(f"WebSocket accept failed, state is {new_state}")
                        self.active_connections[pc_id] = websocket
                else:
                    # Fallback: accept anyway if client_state not available
                    await websocket.accept()
                    self.active_connections[pc_id] = websocket
            except Exception as e:
                logger.error(f"Error accepting WebSocket for {pc_id}: {e}")
                # Remove from active connections if accept failed
                if pc_id in self.active_connections:
                    del self.active_connections[pc_id]
                raise
        
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
        if pc_id not in self.active_connections:
            logger.warning(f"PC {pc_id} not in active connections, cannot send message")
            # Check if PC is still marked as connected in DB
            pc = await PCService.get_pc(pc_id)
            if pc and pc.connected:
                logger.warning(f"PC {pc_id} is marked as connected in DB but not in active connections - marking as disconnected")
                await PCService.update_connection_status(pc_id, connected=False)
            return False
        
        websocket = self.active_connections[pc_id]
        
        # Check if WebSocket is still open before sending
        try:
            # Check WebSocket state - if it's disconnected, don't try to send
            if hasattr(websocket, 'client_state'):
                state = websocket.client_state.name
                if state == "DISCONNECTED":
                    logger.warning(f"WebSocket for {pc_id} is already disconnected, removing from active connections")
                    if pc_id in self.active_connections:
                        del self.active_connections[pc_id]
                    await PCService.update_connection_status(pc_id, connected=False)
                    return False
        except Exception as e:
            logger.debug(f"Error checking WebSocket state for {pc_id}: {e}")
            # Continue anyway - try to send and catch error if it fails
        
        try:
            await websocket.send_json(message)
            
            # Update last_seen
            await PCService.update_last_seen(pc_id)
            
            logger.debug(f"Message sent successfully to {pc_id}")
            return True
        except Exception as e:
            error_msg = str(e)
            # Check for specific error messages
            if "close message has been sent" in error_msg or "not connected" in error_msg.lower() or "accept" in error_msg.lower():
                logger.warning(f"WebSocket for {pc_id} is closed or not accepted: {e}")
            else:
                logger.error(f"Error sending message to {pc_id}: {e}")
            
            # Disconnect and mark as disconnected in DB
            await self.disconnect(pc_id)
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
        try:
            # Create execution record
            try:
                execution = ExecutionCreate(
                    pc_id=pc_id,
                    script_name=script_name,
                    status="pending"
                )
                execution_record = await ExecutionService.create_execution(execution)
                logger.debug(f"Created execution record {execution_record.id} for script '{script_name}' on PC '{pc_id}'")
            except Exception as e:
                logger.error(f"Error creating execution record for script '{script_name}' on PC '{pc_id}': {e}", exc_info=True)
                return False
            
            # Prepare message
            try:
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
                
                logger.debug(f"Prepared script message for PC '{pc_id}': script_name={script_name}, execution_id={execution_record.id}, has_params={bool(script_params)}")
            except Exception as e:
                logger.error(f"Error preparing script message for PC '{pc_id}': {e}", exc_info=True)
                return False
            
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
            
            # Send script
            try:
                success = await self.send_personal_message(message, pc_id)
                if success:
                    logger.info(f"Script '{script_name}' sent successfully to PC '{pc_id}' (execution_id: {execution_record.id})")
                else:
                    logger.warning(f"Failed to send script '{script_name}' to PC '{pc_id}' - WebSocket message send failed")
                return success
            except Exception as e:
                logger.error(f"Error sending script message to PC '{pc_id}': {e}", exc_info=True)
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error in send_script for PC '{pc_id}': {e}", exc_info=True)
            return False
    
    def is_connected(self, pc_id: str) -> bool:
        """Check if a PC is connected (WebSocket only)"""
        if pc_id not in self.active_connections:
            return False
        
        # If PC is in active_connections, consider it connected
        # The WebSocket handler will remove it from active_connections on disconnect
        # This is more reliable than checking client_state which may not be available
        return True
    
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
        
        # If DB says connected but WebSocket says not, trust the DB
        # This handles cases where PC is sending heartbeats (updating DB) but WebSocket state check fails
        # If PC is sending heartbeats, it's definitely connected, so trust the DB
        if not is_ws_connected and is_db_connected:
            logger.info(f"Syncing connection status for {pc_id}: WebSocket=False, DB=True -> trusting DB (PC sending heartbeats)")
            # Don't update DB to False - trust that heartbeats are keeping it alive
            # Return True to allow operations to proceed
            return True
        
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
    
    async def send_stop_command(self, pc_id: str) -> bool:
        """
        Send stop command to a PC client to terminate it completely
        
        This is a one-time action - if the PC client restarts,
        it will need to be stopped again.
        
        Args:
            pc_id: ID of the PC to stop
        
        Returns:
            True if command was sent successfully, False otherwise
        """
        message = {
            "type": "stop_pc"
        }
        logger.info(f"Sending stop command to PC: {pc_id}")
        success = await self.send_personal_message(message, pc_id)
        if success:
            logger.info(f"Stop command sent successfully to PC: {pc_id}")
        else:
            logger.warning(f"Failed to send stop command to PC: {pc_id} (PC may not be connected)")
        return success


# Global connection manager instance
manager = ConnectionManager()

