"""
WebRTC Service - Manages WebRTC peer connections for streaming
"""
from typing import Dict, Optional
import logging
import asyncio

# Try to import aiortc, but make it optional
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCIceCandidate
    from aiortc.contrib.media import MediaPlayer, MediaRelay
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    # Create dummy classes to prevent import errors
    class RTCPeerConnection:
        pass
    class RTCSessionDescription:
        pass
    class RTCConfiguration:
        pass
    class RTCIceServer:
        pass
    class RTCIceCandidate:
        pass
    class MediaPlayer:
        pass
    class MediaRelay:
        pass

import logging
logger = logging.getLogger(__name__)

if not WEBRTC_AVAILABLE:
    logger.warning("aiortc not available. WebRTC features will be disabled. Install with: pip install aiortc")


class WebRTCService:
    """Service for managing WebRTC connections"""
    
    def __init__(self):
        # Store active peer connections: {pc_id: RTCPeerConnection}
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        # Store active stream types: {pc_id: "camera" | "microphone" | "screen"}
        self.active_streams: Dict[str, str] = {}
        # Store received tracks from PCs: {pc_id: [tracks]}
        self.pc_tracks: Dict[str, list] = {}
        # Media relay for sharing media tracks
        self.relay = MediaRelay()
        # Store ICE candidate callbacks: {pc_id: callback_function}
        self.ice_candidate_callbacks: Dict[str, callable] = {}
    
    async def create_peer_connection(self, pc_id: str, on_ice_candidate=None) -> RTCPeerConnection:
        """Create a new RTCPeerConnection for a PC"""
        if not WEBRTC_AVAILABLE:
            raise RuntimeError("WebRTC is not available. Install aiortc: pip install aiortc")
        
        # Stop any existing stream first
        await self.stop_stream(pc_id)
        
        # Build ICE servers list
        ice_servers = [
            RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
            RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
        ]
        
        # Add TURN server if configured
        from app.config import settings
        if settings.TURN_SERVER_URL:
            turn_config = {"urls": [settings.TURN_SERVER_URL]}
            if settings.TURN_SERVER_USERNAME and settings.TURN_SERVER_PASSWORD:
                turn_config["username"] = settings.TURN_SERVER_USERNAME
                turn_config["credential"] = settings.TURN_SERVER_PASSWORD
            ice_servers.append(RTCIceServer(**turn_config))
            logger.info(f"[WebRTC] Using TURN server: {settings.TURN_SERVER_URL}")
        
        # Create peer connection with ICE servers
        configuration = RTCConfiguration(iceServers=ice_servers)
        
        pc = RTCPeerConnection(configuration=configuration)
        self.peer_connections[pc_id] = pc
        
        # Handle incoming tracks
        @pc.on("track")
        def on_track(track):
            logger.info(f"[WebRTC] {pc_id} received track: {track.kind}")
            # Store track for relaying to frontend
            if pc_id not in self.pc_tracks:
                self.pc_tracks[pc_id] = []
            self.pc_tracks[pc_id].append(track)
        
        # Handle ICE candidates - send to PC client
        @pc.on("icecandidate")
        async def on_ice_candidate_event(event):
            if event.candidate:
                # Call the provided callback if available
                if on_ice_candidate:
                    await on_ice_candidate(pc_id, event.candidate)
                # Also call stored callback if available
                if pc_id in self.ice_candidate_callbacks:
                    callback = self.ice_candidate_callbacks[pc_id]
                    if callback:
                        await callback(pc_id, event.candidate)
        
        # Handle connection state changes
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"[WebRTC] {pc_id} connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed", "disconnected"]:
                await self.cleanup_connection(pc_id)
        
        return pc
    
    async def start_camera_stream(self, pc_id: str, on_ice_candidate=None) -> bool:
        """Start camera stream for a PC"""
        try:
            # Stop any existing stream
            await self.stop_stream(pc_id)
            
            # Create peer connection with ICE candidate handler
            if pc_id not in self.peer_connections:
                await self.create_peer_connection(pc_id, on_ice_candidate)
            
            pc = self.peer_connections[pc_id]
            
            # Mark stream as active (PC will provide the track)
            self.active_streams[pc_id] = "camera"
            
            logger.info(f"[WebRTC] Started camera stream for {pc_id}")
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error starting camera stream for {pc_id}: {e}")
            await self.cleanup_connection(pc_id)
            return False
    
    async def start_microphone_stream(self, pc_id: str, on_ice_candidate=None) -> bool:
        """Start microphone stream for a PC"""
        try:
            # Stop any existing stream
            await self.stop_stream(pc_id)
            
            # Create peer connection with ICE candidate handler
            if pc_id not in self.peer_connections:
                await self.create_peer_connection(pc_id, on_ice_candidate)
            
            pc = self.peer_connections[pc_id]
            
            # Mark stream as active (PC will provide the track)
            self.active_streams[pc_id] = "microphone"
            
            logger.info(f"[WebRTC] Started microphone stream for {pc_id}")
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error starting microphone stream for {pc_id}: {e}")
            await self.cleanup_connection(pc_id)
            return False
    
    async def start_screen_stream(self, pc_id: str, on_ice_candidate=None) -> bool:
        """Start screen share stream for a PC"""
        try:
            # Stop any existing stream
            await self.stop_stream(pc_id)
            
            # Create peer connection with ICE candidate handler
            if pc_id not in self.peer_connections:
                await self.create_peer_connection(pc_id, on_ice_candidate)
            
            pc = self.peer_connections[pc_id]
            
            # Mark stream as active (PC will provide the track)
            self.active_streams[pc_id] = "screen"
            
            logger.info(f"[WebRTC] Started screen stream for {pc_id}")
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error starting screen stream for {pc_id}: {e}")
            await self.cleanup_connection(pc_id)
            return False
    
    async def stop_stream(self, pc_id: str) -> bool:
        """Stop any active stream for a PC"""
        try:
            if pc_id in self.peer_connections:
                pc = self.peer_connections[pc_id]
                
                # Close all tracks
                for sender in pc.getSenders():
                    if sender.track:
                        sender.track.stop()
                
                # Close peer connection
                await pc.close()
                del self.peer_connections[pc_id]
            
            if pc_id in self.active_streams:
                stream_type = self.active_streams[pc_id]
                del self.active_streams[pc_id]
                logger.info(f"[WebRTC] Stopped {stream_type} stream for {pc_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error stopping stream for {pc_id}: {e}")
            return False
    
    async def handle_offer(self, pc_id: str, offer_sdp: str, ice_candidate_callback=None) -> Optional[str]:
        """Handle WebRTC offer from PC and return answer"""
        try:
            # Store ICE candidate callback for this PC
            if ice_candidate_callback:
                self.ice_candidate_callbacks[pc_id] = ice_candidate_callback
            
            if pc_id not in self.peer_connections:
                logger.warning(f"[WebRTC] No peer connection for {pc_id}, creating new one")
                await self.create_peer_connection(pc_id, ice_candidate_callback)
            
            pc = self.peer_connections[pc_id]
            
            # Create offer object
            offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
            
            # Set remote description
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            logger.info(f"[WebRTC] Created answer for {pc_id}, SDP length: {len(answer.sdp)}")
            
            # Log connection state
            logger.info(f"[WebRTC] {pc_id} connection state after answer: {pc.connectionState}")
            
            return pc.localDescription.sdp
            
        except Exception as e:
            logger.error(f"[WebRTC] Error handling offer for {pc_id}: {e}", exc_info=True)
            await self.cleanup_connection(pc_id)
            return None
    
    async def handle_answer(self, pc_id: str, answer_sdp: str) -> bool:
        """Handle WebRTC answer from PC"""
        try:
            if pc_id not in self.peer_connections:
                logger.warning(f"[WebRTC] No peer connection for {pc_id}")
                return False
            
            pc = self.peer_connections[pc_id]
            
            # Create answer object
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            
            # Set remote description
            await pc.setRemoteDescription(answer)
            
            logger.info(f"[WebRTC] Set answer for {pc_id}")
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error handling answer for {pc_id}: {e}")
            return False
    
    async def handle_ice_candidate(self, pc_id: str, candidate) -> bool:
        """Handle ICE candidate from PC"""
        try:
            if pc_id not in self.peer_connections:
                return False
            
            pc = self.peer_connections[pc_id]
            
            # If candidate is already an RTCIceCandidate object, use it directly
            # If it's a dict, create RTCIceCandidate from it
            if isinstance(candidate, dict):
                ice_candidate = RTCIceCandidate(
                    candidate=candidate.get("candidate", ""),
                    sdpMLineIndex=candidate.get("sdpMLineIndex"),
                    sdpMid=candidate.get("sdpMid")
                )
            else:
                ice_candidate = candidate
            
            await pc.addIceCandidate(ice_candidate)
            
            return True
            
        except Exception as e:
            logger.error(f"[WebRTC] Error handling ICE candidate for {pc_id}: {e}")
            return False
    
    async def cleanup_connection(self, pc_id: str):
        """Clean up WebRTC connection for a PC"""
        await self.stop_stream(pc_id)
        if pc_id in self.pc_tracks:
            del self.pc_tracks[pc_id]
        if pc_id in self.ice_candidate_callbacks:
            del self.ice_candidate_callbacks[pc_id]
    
    def get_pc_tracks(self, pc_id: str, track_kind: str = None):
        """Get tracks for a PC, optionally filtered by kind"""
        tracks = self.pc_tracks.get(pc_id, [])
        if track_kind:
            return [t for t in tracks if t.kind == track_kind]
        return tracks
    
    def get_active_stream(self, pc_id: str) -> Optional[str]:
        """Get active stream type for a PC"""
        return self.active_streams.get(pc_id)
    
    def has_active_stream(self, pc_id: str) -> bool:
        """Check if PC has an active stream"""
        return pc_id in self.active_streams


# Global WebRTC service instance
webrtc_service = WebRTCService()

