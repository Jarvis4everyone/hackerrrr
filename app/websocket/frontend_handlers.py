"""
WebSocket Handlers for Frontend WebRTC Signaling
"""
import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from app.services.webrtc_service import webrtc_service
from app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)


async def handle_frontend_websocket(websocket: WebSocket, pc_id: str, stream_type: str):
    """Handle WebSocket connection for frontend WebRTC signaling"""
    try:
        await websocket.accept()
        logger.info(f"[Frontend WebRTC] Frontend connected for {pc_id} {stream_type} stream")
        
        # Wait for PC's peer connection and tracks to be available
        pc_connection = None
        max_wait = 20  # Wait up to 20 seconds for tracks (increased for slower connections)
        wait_count = 0
        
        # Map stream_type to WebRTC track kind
        # camera -> video, microphone -> audio, screen -> video
        if stream_type == "camera" or stream_type == "screen":
            track_kind = "video"
        elif stream_type == "microphone":
            track_kind = "audio"
        else:
            track_kind = stream_type
        
        # First, wait for peer connection to exist
        logger.info(f"[Frontend WebRTC] Waiting for PC '{pc_id}' peer connection...")
        while wait_count < max_wait:
            pc_connection = webrtc_service.peer_connections.get(pc_id)
            if pc_connection:
                logger.info(f"[Frontend WebRTC] Peer connection found, checking for {track_kind} tracks...")
                break
            await asyncio.sleep(0.5)
            wait_count += 1
        
        # Now wait for tracks to be available
        wait_count = 0
        while wait_count < max_wait and pc_connection:
            # Check stored tracks first
            pc_tracks = webrtc_service.get_pc_tracks(pc_id, track_kind)
            if pc_tracks:
                logger.info(f"[Frontend WebRTC] Found {len(pc_tracks)} {track_kind} track(s) in stored tracks")
                break
            
            # Also check transceivers (tracks might be there but not stored yet)
            for transceiver in pc_connection.getTransceivers():
                if transceiver.receiver and transceiver.receiver.track:
                    track = transceiver.receiver.track
                    if track.kind == track_kind:
                        logger.info(f"[Frontend WebRTC] Found {track_kind} track in transceiver")
                        pc_tracks = [track]
                        break
            
            if pc_tracks:
                break
                
            await asyncio.sleep(0.5)
            wait_count += 1
        
        if not pc_connection:
            logger.warning(f"[Frontend WebRTC] No peer connection for PC '{pc_id}', waiting...")
            # Wait a bit more for the connection
            await asyncio.sleep(2)
            pc_connection = webrtc_service.peer_connections.get(pc_id)
            if not pc_connection:
                await websocket.send_json({
                    "type": "webrtc_error",
                    "message": f"No active stream for PC '{pc_id}'. Please start the stream first."
                })
                return
        
        # Get track from PC connection and relay to frontend
        pc_tracks = webrtc_service.get_pc_tracks(pc_id, track_kind)
        
        if not pc_tracks:
            # Fallback: try to get tracks from transceivers
            pc_tracks = []
            for transceiver in pc_connection.getTransceivers():
                if transceiver.receiver and transceiver.receiver.track:
                    track = transceiver.receiver.track
                    if track.kind == track_kind:
                        pc_tracks.append(track)
        
        if not pc_tracks:
            logger.warning(f"[Frontend WebRTC] No {track_kind} tracks found for PC '{pc_id}', waiting a bit more...")
            # Wait a bit more for tracks to arrive (PC might still be setting up)
            for retry in range(4):  # 4 more retries, 2 seconds each = 8 more seconds
                await asyncio.sleep(2)
                
                # Check stored tracks
                pc_tracks = webrtc_service.get_pc_tracks(pc_id, track_kind)
                if pc_tracks:
                    logger.info(f"[Frontend WebRTC] Found {track_kind} tracks after retry {retry + 1}")
                    break
                
                # Check transceivers
                if pc_connection:
                    for transceiver in pc_connection.getTransceivers():
                        if transceiver.receiver and transceiver.receiver.track:
                            track = transceiver.receiver.track
                            if track.kind == track_kind:
                                logger.info(f"[Frontend WebRTC] Found {track_kind} track in transceiver after retry {retry + 1}")
                                pc_tracks = [track]
                                break
                
                if pc_tracks:
                    break
            
            if not pc_tracks:
                logger.error(f"[Frontend WebRTC] No {track_kind} track available after all retries")
                await websocket.send_json({
                    "type": "webrtc_error",
                    "message": f"No {track_kind} track available for PC '{pc_id}' yet. The stream may still be initializing. Please wait a moment and try again."
                })
                return
        
        # Create frontend peer connection to relay video to browser
        frontend_pc = None
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCIceCandidate
            
            # Build ICE servers list
            from app.config import settings
            ice_servers = [
                RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
                RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
            ]
            
            # Add TURN server if configured
            if settings.TURN_SERVER_URL:
                turn_config = {"urls": [settings.TURN_SERVER_URL]}
                if settings.TURN_SERVER_USERNAME and settings.TURN_SERVER_PASSWORD:
                    turn_config["username"] = settings.TURN_SERVER_USERNAME
                    turn_config["credential"] = settings.TURN_SERVER_PASSWORD
                ice_servers.append(RTCIceServer(**turn_config))
                logger.info(f"[Frontend WebRTC] Using TURN server: {settings.TURN_SERVER_URL}")
            
            configuration = RTCConfiguration(iceServers=ice_servers)
            frontend_pc = RTCPeerConnection(configuration=configuration)
            
            # Add tracks to frontend connection using relay
            for track in pc_tracks:
                # Use MediaRelay to share the track
                relayed_track = webrtc_service.relay.subscribe(track)
                frontend_pc.addTrack(relayed_track)
                logger.info(f"[Frontend WebRTC] Added {track.kind} track to frontend connection")
            
            # Create offer (server has the track, so it creates offer)
            offer = await frontend_pc.createOffer()
            await frontend_pc.setLocalDescription(offer)
            
            # Send offer to frontend
            await websocket.send_json({
                "type": "webrtc_offer",
                "sdp": offer.sdp
            })
            logger.info(f"[Frontend WebRTC] Sent offer to frontend")
            
            # Handle ICE candidates from frontend peer connection (server -> frontend)
            @frontend_pc.on("icecandidate")
            async def on_ice_candidate(event):
                try:
                    if not event or not hasattr(event, 'candidate') or not event.candidate:
                        return
                    
                    candidate_obj = event.candidate
                    candidate_str = ""
                    sdp_mid = None
                    sdp_mline_index = None
                    
                    # Check if it's a dict first
                    if isinstance(candidate_obj, dict):
                        candidate_str = candidate_obj.get("candidate", "")
                        sdp_mid = candidate_obj.get("sdpMid")
                        sdp_mline_index = candidate_obj.get("sdpMLineIndex")
                    else:
                        # It's an object, use getattr to safely access attributes
                        candidate_str = str(getattr(candidate_obj, "candidate", ""))
                        sdp_mid = getattr(candidate_obj, "sdpMid", None)
                        sdp_mline_index = getattr(candidate_obj, "sdpMLineIndex", None)
                    
                    # Only send if we have a valid candidate string
                    if candidate_str:
                        candidate_data = {
                            "candidate": candidate_str,
                            "sdpMLineIndex": sdp_mline_index,
                            "sdpMid": sdp_mid
                        }
                        
                        await websocket.send_json({
                            "type": "webrtc_ice_candidate",
                            "candidate": candidate_data
                        })
                except Exception as e:
                    # Log but don't break the connection
                    logger.debug(f"[Frontend WebRTC] Error processing ICE candidate: {e}")
            
            # Handle connection state
            @frontend_pc.on("connectionstatechange")
            async def on_connectionstatechange():
                logger.info(f"[Frontend WebRTC] Frontend connection state: {frontend_pc.connectionState}")
            
            # Listen for messages from frontend
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                    message_type = data.get("type")
                    
                    if message_type == "webrtc_answer":
                        # Frontend sends answer
                        answer_sdp = data.get("sdp")
                        if answer_sdp:
                            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
                            await frontend_pc.setRemoteDescription(answer)
                            logger.info(f"[Frontend WebRTC] Received answer from frontend")
                    
                    elif message_type == "webrtc_ice_candidate":
                        # Frontend sends ICE candidate
                        candidate_data = data.get("candidate")
                        if candidate_data:
                            try:
                                # Parse candidate string: "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host"
                                candidate_str = candidate_data.get("candidate", "")
                                if candidate_str and candidate_str.startswith("candidate:"):
                                    # Remove "candidate:" prefix and split
                                    candidate_line = candidate_str.replace("candidate:", "").strip()
                                    parts = candidate_line.split()
                                    
                                    if len(parts) >= 8:
                                        # Format: foundation component protocol priority ip port typ type
                                        foundation = parts[0]
                                        component = int(parts[1])
                                        protocol = parts[2]
                                        priority = int(parts[3])
                                        ip = parts[4]
                                        port = int(parts[5])
                                        typ = parts[6]  # "typ"
                                        type_val = parts[7]  # "host", "srflx", "relay", etc.
                                        
                                        # Get optional fields
                                        sdp_mid = candidate_data.get("sdpMid")
                                        sdp_mline_index = candidate_data.get("sdpMLineIndex")
                                        
                                        ice_candidate = RTCIceCandidate(
                                            component=component,
                                            foundation=foundation,
                                            ip=ip,
                                            port=port,
                                            priority=priority,
                                            protocol=protocol,
                                            type=type_val,
                                            sdpMLineIndex=sdp_mline_index,
                                            sdpMid=sdp_mid
                                        )
                                        await frontend_pc.addIceCandidate(ice_candidate)
                                        logger.debug(f"[Frontend WebRTC] Added ICE candidate from frontend")
                                    else:
                                        logger.debug(f"[Frontend WebRTC] Invalid candidate format: {candidate_str}")
                            except Exception as e:
                                # Log but don't break - ICE candidates help but aren't always required
                                logger.debug(f"[Frontend WebRTC] Could not parse/add ICE candidate: {e}")
                    
                except asyncio.TimeoutError:
                    # Send keepalive
                    try:
                        await websocket.send_json({"type": "ping"})
                    except:
                        break
                
        except Exception as e:
            logger.error(f"[Frontend WebRTC] Error: {e}", exc_info=True)
            try:
                await websocket.send_json({
                    "type": "webrtc_error",
                    "message": str(e)
                })
            except:
                pass
        finally:
            if frontend_pc:
                try:
                    await frontend_pc.close()
                except:
                    pass
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[Frontend WebRTC] WebSocket error: {e}")
    finally:
        logger.info(f"[Frontend WebRTC] Frontend disconnected for {pc_id}")

