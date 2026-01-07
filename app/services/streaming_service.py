"""
Streaming Service
Manages streaming connections for camera, microphone, and screen sharing
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket
import logging
import asyncio

logger = logging.getLogger(__name__)


class StreamingService:
    """Manages streaming connections"""
    
    def __init__(self):
        # Store frontend WebSocket connections for each PC and stream type
        # Format: {pc_id: {stream_type: Set[websocket]}}
        # stream_type: 'camera', 'microphone', 'screen'
        self.frontend_connections: Dict[str, Dict[str, Set[WebSocket]]] = {}
        
        # Store PC streaming status
        # Format: {pc_id: {stream_type: bool}}
        self.pc_streaming_status: Dict[str, Dict[str, bool]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def add_frontend_connection(self, pc_id: str, stream_type: str, websocket: WebSocket):
        """Add a frontend WebSocket connection for receiving streams"""
        async with self._lock:
            if pc_id not in self.frontend_connections:
                self.frontend_connections[pc_id] = {}
            if stream_type not in self.frontend_connections[pc_id]:
                self.frontend_connections[pc_id][stream_type] = set()
            
            self.frontend_connections[pc_id][stream_type].add(websocket)
            logger.info(f"[Streaming] Frontend connected for {pc_id} - {stream_type} (total: {len(self.frontend_connections[pc_id][stream_type])})")
    
    async def remove_frontend_connection(self, pc_id: str, stream_type: str, websocket: WebSocket):
        """Remove a frontend WebSocket connection"""
        async with self._lock:
            if pc_id in self.frontend_connections:
                if stream_type in self.frontend_connections[pc_id]:
                    self.frontend_connections[pc_id][stream_type].discard(websocket)
                    if not self.frontend_connections[pc_id][stream_type]:
                        del self.frontend_connections[pc_id][stream_type]
                    logger.info(f"[Streaming] Frontend disconnected for {pc_id} - {stream_type}")
    
    async def broadcast_to_frontend(self, pc_id: str, stream_type: str, data: dict):
        """Broadcast stream data to all frontend connections for a PC"""
        async with self._lock:
            if pc_id not in self.frontend_connections:
                return
            
            if stream_type not in self.frontend_connections[pc_id]:
                return
            
            # Get a copy of connections to avoid modification during iteration
            connections = list(self.frontend_connections[pc_id][stream_type])
        
        # Broadcast to all frontend connections with timeout
        disconnected = []
        for websocket in connections:
            try:
                # Use asyncio.wait_for to prevent hanging on slow connections
                await asyncio.wait_for(websocket.send_json(data), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning(f"[Streaming] Timeout sending to frontend for {pc_id}/{stream_type}")
                disconnected.append(websocket)
            except Exception as e:
                logger.debug(f"[Streaming] Error sending to frontend: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected connections
        if disconnected:
            async with self._lock:
                if pc_id in self.frontend_connections:
                    if stream_type in self.frontend_connections[pc_id]:
                        for ws in disconnected:
                            self.frontend_connections[pc_id][stream_type].discard(ws)
    
    async def set_pc_streaming_status(self, pc_id: str, stream_type: str, status: bool):
        """Set streaming status for a PC"""
        async with self._lock:
            if pc_id not in self.pc_streaming_status:
                self.pc_streaming_status[pc_id] = {}
            self.pc_streaming_status[pc_id][stream_type] = status
            logger.info(f"[Streaming] {pc_id} - {stream_type}: {'started' if status else 'stopped'}")
    
    async def get_pc_streaming_status(self, pc_id: str, stream_type: str) -> bool:
        """Get streaming status for a PC"""
        async with self._lock:
            if pc_id not in self.pc_streaming_status:
                return False
            return self.pc_streaming_status[pc_id].get(stream_type, False)
    
    async def cleanup_pc_connections(self, pc_id: str):
        """Clean up all connections for a PC"""
        async with self._lock:
            if pc_id in self.frontend_connections:
                # Close all frontend connections
                for stream_type, connections in self.frontend_connections[pc_id].items():
                    for websocket in list(connections):
                        try:
                            await websocket.close()
                        except:
                            pass
                del self.frontend_connections[pc_id]
            
            if pc_id in self.pc_streaming_status:
                del self.pc_streaming_status[pc_id]
            
            logger.info(f"[Streaming] Cleaned up all connections for {pc_id}")


# Global streaming service instance
streaming_service = StreamingService()

