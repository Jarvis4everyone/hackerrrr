# PC Client Streaming Implementation Guide

This guide explains how to implement camera, microphone, and screen sharing functionality in the PC client using WebSocket.

## Overview

The streaming system uses WebSocket to send frames/audio chunks from the PC to the server, which then forwards them to the frontend. This approach works in both localhost and production environments without requiring STUN/TURN servers.

## Architecture

1. **PC Client** captures video/audio/screen frames
2. **PC Client** encodes frames to JPEG (for video/screen) or raw audio bytes
3. **PC Client** sends frames via WebSocket as base64-encoded strings
   - **Camera/Screen**: Continuous frame streaming (~30 FPS)
   - **Microphone**: 5-second audio chunks
4. **Server** receives frames/chunks and forwards to all connected frontend clients
5. **Frontend** displays video/audio using HTML5 elements
   - **Camera/Screen**: Real-time video display
   - **Microphone**: Chunk list with play/download options

## Message Types

### From Server to PC Client

#### Start Stream
```json
{
  "type": "start_stream",
  "stream_type": "camera" | "microphone" | "screen"
}
```

#### Stop Stream
```json
{
  "type": "stop_stream",
  "stream_type": "camera" | "microphone" | "screen"
}
```

### From PC Client to Server

#### Camera Frame
```json
{
  "type": "camera_frame",
  "frame": "<base64_encoded_jpeg>"
}
```

#### Microphone Audio (5-second chunks)
```json
{
  "type": "microphone_audio",
  "audio": "<base64_encoded_audio_bytes>",
  "chunk_number": 1,
  "duration": 5.0,
  "sample_rate": 44100,
  "channels": 1,
  "format": "pcm"
}
```

#### Screen Frame
```json
{
  "type": "screen_frame",
  "frame": "<base64_encoded_jpeg>"
}
```

#### Stream Status
```json
{
  "type": "stream_status",
  "stream_type": "camera" | "microphone" | "screen",
  "status": "started" | "stopped" | "error",
  "error": "<error_message>" // optional, only if status is "error"
}
```

## Implementation

### 1. Camera Streaming

#### Required Libraries
```bash
pip install opencv-python pillow
```

#### Python Implementation
```python
import cv2
import base64
import asyncio
import websockets
import json

class CameraStreamer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.camera = None
        self.is_streaming = False
        self.frame_interval = 0.016  # ~60 FPS (16ms per frame) - faster for lower latency
    
    async def start(self):
        """Start camera streaming"""
        try:
            # Open camera (0 is default camera, adjust if needed)
            self.camera = cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                await self.send_status("error", "Failed to open camera")
                return
            
            # Set camera properties for optimized performance and lower latency
            # Much lower resolution = much smaller file size = much faster transmission
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            self.camera.set(cv2.CAP_PROP_FPS, 20)  # Lower FPS to reduce network load
            # Reduce buffer size to minimize latency
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            self.is_streaming = True
            await self.send_status("started")
            
            # Start streaming loop
            await self.stream_loop()
            
        except Exception as e:
            await self.send_status("error", str(e))
    
    async def stop(self):
        """Stop camera streaming"""
        self.is_streaming = False
        if self.camera:
            self.camera.release()
            self.camera = None
        await self.send_status("stopped")
    
    async def stream_loop(self):
        """Main streaming loop - optimized for low latency"""
        while self.is_streaming:
            try:
                # Check if WebSocket is still open before sending
                if self.websocket.closed:
                    print("[Camera] WebSocket closed, stopping stream")
                    self.is_streaming = False
                    break
                
                ret, frame = self.camera.read()
                if not ret:
                    break
                
                # Resize frame for faster encoding and transmission
                # Much smaller frames = much less data = much lower latency
                frame = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_LINEAR)
                
                # Encode frame to JPEG with aggressive optimization
                # Very low quality (40) = very small file = very fast transmission
                # Use optimized encoding parameters
                encode_params = [
                    cv2.IMWRITE_JPEG_QUALITY, 40,  # Very low quality for speed
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1  # Optimize JPEG
                ]
                _, buffer = cv2.imencode('.jpg', frame, encode_params)
                
                # Skip frame if it's too large (over 30KB) to prevent network congestion
                if len(buffer) > 30000:
                    continue
                
                # Convert to base64
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame to server (with error handling)
                try:
                    await self.websocket.send(json.dumps({
                        "type": "camera_frame",
                        "frame": frame_b64
                    }))
                except Exception as send_error:
                    print(f"[Camera] Error sending frame: {send_error}")
                    # If connection is closed, stop streaming
                    if "closed" in str(send_error).lower() or "connection" in str(send_error).lower():
                        self.is_streaming = False
                        break
                
                # Limit frame rate to prevent network congestion
                # 15 FPS = ~66ms per frame - good balance between smoothness and latency
                await asyncio.sleep(0.066)  # ~15 FPS to prevent overwhelming network
                
            except Exception as e:
                print(f"[Camera] Error: {e}")
                self.is_streaming = False
                break
    
    async def send_status(self, status, error=None):
        """Send streaming status to server"""
        message = {
            "type": "stream_status",
            "stream_type": "camera",
            "status": status
        }
        if error:
            message["error"] = error
        await self.websocket.send(json.dumps(message))
```

### 2. Microphone Streaming

#### Required Libraries
```bash
pip install pyaudio
```

#### Python Implementation
```python
import pyaudio
import base64
import asyncio
import websockets
import json

class MicrophoneStreamer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.audio = None
        self.stream = None
        self.is_streaming = False
        
        # Audio settings
        self.CHUNK = 1024  # Audio chunk size
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1  # Mono
        self.RATE = 44100  # Sample rate
    
    async def start(self):
        """Start microphone streaming"""
        try:
            self.audio = pyaudio.PyAudio()
            
            # Open audio stream
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            self.is_streaming = True
            await self.send_status("started")
            
            # Start streaming loop
            await self.stream_loop()
            
        except Exception as e:
            await self.send_status("error", str(e))
    
    async def stop(self):
        """Stop microphone streaming"""
        self.is_streaming = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.audio:
            self.audio.terminate()
            self.audio = None
        await self.send_status("stopped")
    
    async def stream_loop(self):
        """Main streaming loop - sends 5-second audio chunks"""
        import time
        
        chunk_duration = 5.0  # 5 seconds per chunk
        chunk_number = 0
        
        while self.is_streaming:
            try:
                # Check if WebSocket is still open before sending
                if self.websocket.closed:
                    print("[Microphone] WebSocket closed, stopping stream")
                    self.is_streaming = False
                    break
                
                chunk_number += 1
                chunk_start_time = time.time()
                chunk_audio_data = []
                
                # Collect audio data for 5 seconds
                while (time.time() - chunk_start_time) < chunk_duration and self.is_streaming:
                    if self.websocket.closed:
                        self.is_streaming = False
                        break
                    
                    try:
                        # Read audio data
                        audio_data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                        chunk_audio_data.append(audio_data)
                    except Exception as e:
                        print(f"[Microphone] Error reading audio: {e}")
                        break
                
                if not self.is_streaming or self.websocket.closed:
                    break
                
                # Combine all audio chunks into one
                combined_audio = b''.join(chunk_audio_data)
                
                if len(combined_audio) == 0:
                    continue
                
                # Encode to base64
                audio_b64 = base64.b64encode(combined_audio).decode('utf-8')
                
                # Send to server (with error handling)
                try:
                    await self.websocket.send(json.dumps({
                        "type": "microphone_audio",
                        "audio": audio_b64,
                        "chunk_number": chunk_number,
                        "duration": chunk_duration,
                        "sample_rate": self.RATE,
                        "channels": self.CHANNELS,
                        "format": "pcm"
                    }))
                    print(f"[Microphone] Sent chunk {chunk_number} ({len(combined_audio)} bytes)")
                except Exception as send_error:
                    print(f"[Microphone] Error sending audio chunk {chunk_number}: {send_error}")
                    # If connection is closed, stop streaming
                    if "closed" in str(send_error).lower() or "connection" in str(send_error).lower():
                        self.is_streaming = False
                        break
                
            except Exception as e:
                print(f"[Microphone] Error: {e}")
                self.is_streaming = False
                break
    
    async def send_status(self, status, error=None):
        """Send streaming status to server"""
        message = {
            "type": "stream_status",
            "stream_type": "microphone",
            "status": status
        }
        if error:
            message["error"] = error
        await self.websocket.send(json.dumps(message))
```

### 3. Screen Sharing

#### Required Libraries
```bash
pip install mss pillow
```

#### Python Implementation
```python
import mss
import numpy as np
import cv2
import base64
import asyncio
import websockets
import json

class ScreenStreamer:
    def __init__(self, websocket):
        self.websocket = websocket
        self.sct = None
        self.is_streaming = False
        self.frame_interval = 0.016  # ~60 FPS (16ms per frame) - faster for lower latency
    
    async def start(self):
        """Start screen sharing"""
        try:
            self.sct = mss.mss()
            self.is_streaming = True
            await self.send_status("started")
            
            # Start streaming loop
            await self.stream_loop()
            
        except Exception as e:
            await self.send_status("error", str(e))
    
    async def stop(self):
        """Stop screen sharing"""
        self.is_streaming = False
        if self.sct:
            self.sct.close()
            self.sct = None
        await self.send_status("stopped")
    
    async def stream_loop(self):
        """Main streaming loop"""
        # Get primary monitor
        monitor = self.sct.monitors[1]  # 0 is all monitors, 1 is primary
        
        while self.is_streaming:
            try:
                # Check if WebSocket is still open before sending
                if self.websocket.closed:
                    print("[Screen] WebSocket closed, stopping stream")
                    self.is_streaming = False
                    break
                
                # Capture screen
                screenshot = self.sct.grab(monitor)
                
                # Convert to numpy array
                img = np.array(screenshot)
                
                # Convert BGRA to RGB
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                
                # Resize for faster encoding and transmission
                # Much lower resolution = much smaller file = much lower latency
                # Use 960x540 for good quality/speed balance (half of 1920x1080)
                img = cv2.resize(img, (960, 540), interpolation=cv2.INTER_LINEAR)
                
                # Encode to JPEG with aggressive optimization
                # Very low quality (40) = very small file = very fast transmission
                # Use optimized encoding parameters
                encode_params = [
                    cv2.IMWRITE_JPEG_QUALITY, 40,  # Very low quality for speed
                    cv2.IMWRITE_JPEG_OPTIMIZE, 1  # Optimize JPEG
                ]
                _, buffer = cv2.imencode('.jpg', img, encode_params)
                
                # Skip frame if it's too large (over 50KB) to prevent network congestion
                if len(buffer) > 50000:
                    continue
                
                # Convert to base64
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send to server (with error handling)
                try:
                    await self.websocket.send(json.dumps({
                        "type": "screen_frame",
                        "frame": frame_b64
                    }))
                except Exception as send_error:
                    print(f"[Screen] Error sending frame: {send_error}")
                    # If connection is closed, stop streaming
                    if "closed" in str(send_error).lower() or "connection" in str(send_error).lower():
                        self.is_streaming = False
                        break
                
                # Limit frame rate to prevent network congestion
                # 15 FPS = ~66ms per frame - good balance between smoothness and latency
                await asyncio.sleep(0.066)  # ~15 FPS to prevent overwhelming network
                
            except Exception as e:
                print(f"[Screen] Error: {e}")
                self.is_streaming = False
                break
    
    async def send_status(self, status, error=None):
        """Send streaming status to server"""
        message = {
            "type": "stream_status",
            "stream_type": "screen",
            "status": status
        }
        if error:
            message["error"] = error
        await self.websocket.send(json.dumps(message))
```

### 4. Integration with Main WebSocket Handler

```python
import asyncio
import websockets
import json

# Initialize streamers
camera_streamer = None
microphone_streamer = None
screen_streamer = None

async def handle_websocket(websocket, path):
    """Main WebSocket handler"""
    global camera_streamer, microphone_streamer, screen_streamer
    
    async for message in websocket:
        data = json.loads(message)
        message_type = data.get("type")
        
        if message_type == "start_stream":
            stream_type = data.get("stream_type")
            
            if stream_type == "camera":
                if not camera_streamer:
                    camera_streamer = CameraStreamer(websocket)
                await camera_streamer.start()
            
            elif stream_type == "microphone":
                if not microphone_streamer:
                    microphone_streamer = MicrophoneStreamer(websocket)
                await microphone_streamer.start()
            
            elif stream_type == "screen":
                if not screen_streamer:
                    screen_streamer = ScreenStreamer(websocket)
                await screen_streamer.start()
        
        elif message_type == "stop_stream":
            stream_type = data.get("stream_type")
            
            if stream_type == "camera" and camera_streamer:
                await camera_streamer.stop()
                camera_streamer = None
            
            elif stream_type == "microphone" and microphone_streamer:
                await microphone_streamer.stop()
                microphone_streamer = None
            
            elif stream_type == "screen" and screen_streamer:
                await screen_streamer.stop()
                screen_streamer = None

# Connect to server
async def connect_to_server():
    server_url = "wss://your-server.com/ws/YourPCID"
    async with websockets.connect(server_url) as websocket:
        await handle_websocket(websocket, None)

# Run
asyncio.run(connect_to_server())
```

## Performance Optimization

### Frame Rate Control
- **Camera**: 30 FPS (0.033s interval)
- **Screen**: 30 FPS (0.033s interval)
- **Microphone**: Continuous (no sleep needed)

### Image Quality
- **JPEG Quality**: 75-85 (balance between quality and size)
- **Resolution**: 
  - Camera: 640x480 or 1280x720
  - Screen: Native or 1280x720

### Compression
- Use JPEG compression for video/screen frames
- Send raw PCM audio for microphone (server can handle it)

## Error Handling

Always send `stream_status` messages:
- When stream starts successfully: `{"status": "started"}`
- When stream stops: `{"status": "stopped"}`
- When error occurs: `{"status": "error", "error": "error message"}`

## Testing

1. **Test Camera**: Ensure camera permissions are granted
2. **Test Microphone**: Ensure microphone permissions are granted
3. **Test Screen**: Should work without permissions on most systems

## Troubleshooting

### Camera not working
- Check camera permissions
- Try different camera index (0, 1, 2, etc.)
- Verify camera is not in use by another application

### Microphone not working
- Check microphone permissions
- Verify audio input device is available
- Check PyAudio installation

### Screen not working
- Verify mss library is installed
- Check if running on Windows/Linux/Mac (mss supports all)

### High CPU Usage
- Reduce frame rate (increase `frame_interval`)
- Reduce resolution
- Lower JPEG quality

## Notes

- All frames/audio are sent as base64-encoded strings in JSON messages
- Server forwards messages to all connected frontend clients
- No STUN/TURN servers needed - works through WebSocket
- Works in both localhost and production environments
- Frame rate can be adjusted based on network conditions

