"""
PC Client with Agora Support
Complete example showing how to connect and stream camera, microphone, and screen using Agora
"""
import asyncio
import json
import os
import sys
import socket
import time
from websockets import connect
from websockets.exceptions import ConnectionClosed
import logging

# Agora imports
try:
    from agora_rtc_sdk import AgoraRtcEngine, AgoraRtcEngineEventHandler, RtcEngineConfig, VideoCanvas, VideoSourceType
    AGORA_AVAILABLE = True
except ImportError:
    AGORA_AVAILABLE = False
    print("[!] Agora SDK not available. Install: pip install agora-python-sdk")
    print("[!] Note: Agora Python SDK may require additional setup. See: https://docs.agora.io/en/video-calling/get-started/get-started-sdk")

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "ws://localhost:8000")
PC_ID = os.getenv("PC_ID", socket.gethostname())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgoraEventHandler(AgoraRtcEngineEventHandler):
    """Event handler for Agora RTC engine"""
    
    def __init__(self, client):
        super().__init__()
        self.client = client
    
    def onJoinChannelSuccess(self, channel, uid, elapsed):
        logger.info(f"[Agora] Successfully joined channel '{channel}' with uid {uid}")
    
    def onLeaveChannel(self, stats):
        logger.info(f"[Agora] Left channel")
    
    def onError(self, err, msg):
        logger.error(f"[Agora] Error {err}: {msg}")
    
    def onUserJoined(self, uid, elapsed):
        logger.info(f"[Agora] User {uid} joined")
    
    def onUserOffline(self, uid, reason):
        logger.info(f"[Agora] User {uid} left (reason: {reason})")


class PCClientAgora:
    """PC Client with Agora streaming support"""
    
    def __init__(self, server_url: str, pc_id: str):
        self.server_url = server_url
        self.pc_id = pc_id
        self.websocket = None
        self.running = False
        self.agora_engine = None
        self.event_handler = None
        self.active_stream_type = None
        self.current_channel = None
        self.current_token = None
        self.current_app_id = None
        self.current_uid = 0
    
    async def connect(self):
        """Connect to server via WebSocket"""
        ws_url = f"{self.server_url}/ws/{self.pc_id}"
        logger.info(f"Connecting to {ws_url}...")
        
        try:
            self.websocket = await connect(ws_url)
            logger.info(f"Connected as {self.pc_id}")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def send_message(self, message: dict):
        """Send message to server"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def send_error(self, error: str):
        """Send error message to server"""
        await self.send_message({"type": "error", "message": error})
    
    async def start_camera_stream(self, agora_config: dict):
        """Start camera stream using Agora"""
        if not AGORA_AVAILABLE:
            await self.send_error("Agora SDK not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Extract Agora configuration
            channel_name = agora_config.get("channel_name")
            token = agora_config.get("token")
            uid = agora_config.get("uid", 0)
            app_id = agora_config.get("app_id")
            
            if not all([channel_name, token, app_id]):
                await self.send_error("Invalid Agora configuration")
                return
            
            logger.info(f"[Agora] Starting camera stream on channel '{channel_name}'")
            
            # Initialize Agora engine
            config = RtcEngineConfig()
            config.app_id = app_id
            config.event_handler = AgoraEventHandler(self)
            
            self.agora_engine = AgoraRtcEngine.create_rtc_engine(config)
            self.agora_engine.initialize(config)
            
            # Enable video
            self.agora_engine.enable_video()
            
            # Enable local video
            self.agora_engine.enable_local_video(True)
            
            # Set video encoder configuration
            self.agora_engine.set_video_encoder_configuration({
                'width': 1280,
                'height': 720,
                'frameRate': 30,
                'bitrate': 2000
            })
            
            # Join channel
            self.agora_engine.join_channel(token, channel_name, uid)
            
            # Start camera capture
            # Note: Platform-specific camera access
            # Windows: Use camera index or device name
            # Linux: Use /dev/video0, /dev/video1, etc.
            # macOS: Use device ID
            
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windows: Try to use default camera (index 0)
                # You may need to adjust based on your camera setup
                camera_id = 0
                logger.info(f"[Agora] Using Windows camera index {camera_id}")
            elif system == "Linux":
                # Linux: Use /dev/video0
                camera_id = "/dev/video0"
                logger.info(f"[Agora] Using Linux camera device {camera_id}")
            elif system == "Darwin":  # macOS
                # macOS: Use default camera
                camera_id = 0
                logger.info(f"[Agora] Using macOS camera index {camera_id}")
            else:
                camera_id = 0
                logger.warning(f"[Agora] Unknown platform {system}, using default camera")
            
            # Start camera preview (optional, for local preview)
            # self.agora_engine.start_preview()
            
            self.active_stream_type = "camera"
            self.current_channel = channel_name
            self.current_token = token
            self.current_app_id = app_id
            self.current_uid = uid
            
            logger.info(f"[Agora] Camera stream started successfully")
            await self.send_message({
                "type": "stream_started",
                "stream_type": "camera"
            })
            
        except Exception as e:
            logger.error(f"[Agora] Error starting camera stream: {e}", exc_info=True)
            await self.send_error(f"Failed to start camera stream: {e}")
    
    async def start_microphone_stream(self, agora_config: dict):
        """Start microphone stream using Agora"""
        if not AGORA_AVAILABLE:
            await self.send_error("Agora SDK not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Extract Agora configuration
            channel_name = agora_config.get("channel_name")
            token = agora_config.get("token")
            uid = agora_config.get("uid", 0)
            app_id = agora_config.get("app_id")
            
            if not all([channel_name, token, app_id]):
                await self.send_error("Invalid Agora configuration")
                return
            
            logger.info(f"[Agora] Starting microphone stream on channel '{channel_name}'")
            
            # Initialize Agora engine
            config = RtcEngineConfig()
            config.app_id = app_id
            config.event_handler = AgoraEventHandler(self)
            
            self.agora_engine = AgoraRtcEngine.create_rtc_engine(config)
            self.agora_engine.initialize(config)
            
            # Enable audio
            self.agora_engine.enable_audio()
            
            # Enable local audio
            self.agora_engine.enable_local_audio(True)
            
            # Set audio profile
            self.agora_engine.set_audio_profile({
                'profile': 1,  # AUDIO_PROFILE_DEFAULT
                'scenario': 0  # AUDIO_SCENARIO_DEFAULT
            })
            
            # Join channel
            self.agora_engine.join_channel(token, channel_name, uid)
            
            self.active_stream_type = "microphone"
            self.current_channel = channel_name
            self.current_token = token
            self.current_app_id = app_id
            self.current_uid = uid
            
            logger.info(f"[Agora] Microphone stream started successfully")
            await self.send_message({
                "type": "stream_started",
                "stream_type": "microphone"
            })
            
        except Exception as e:
            logger.error(f"[Agora] Error starting microphone stream: {e}", exc_info=True)
            await self.send_error(f"Failed to start microphone stream: {e}")
    
    async def start_screen_stream(self, agora_config: dict):
        """Start screen share stream using Agora"""
        if not AGORA_AVAILABLE:
            await self.send_error("Agora SDK not available")
            return
        
        try:
            # Stop any existing stream
            await self.stop_stream()
            
            # Extract Agora configuration
            channel_name = agora_config.get("channel_name")
            token = agora_config.get("token")
            uid = agora_config.get("uid", 0)
            app_id = agora_config.get("app_id")
            
            if not all([channel_name, token, app_id]):
                await self.send_error("Invalid Agora configuration")
                return
            
            logger.info(f"[Agora] Starting screen stream on channel '{channel_name}'")
            
            # Initialize Agora engine
            config = RtcEngineConfig()
            config.app_id = app_id
            config.event_handler = AgoraEventHandler(self)
            
            self.agora_engine = AgoraRtcEngine.create_rtc_engine(config)
            self.agora_engine.initialize(config)
            
            # Enable video
            self.agora_engine.enable_video()
            
            # Enable screen sharing
            # Note: Screen sharing implementation varies by platform
            # This is a simplified example - you may need platform-specific code
            
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windows screen sharing
                logger.info("[Agora] Setting up Windows screen sharing")
                # Use screen capture API (implementation depends on Agora SDK version)
            elif system == "Linux":
                # Linux screen sharing (X11)
                logger.info("[Agora] Setting up Linux screen sharing")
            elif system == "Darwin":  # macOS
                # macOS screen sharing
                logger.info("[Agora] Setting up macOS screen sharing")
            
            # Set video encoder configuration for screen sharing
            self.agora_engine.set_video_encoder_configuration({
                'width': 1920,
                'height': 1080,
                'frameRate': 30,
                'bitrate': 3000
            })
            
            # Join channel
            self.agora_engine.join_channel(token, channel_name, uid)
            
            self.active_stream_type = "screen"
            self.current_channel = channel_name
            self.current_token = token
            self.current_app_id = app_id
            self.current_uid = uid
            
            logger.info(f"[Agora] Screen stream started successfully")
            await self.send_message({
                "type": "stream_started",
                "stream_type": "screen"
            })
            
        except Exception as e:
            logger.error(f"[Agora] Error starting screen stream: {e}", exc_info=True)
            await self.send_error(f"Failed to start screen stream: {e}")
    
    async def stop_stream(self):
        """Stop any active stream"""
        if self.agora_engine:
            try:
                if self.current_channel:
                    self.agora_engine.leave_channel()
                    logger.info(f"[Agora] Left channel '{self.current_channel}'")
                
                self.agora_engine.release()
                self.agora_engine = None
                
                self.active_stream_type = None
                self.current_channel = None
                self.current_token = None
                self.current_app_id = None
                self.current_uid = 0
                
                logger.info("[Agora] Stream stopped")
            except Exception as e:
                logger.error(f"[Agora] Error stopping stream: {e}")
    
    async def handle_message(self, message: dict):
        """Handle incoming WebSocket message"""
        message_type = message.get("type")
        
        if message_type == "start_stream":
            stream_type = message.get("stream_type")
            agora_config = message.get("agora")
            
            if not agora_config:
                await self.send_error(f"No Agora configuration provided for {stream_type} stream")
                return
            
            if stream_type == "camera":
                await self.start_camera_stream(agora_config)
            elif stream_type == "microphone":
                await self.start_microphone_stream(agora_config)
            elif stream_type == "screen":
                await self.start_screen_stream(agora_config)
            else:
                await self.send_error(f"Unknown stream type: {stream_type}")
        
        elif message_type == "stop_stream":
            await self.stop_stream()
            await self.send_message({
                "type": "stream_stopped"
            })
    
    async def run(self):
        """Main event loop"""
        if not await self.connect():
            return
        
        try:
            # Send PC info
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
            
            await self.send_message({
                "type": "pc_info",
                "pc_id": self.pc_id,
                "hostname": hostname,
                "ip_address": ip_address,
                "agora_available": AGORA_AVAILABLE
            })
            
            # Listen for messages
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message: {message}")
                except Exception as e:
                    logger.error(f"Error handling message: {e}", exc_info=True)
        
        except ConnectionClosed:
            logger.info("Connection closed")
        except Exception as e:
            logger.error(f"Error in event loop: {e}", exc_info=True)
        finally:
            await self.stop_stream()
            if self.websocket:
                await self.websocket.close()


async def main():
    """Main entry point"""
    print("=" * 60)
    print("  Remote Script Server - PC Client (Agora)")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"PC ID: {PC_ID}")
    print(f"Hostname: {socket.gethostname()}")
    print(f"Agora Support: {'Available' if AGORA_AVAILABLE else 'Not Available'}")
    print("=" * 60)
    
    client = PCClientAgora(SERVER_URL, PC_ID)
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

