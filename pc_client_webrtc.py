"""
PC Client with WebRTC Support
Complete example showing how to connect and stream camera, microphone, and screen
"""
import asyncio
import json
import os
import sys
import tempfile
import socket
from websockets import connect
from websockets.exceptions import ConnectionClosed
import logging

# WebRTC imports (for Python client)
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaPlayer, MediaRecorder
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    print("[!] WebRTC not available. Install: pip install aiortc")

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "ws://localhost:8000")
PC_ID = os.getenv("PC_ID", socket.gethostname())

# TURN server configuration (optional, for better NAT traversal in production)
TURN_SERVER_URL = os.getenv("TURN_SERVER_URL", None)
TURN_SERVER_USERNAME = os.getenv("TURN_SERVER_USERNAME", None)
TURN_SERVER_PASSWORD = os.getenv("TURN_SERVER_PASSWORD", None)


def normalize_websocket_url(url: str) -> str:
    """
    Convert HTTP/HTTPS URL to WebSocket URL (WS/WSS)
    Handles both http:// and https:// URLs, and already correct ws:///wss:// URLs
    """
    url = url.strip()
    
    # If already a WebSocket URL, return as-is
    if url.startswith("ws://") or url.startswith("wss://"):
        return url
    
    # Convert HTTP to WS
    if url.startswith("http://"):
        return url.replace("http://", "ws://", 1)
    
    # Convert HTTPS to WSS
    if url.startswith("https://"):
        return url.replace("https://", "wss://", 1)
    
    # If no protocol specified, assume WS for localhost, WSS for others
    if "localhost" in url or "127.0.0.1" in url:
        return f"ws://{url}" if not url.startswith("ws") else url
    else:
        return f"wss://{url}" if not url.startswith("ws") else url


def get_ice_servers():
    """Get ICE servers configuration with STUN and optional TURN"""
    ice_servers = [
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun2.l.google.com:19302"]),
    ]
    
    # Add TURN server if configured
    if TURN_SERVER_URL:
        turn_config = {"urls": [TURN_SERVER_URL]}
        if TURN_SERVER_USERNAME and TURN_SERVER_PASSWORD:
            turn_config["username"] = TURN_SERVER_USERNAME
            turn_config["credential"] = TURN_SERVER_PASSWORD
        ice_servers.append(RTCIceServer(**turn_config))
        logger.info(f"[WebRTC] Using TURN server: {TURN_SERVER_URL}")
    
    return ice_servers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce verbosity of aioice logs on client side
logging.getLogger('aioice.ice').setLevel(logging.WARNING)


class PCClientWebRTC:
    """PC Client with WebRTC streaming support"""
    
    def __init__(self, server_url: str, pc_id: str):
        # Normalize WebSocket URL (convert HTTP/HTTPS to WS/WSS)
        self.server_url = normalize_websocket_url(server_url)
        self.pc_id = pc_id
        self.websocket = None
        self.running = False
        self.peer_connection = None
        self.active_stream_type = None
        self.media_player = None
    
    async def connect(self):
        """Connect to the server"""
        uri = f"{self.server_url}/ws/{self.pc_id}"
        logger.info(f"[*] Connecting to {uri}...")
        
        try:
            self.websocket = await connect(uri)
            self.running = True
            logger.info(f"[+] Connected as {self.pc_id}")
            return True
        except Exception as e:
            logger.error(f"[!] Connection failed: {e}")
            return False
    
    async def create_peer_connection(self):
        """Create WebRTC peer connection"""
        if not WEBRTC_AVAILABLE:
            logger.error("[!] WebRTC not available")
            return None
        
        # Use enhanced ICE servers (multiple STUN + optional TURN)
        ice_servers = get_ice_servers()
        configuration = RTCConfiguration(iceServers=ice_servers)
        
        pc = RTCPeerConnection(configuration=configuration)
        
        @pc.on("track")
        def on_track(track):
            logger.info(f"[WebRTC] Received track: {track.kind}")
            # Handle incoming tracks from server if needed
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"[WebRTC] Connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed", "disconnected"]:
                await self.stop_stream()
        
        self.peer_connection = pc
        return pc
    
    async def start_camera_stream(self):
        """Start camera stream"""
        if not WEBRTC_AVAILABLE:
            await self.send_error("WebRTC not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Create peer connection
            pc = await self.create_peer_connection()
            if not pc:
                return
            
            # Get camera track
            # Note: This is a simplified example. In production, you'd use proper camera access
            # For Windows, you might need: MediaPlayer("video=Integrated Camera", format="dshow")
            # For Linux: MediaPlayer("/dev/video0", format="v4l2")
            # For macOS: MediaPlayer("default", format="avfoundation")
            
            # Example for Windows (adjust based on your system)
            try:
                self.media_player = MediaPlayer("video=Integrated Camera", format="dshow")
            except:
                # Fallback for other systems
                try:
                    self.media_player = MediaPlayer("/dev/video0", format="v4l2")
                except:
                    self.media_player = MediaPlayer("default", format="avfoundation")
            
            if self.media_player and self.media_player.video:
                pc.addTrack(self.media_player.video)
                self.active_stream_type = "camera"
                
                # Create offer
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)
                
                # Send offer to server
                await self.websocket.send(json.dumps({
                    "type": "webrtc_offer",
                    "sdp": pc.localDescription.sdp
                }))
                
                logger.info("[WebRTC] Camera stream started, offer sent")
            else:
                await self.send_error("Failed to access camera")
                
        except Exception as e:
            logger.error(f"[!] Error starting camera stream: {e}")
            await self.send_error(f"Camera error: {str(e)}")
    
    async def start_microphone_stream(self):
        """Start microphone stream"""
        if not WEBRTC_AVAILABLE:
            await self.send_error("WebRTC not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Create peer connection
            pc = await self.create_peer_connection()
            if not pc:
                return
            
            # Get microphone track
            # Similar to camera, adjust based on your system
            try:
                self.media_player = MediaPlayer("audio=Microphone", format="dshow")
            except:
                try:
                    self.media_player = MediaPlayer("default", format="pulse")
                except:
                    self.media_player = MediaPlayer("default", format="avfoundation")
            
            if self.media_player and self.media_player.audio:
                pc.addTrack(self.media_player.audio)
                self.active_stream_type = "microphone"
                
                # Create offer
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)
                
                # Send offer to server
                await self.websocket.send(json.dumps({
                    "type": "webrtc_offer",
                    "sdp": pc.localDescription.sdp
                }))
                
                logger.info("[WebRTC] Microphone stream started, offer sent")
            else:
                await self.send_error("Failed to access microphone")
                
        except Exception as e:
            logger.error(f"[!] Error starting microphone stream: {e}")
            await self.send_error(f"Microphone error: {str(e)}")
    
    async def start_screen_stream(self):
        """Start screen share stream"""
        if not WEBRTC_AVAILABLE:
            await self.send_error("WebRTC not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Create peer connection
            pc = await self.create_peer_connection()
            if not pc:
                return
            
            # Get screen share track
            # For screen sharing, you'd typically use a screen capture library
            # This is platform-specific. Example for Windows:
            # You might need to use a screen capture tool or library
            
            # Simplified example - in production, use proper screen capture
            # For now, we'll just set up the connection structure
            self.active_stream_type = "screen"
            
            # Create offer
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            # Send offer to server
            await self.websocket.send(json.dumps({
                "type": "webrtc_offer",
                "sdp": pc.localDescription.sdp
            }))
            
            logger.info("[WebRTC] Screen stream started, offer sent")
            logger.warning("[!] Screen capture implementation is platform-specific")
            logger.warning("[!] You need to implement screen capture based on your OS")
                
        except Exception as e:
            logger.error(f"[!] Error starting screen stream: {e}")
            await self.send_error(f"Screen error: {str(e)}")
    
    async def stop_stream(self):
        """Stop current stream"""
        try:
            if self.peer_connection:
                # Close all tracks
                for sender in self.peer_connection.getSenders():
                    if sender.track:
                        sender.track.stop()
                
                await self.peer_connection.close()
                self.peer_connection = None
            
            if self.media_player:
                self.media_player = None
            
            self.active_stream_type = None
            logger.info("[WebRTC] Stream stopped")
            
        except Exception as e:
            logger.error(f"[!] Error stopping stream: {e}")
    
    async def handle_webrtc_answer(self, answer_sdp: str):
        """Handle WebRTC answer from server"""
        try:
            if not self.peer_connection:
                logger.warning("[WebRTC] No peer connection for answer")
                return
            
            answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
            await self.peer_connection.setRemoteDescription(answer)
            logger.info("[WebRTC] Answer set, connection established")
            
            # Notify server that stream is ready
            await self.websocket.send(json.dumps({
                "type": "webrtc_stream_ready",
                "stream_type": self.active_stream_type
            }))
            
        except Exception as e:
            logger.error(f"[!] Error handling answer: {e}")
    
    async def handle_ice_candidate(self, candidate: dict):
        """Handle ICE candidate from server"""
        try:
            if not self.peer_connection:
                return
            
            await self.peer_connection.addIceCandidate(candidate)
            
        except Exception as e:
            logger.error(f"[!] Error handling ICE candidate: {e}")
    
    async def send_message(self, message: dict):
        """Send a message to the server"""
        if self.websocket and self.running:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"[!] Error sending message: {e}")
                self.running = False
    
    async def send_error(self, message: str):
        """Send error message"""
        await self.send_message({
            "type": "error",
            "message": message
        })
    
    async def execute_script(self, script_content: str, script_name: str, 
                            server_url: str, execution_id: str):
        """Execute a Python script received from server"""
        import subprocess
        from datetime import datetime
        
        logger.info(f"[*] Executing script: {script_name}")
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create log file with proper naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{script_name.replace('.py', '')}_{timestamp}_{execution_id[:8]}.log"
        log_file_path = os.path.join(logs_dir, log_filename)
        
        # Create a custom logger that writes to both file and sends to server
        import logging
        log_handler = logging.FileHandler(log_file_path)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        script_logger = logging.getLogger(f"script_{execution_id}")
        script_logger.setLevel(logging.DEBUG)
        script_logger.addHandler(log_handler)
        
        # Redirect stdout and stderr to capture output
        log_lines = []
        
        class LogCapture:
            def __init__(self, client_instance, log_level="INFO"):
                self.client_instance = client_instance
                self.log_level = log_level
                self.buffer = []
            
            def write(self, message):
                if message.strip():
                    log_lines.append(message.strip())
                    script_logger.log(
                        logging.INFO if self.log_level == "INFO" else logging.ERROR,
                        message.strip()
                    )
                    # Send log to server in real-time (fire and forget)
                    try:
                        # Create task to send log asynchronously
                        loop = asyncio.get_event_loop()
                        loop.create_task(self.send_log_to_server(message.strip()))
                    except:
                        pass  # Ignore if event loop is not available
            
            async def send_log_to_server(self, content):
                try:
                    if self.client_instance.websocket and self.client_instance.running:
                        await self.client_instance.websocket.send(json.dumps({
                            "type": "log",
                            "script_name": script_name,
                            "execution_id": execution_id,
                            "log_file_path": log_file_path,
                            "log_content": content,
                            "log_level": self.log_level
                        }))
                except:
                    pass  # Ignore errors if websocket is not available
            
            def flush(self):
                pass
        
        stdout_capture = LogCapture(self, "INFO")
        stderr_capture = LogCapture(self, "ERROR")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        try:
            # Redirect stdout and stderr
            import sys
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            script_globals = {
                '__name__': '__main__',
                '__file__': temp_script,
                'SERVER_URL': server_url,
                'PC_ID': self.pc_id,
                'print': lambda *args, **kwargs: stdout_capture.write(' '.join(map(str, args)) + '\n')
            }
            
            # Execute script
            exec(compile(script_content, temp_script, 'exec'), script_globals)
            
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # Send final log entry
            final_log = f"Script '{script_name}' executed successfully"
            await self.send_message({
                "type": "log",
                "script_name": script_name,
                "execution_id": execution_id,
                "log_file_path": log_file_path,
                "log_content": final_log,
                "log_level": "INFO"
            })
            
            await self.send_message({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "success",
                "result": {
                    "message": f"Script '{script_name}' executed successfully",
                    "log_file": log_file_path
                }
            })
            
            logger.info(f"[+] Script '{script_name}' executed successfully")
            logger.info(f"[+] Log saved to: {log_file_path}")
            
        except Exception as e:
            # Restore stdout/stderr
            import sys
            sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
            sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
            
            error_msg = f"Error executing script '{script_name}': {str(e)}"
            logger.error(f"[!] {error_msg}")
            
            # Log error to file
            script_logger.error(error_msg)
            
            # Send error log to server
            await self.send_message({
                "type": "log",
                "script_name": script_name,
                "execution_id": execution_id,
                "log_file_path": log_file_path,
                "log_content": error_msg,
                "log_level": "ERROR"
            })
            
            await self.send_message({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "failed",
                "error_message": error_msg
            })
        
        finally:
            # Clean up
            try:
                log_handler.close()
                script_logger.removeHandler(log_handler)
            except:
                pass
            
            try:
                os.unlink(temp_script)
            except:
                pass
    
    async def handle_message(self, data: dict):
        """Handle incoming messages from server"""
        message_type = data.get("type")
        
        if message_type == "connection":
            logger.info(f"[*] {data.get('message', '')}")
            await self.send_message({
                "type": "status",
                "message": f"PC {self.pc_id} ready"
            })
        
        elif message_type == "script":
            await self.execute_script(
                script_content=data.get("script_content"),
                script_name=data.get("script_name"),
                server_url=data.get("server_url", self.server_url.replace("ws://", "http://").replace("wss://", "https://")),
                execution_id=data.get("execution_id")
            )
        
        elif message_type == "start_stream":
            stream_type = data.get("stream_type")
            if stream_type == "camera":
                await self.start_camera_stream()
            elif stream_type == "microphone":
                await self.start_microphone_stream()
            elif stream_type == "screen":
                await self.start_screen_stream()
        
        elif message_type == "stop_stream":
            await self.stop_stream()
        
        elif message_type == "webrtc_answer":
            answer_sdp = data.get("sdp")
            if answer_sdp:
                await self.handle_webrtc_answer(answer_sdp)
        
        elif message_type == "webrtc_ice_candidate":
            candidate = data.get("candidate")
            if candidate:
                await self.handle_ice_candidate(candidate)
        
        elif message_type == "ping":
            await self.send_message({"type": "pong"})
        
        else:
            logger.debug(f"[*] Received message type: {message_type}")
    
    async def listen(self):
        """Listen for messages from server"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    
                    data = json.loads(message)
                    await self.handle_message(data)
                
                except asyncio.TimeoutError:
                    await self.send_message({
                        "type": "heartbeat",
                        "status": "ok"
                    })
                
                except ConnectionClosed:
                    logger.warning("[!] Connection closed by server")
                    break
                
                except Exception as e:
                    logger.error(f"[!] Error receiving message: {e}")
                    break
        
        except Exception as e:
            logger.error(f"[!] Listen error: {e}")
        finally:
            self.running = False
            await self.stop_stream()
    
    async def run(self):
        """Main client loop"""
        while True:
            if await self.connect():
                await self.listen()
            
            if self.running:
                logger.info("[*] Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            else:
                break


async def main():
    """Main entry point"""
    print("=" * 60)
    print("  Remote Script Server - PC Client (WebRTC)")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"PC ID: {PC_ID}")
    print(f"WebRTC Available: {WEBRTC_AVAILABLE}")
    print("=" * 60)
    
    if not WEBRTC_AVAILABLE:
        print("[!] Warning: WebRTC not available. Install: pip install aiortc")
    
    client = PCClientWebRTC(SERVER_URL, PC_ID)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n[*] Client shutting down...")
        await client.stop_stream()
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

