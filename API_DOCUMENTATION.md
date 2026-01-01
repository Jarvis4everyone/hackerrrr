# PC-Side Developer API Documentation

Complete guide for developing PC clients that connect to the Remote Script Server.

## Table of Contents

1. [Overview](#overview)
2. [Connection Setup](#connection-setup)
3. [WebSocket Communication](#websocket-communication)
4. [Message Types](#message-types)
5. [WebRTC Streaming](#webrtc-streaming)
6. [REST API Endpoints](#rest-api-endpoints)
7. [Complete Client Example](#complete-client-example)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## Overview

The Remote Script Server uses **WebSocket** for real-time bidirectional communication between the server and multiple PCs. Each PC connects with a unique `pc_id` and can receive scripts to execute remotely.

### Key Features:
- **Real-time Communication**: WebSocket for instant script delivery
- **Multiple PC Support**: Server handles unlimited concurrent connections
- **Script Execution Tracking**: All executions are logged in MongoDB
- **Status Reporting**: PCs can send execution status and results back to server
- **WebRTC Streaming**: Built-in support for camera, microphone, and screen streaming
  - Camera streaming for video feed
  - Microphone streaming with 5-second audio chunks
  - Screen sharing for remote desktop viewing
  - Only one stream active at a time per PC

---

## Connection Setup

### WebSocket Endpoint

```
ws://{server_host}:{port}/ws/{pc_id}
```

**Example:**
```
ws://localhost:8000/ws/PC-001
ws://192.168.1.100:8000/ws/DESKTOP-ABC123
```

### Connection Requirements

1. **PC ID**: Each PC must have a unique identifier
   - Recommended: Use hostname, MAC address, or custom ID
   - Format: Alphanumeric string (letters, numbers, hyphens, underscores)
   - Example: `PC-001`, `DESKTOP-ABC123`, `LAPTOP-USER-01`

2. **WebSocket Library**: Use a WebSocket client library
   - Python: `websockets` or `websocket-client`
   - JavaScript: Native `WebSocket` or `ws` library
   - Other languages: Any WebSocket client library

---

## WebSocket Communication

### Connection Flow

1. **Connect** to WebSocket endpoint
2. **Receive** welcome message from server
3. **Listen** for script messages
4. **Execute** received scripts
5. **Send** status updates back to server
6. **Handle** disconnections and reconnect

### Initial Connection

When you connect, the server will send a welcome message:

```json
{
    "type": "connection",
    "status": "connected",
    "message": "Connected to server as PC-001",
    "server_url": "http://localhost:8000"
}
```

**Important:** The server automatically records your IP address from the WebSocket connection. However, you should send your hostname and other PC information to the server after connecting.

### Sending PC Information

After receiving the connection message, send your PC information to the server:

```json
{
    "type": "pc_info",
    "ip_address": "192.168.1.100",
    "hostname": "DESKTOP-ABC123",
    "name": "My PC",
    "os_info": {
        "platform": "Windows",
        "version": "10.0.19045",
        "architecture": "x64"
    },
    "metadata": {
        "custom_field": "value"
    }
}
```

**Fields:**
- `type`: Must be `"pc_info"`
- `ip_address` (optional but recommended): Your PC's real IP address. **IMPORTANT**: If not provided, the server will use the IP from the WebSocket connection, which may be `127.0.0.1` for localhost connections or incorrect for NAT scenarios.
- `hostname` (optional): Your PC's hostname (recommended)
- `name` (optional): Display name for your PC
- `os_info` (optional): Operating system information
- `metadata` (optional): Any additional metadata

**Why send this?**
- **IP Address**: **CRITICAL** - Send your real IP address. The server will use the WebSocket connection IP as fallback, but this may be incorrect (e.g., `127.0.0.1` for localhost, or router IP for NAT).
- **Hostname**: Helps identify your PC in the logs and dashboard
- **OS Info**: Useful for debugging and compatibility checks

**Example Implementation:**

```python
import socket
import platform

# After receiving connection message
hostname = socket.gethostname()

# Get real IP address (not 127.0.0.1)
def get_local_ip():
    try:
        # Connect to a remote address to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

ip_address = get_local_ip()
os_info = {
    "platform": platform.system(),
    "version": platform.version(),
    "architecture": platform.machine()
}

await websocket.send_json({
    "type": "pc_info",
    "ip_address": ip_address,  # IMPORTANT: Send real IP
    "hostname": hostname,
    "name": hostname,  # or custom name
    "os_info": os_info
})
```

```javascript
const os = require('os');
const { networkInterfaces } = require('os');

// After receiving connection message
const hostname = os.hostname();

// Get real IP address (not 127.0.0.1)
function getLocalIP() {
    const nets = networkInterfaces();
    for (const name of Object.keys(nets)) {
        for (const net of nets[name]) {
            if (net.family === 'IPv4' && !net.internal) {
                return net.address;
            }
        }
    }
    return null;
}

const ipAddress = getLocalIP();
const osInfo = {
    platform: os.platform(),
    version: os.release(),
    architecture: os.arch()
};

ws.send(JSON.stringify({
    type: "pc_info",
    ip_address: ipAddress,  // IMPORTANT: Send real IP
    hostname: hostname,
    name: hostname,  // or custom name
    os_info: osInfo
}));
```

### Heartbeat/Ping

The server sends periodic ping messages to keep the connection alive:

```json
{
    "type": "ping"
}
```

**Response:**
```json
{
    "type": "pong"
}
```

---

## Message Types

### Messages FROM Server TO PC

#### 1. Connection Message
Sent immediately after connection.

```json
{
    "type": "connection",
    "status": "connected",
    "message": "Connected to server as {pc_id}",
    "server_url": "http://localhost:8000"
}
```

#### 2. Script Message
Sent when server wants to execute a script on the PC.

```json
{
    "type": "script",
    "script_name": "disable_input.py",
    "script_content": "# Python script code here...",
    "server_url": "http://localhost:8000",
    "execution_id": "507f1f77bcf86cd799439011",
    "script_params": {
        "DISABLE_DURATION": "30"
    }
}
```

**Fields:**
- `type`: Always `"script"`
- `script_name`: Name of the script file
- `script_content`: Full Python script code to execute
- `server_url`: Server URL (for scripts that need to upload data)
- `execution_id`: Unique execution ID (use this when reporting status)
- `script_params` (optional): Dictionary of script parameters. **IMPORTANT**: PC client must set these as environment variables before executing the script

**PC Client Implementation:**
When receiving a script message, the PC client **MUST** set environment variables before executing the script:

```python
# When handling script message
if message_type == "script":
    script_content = data.get("script_content")
    script_name = data.get("script_name")
    server_url = data.get("server_url")  # Get server_url from message
    execution_id = data.get("execution_id")
    script_params = data.get("script_params", {})  # Get parameters
    
    import os
    
    # CRITICAL STEP 1: Set SERVER_URL from server_url field (REQUIRED)
    if server_url:
        os.environ["SERVER_URL"] = server_url
    else:
        # Fallback if server_url not provided
        os.environ["SERVER_URL"] = self.server_url.replace("ws://", "http://")
    
    # CRITICAL STEP 2: Set PC_ID (REQUIRED)
    os.environ["PC_ID"] = self.pc_id
    
    # CRITICAL STEP 3: Set script parameters as environment variables
    for param_name, param_value in script_params.items():
        os.environ[param_name] = str(param_value)  # Convert to string
        print(f"[*] Parameter {param_name} = {param_value}")
    
    # Verify SERVER_URL is set (for debugging)
    print(f"[*] SERVER_URL = {os.environ.get('SERVER_URL', 'NOT SET!')}")
    print(f"[*] PC_ID = {os.environ.get('PC_ID', 'NOT SET!')}")
    
    # Now execute the script
    exec(compile(script_content, script_name, 'exec'), script_globals)
```

**⚠️ IMPORTANT NOTES:**
1. **SERVER_URL MUST be set**: The `server_url` field from the script message MUST be set as `os.environ["SERVER_URL"]` before script execution. Scripts rely on this variable.
2. **PC_ID MUST be set**: Always set `os.environ["PC_ID"]` to your PC identifier.
3. **script_params MUST be set**: All parameters from `script_params` must be set as environment variables.
4. **Order matters**: Set `SERVER_URL` and `PC_ID` first, then `script_params`, then execute the script.

**Example with parameters:**
```json
{
    "type": "script",
    "script_name": "disable_input.py",
    "script_content": "# script code...",
    "server_url": "http://localhost:8000",
    "execution_id": "6956a010b36fdfe6e487b7d5",
    "script_params": {
        "DISABLE_DURATION": "5"
    }
}
```

In this case, the PC client must:
1. Set `os.environ["SERVER_URL"] = "http://localhost:8000"` (from `server_url` field)
2. Set `os.environ["PC_ID"] = self.pc_id`
3. Set `os.environ["DISABLE_DURATION"] = "5"` (from `script_params`)

**All three steps are REQUIRED before executing the script.**

#### 3. Download File Message
Server requests PC to download a file.

```json
{
    "type": "download_file",
    "file_path": "C:\\Users\\Username\\Documents\\file.txt",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "max_size": 104857600
}
```

**Fields:**
- `type`: Always `"download_file"`
- `file_path`: Full path to the file on the PC
- `request_id`: Unique request ID for tracking
- `max_size`: Maximum file size in bytes (100 MB = 104857600 bytes)

**PC Client Implementation:**
When receiving a download_file message, the PC client must:
1. Check if the file exists
2. Check if the file size is within the limit
3. Read the file content
4. Encode it as base64
5. Send it back in a `file_download_response` message

**Example Implementation:**

```python
if message_type == "download_file":
    file_path = data.get("file_path")
    request_id = data.get("request_id")
    max_size = data.get("max_size", 100 * 1024 * 1024)  # Default 100 MB
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            await websocket.send_json({
                "type": "file_download_response",
                "request_id": request_id,
                "success": False,
                "error_message": f"File not found: {file_path}"
            })
            return
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            await websocket.send_json({
                "type": "file_download_response",
                "request_id": request_id,
                "success": False,
                "error_message": f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)"
            })
            return
        
        # Read and encode file
        import base64
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        file_content_b64 = base64.b64encode(file_content).decode('utf-8')
        
        # Send file to server
        await websocket.send_json({
            "type": "file_download_response",
            "request_id": request_id,
            "file_path": file_path,
            "success": True,
            "file_content": file_content_b64
        })
        
    except PermissionError:
        await websocket.send_json({
            "type": "file_download_response",
            "request_id": request_id,
            "success": False,
            "error_message": f"Permission denied: {file_path}"
        })
    except Exception as e:
        await websocket.send_json({
            "type": "file_download_response",
            "request_id": request_id,
            "success": False,
            "error_message": f"Error reading file: {str(e)}"
        })
```

**Important Notes:**
- Files larger than 100 MB will be rejected
- The file must be readable by the PC client process
- File content is sent as base64-encoded string
- The PC should handle errors gracefully and send error messages back

#### 4. Ping Message
Periodic heartbeat from server.

```json
{
    "type": "ping"
}
```

**Response Required:**
```json
{
    "type": "pong"
}
```

### Messages FROM PC TO Server

#### 1. Heartbeat
Send periodic heartbeat to keep connection alive.

```json
{
    "type": "heartbeat",
    "status": "ok"
}
```

#### 2. PC Info
Send PC information (IP address, hostname, OS info, etc.) after connecting.

```json
{
    "type": "pc_info",
    "ip_address": "192.168.1.100",
    "hostname": "DESKTOP-ABC123",
    "name": "My PC",
    "os_info": {
        "platform": "Windows",
        "version": "10.0.19045",
        "architecture": "x64"
    },
    "metadata": {}
}
```

**Note:** 
- **IP Address**: **CRITICAL** - Always send your real IP address. The server will use the WebSocket connection IP as fallback, but this may be incorrect (e.g., `127.0.0.1` for localhost connections).
- If you don't send `ip_address`, the server will use the IP from the WebSocket connection, which may be wrong.

#### 3. Status Update
Send general status messages.

```json
{
    "type": "status",
    "message": "Script execution started"
}
```

#### 4. Execution Complete
**IMPORTANT**: Send this after script execution completes.

```json
{
    "type": "execution_complete",
    "execution_id": "507f1f77bcf86cd799439011",
    "status": "success",
    "result": {
        "message": "Script executed successfully",
        "data": {
            "output": "Any additional data"
        }
    }
}
```

**For Failed Executions:**
```json
{
    "type": "execution_complete",
    "execution_id": "507f1f77bcf86cd799439011",
    "status": "failed",
    "error_message": "Error description here",
    "result": null
}
```

**Fields:**
- `execution_id`: Must match the `execution_id` from the script message
- `status`: `"success"` or `"failed"`
- `error_message`: Required if status is `"failed"`
- `result`: Optional data object with execution results

#### 5. Error Message
Send error notifications.

```json
{
    "type": "error",
    "execution_id": "507f1f77bcf86cd799439011",
    "message": "Error occurred during execution"
}
```

#### 6. File Download Response
Send file content back to server after download request.

```json
{
    "type": "file_download_response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_path": "C:\\Users\\Username\\Documents\\file.txt",
    "success": true,
    "file_content": "base64_encoded_file_content_here..."
}
```

**For Failed Downloads:**
```json
{
    "type": "file_download_response",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_path": "C:\\Users\\Username\\Documents\\file.txt",
    "success": false,
    "error_message": "File not found"
}
```

**Fields:**
- `type`: Must be `"file_download_response"`
- `request_id`: Must match the `request_id` from the download_file message
- `file_path`: Path to the file that was requested
- `success`: `true` if file was read successfully, `false` otherwise
- `file_content`: Base64-encoded file content (required if `success` is `true`)
- `error_message`: Error description (required if `success` is `false`)

**Important:**
- File content must be base64-encoded
- Maximum file size is 100 MB
- Always include the `request_id` to match the request
- Send error messages for any failures (file not found, permission denied, etc.)

#### 7. Terminal Ready Message
PC confirms terminal session is ready.

```json
{
    "type": "terminal_ready",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 8. Terminal Output Message
PC sends terminal output.

```json
{
    "type": "terminal_output",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "output": "PS C:\\Users\\Username> ls\r\nfile1.txt\r\nfile2.txt\r\nPS C:\\Users\\Username> ",
    "is_complete": true
}
```

**Fields:**
- `type`: Must be `"terminal_output"`
- `session_id`: Session ID
- `output`: Terminal output text (can include ANSI escape codes)
- `is_complete`: `true` if command completed, `false` if still running (for interactive commands)

**Important:**
- For commands like `ls`, `dir`, `echo`, set `is_complete: true` after output
- For interactive commands like `python`, `node`, set `is_complete: false` and keep streaming
- Include newlines (`\r\n` on Windows) in output
- Send output in real-time as it becomes available

#### 9. Terminal Error Message
PC reports terminal error.

```json
{
    "type": "terminal_error",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "error": "Failed to start PowerShell process"
}
```

#### 10. Terminal Ready
Send when terminal session is ready.

```json
{
    "type": "terminal_ready",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 11. Terminal Output
Send terminal output from PowerShell.

```json
{
    "type": "terminal_output",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "output": "PS C:\\Users\\Username> ls\r\nfile1.txt\r\nfile2.txt\r\nPS C:\\Users\\Username> ",
    "is_complete": true
}
```

**Fields:**
- `type`: Must be `"terminal_output"`
- `session_id`: Session ID
- `output`: Terminal output text (can include ANSI escape codes)
- `is_complete`: `true` if command completed, `false` if still running (for interactive commands)

**Important:**
- For commands like `ls`, `dir`, `echo`, set `is_complete: true` after output
- For interactive commands like `python`, `node`, set `is_complete: false` and keep streaming
- Include newlines (`\r\n` on Windows) in output
- Send output in real-time as it becomes available

#### 12. Terminal Error
Send when terminal error occurs.

```json
{
    "type": "terminal_error",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "error": "Failed to start PowerShell process"
}
```

#### 13. Result Message
Send execution results (alternative to execution_complete).

```json
{
    "type": "result",
    "execution_id": "507f1f77bcf86cd799439011",
    "message": "Execution completed",
    "data": {
        "output": "Additional data"
    }
}
```

#### 6. Pong Response
Response to server ping.

```json
{
    "type": "pong"
}
```

#### 7. WebRTC Offer
Send WebRTC offer to server (PC initiates connection).

```json
{
    "type": "webrtc_offer",
    "sdp": "v=0\r\no=- 1234567890 1234567890 IN IP4 0.0.0.0\r\n..."
}
```

#### 8. WebRTC Answer
Send WebRTC answer to server (for server-initiated connections).

```json
{
    "type": "webrtc_answer",
    "sdp": "v=0\r\no=- 1234567890 1234567890 IN IP4 0.0.0.0\r\n..."
}
```

#### 9. WebRTC ICE Candidate
Send ICE candidate for WebRTC connection.

```json
{
    "type": "webrtc_ice_candidate",
    "candidate": {
        "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host",
        "sdpMLineIndex": 0,
        "sdpMid": "0"
    }
}
```

#### 10. WebRTC Stream Ready
Notify server that stream is ready.

```json
{
    "type": "webrtc_stream_ready",
    "stream_type": "camera"
}
```

---

## WebRTC Streaming

The server supports **WebRTC** for real-time streaming of camera, microphone, and screen. These are built-in features available for every connected PC.

### Overview

- **Camera Streaming**: View PC's camera feed in real-time
- **Microphone Streaming**: Listen to PC's microphone (5-second audio chunks)
- **Screen Sharing**: View PC's screen in real-time
- **Single Stream**: Only one stream can be active at a time per PC
- **On-Demand**: Streams are started/stopped via API calls

### Stream Types

1. **Camera** (`camera`): Video feed from PC's camera
2. **Microphone** (`microphone`): Audio feed from PC's microphone (5-second chunks)
3. **Screen** (`screen`): Screen share from PC's display

### WebRTC Connection Flow

1. **Server initiates stream** via API endpoint
2. **Server sends `start_stream` message** to PC via WebSocket
3. **PC creates WebRTC offer** with TURN/STUN servers and sends it to server
4. **Server creates answer** and sends it back to PC
5. **PC and server exchange ICE candidates**
6. **Connection established**, media starts flowing

### TURN Server Support (NAT Traversal)

For cloud deployments or when PCs are behind NAT/firewalls, **TURN servers are essential** for WebRTC to work properly. The system includes built-in support for Metered.ca's free TURN servers.

**Automatic TURN Configuration:**
- PC client (`pc_client_webrtc.py`) automatically fetches TURN credentials from Metered.ca
- Frontend automatically fetches TURN credentials from Metered.ca
- Backend automatically fetches TURN credentials from Metered.ca
- Credentials are cached for 1 hour to reduce API calls
- Falls back to STUN-only if TURN fetch fails

**How It Works:**
1. On first WebRTC connection, the client fetches TURN server credentials from:
   ```
   https://x1.metered.live/api/v1/turn/credentials?apiKey={API_KEY}
   ```
2. Returns a list of ICE servers (STUN + TURN) with credentials
3. These are used to configure `RTCPeerConnection`
4. TURN servers relay traffic when direct peer-to-peer connection fails

**Environment Variables (Optional):**
```bash
# Custom Metered.ca API key (default: uses free tier)
export METERED_API_KEY=your_api_key_here

# Custom API endpoint (default: https://x1.metered.live/api/v1/turn/credentials)
export METERED_API_URL=https://x1.metered.live/api/v1/turn/credentials
```

**Note:** The default configuration uses Metered.ca's free tier, which is sufficient for most use cases. For production deployments with high traffic, consider using a paid TURN service.

### Messages FROM Server TO PC

#### Start Stream
Server requests PC to start a stream.

```json
{
    "type": "start_stream",
    "stream_type": "camera" | "microphone" | "screen"
}
```

**PC Response:**
- Create WebRTC peer connection
- Get media track (camera/microphone/screen)
- Create offer and send `webrtc_offer` message

#### Stop Stream
Server requests PC to stop current stream.

```json
{
    "type": "stop_stream"
}
```

**PC Response:**
- Stop media tracks
- Close peer connection
- Clean up resources

#### WebRTC Answer
Server sends WebRTC answer to PC.

```json
{
    "type": "webrtc_answer",
    "sdp": "v=0\r\no=- 1234567890 1234567890 IN IP4 0.0.0.0\r\n..."
}
```

**PC Action:**
- Set remote description with answer
- Continue ICE candidate exchange

#### WebRTC ICE Candidate
Server sends ICE candidate to PC.

```json
{
    "type": "webrtc_ice_candidate",
    "candidate": {
        "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host",
        "sdpMLineIndex": 0,
        "sdpMid": "0"
    }
}
```

**PC Action:**
- Add ICE candidate to peer connection

### Messages FROM PC TO Server

#### WebRTC Offer
PC sends WebRTC offer to server.

```json
{
    "type": "webrtc_offer",
    "sdp": "v=0\r\no=- 1234567890 1234567890 IN IP4 0.0.0.0\r\n..."
}
```

**Server Response:**
- Create answer and send `webrtc_answer` message

#### WebRTC ICE Candidate
PC sends ICE candidate to server.

```json
{
    "type": "webrtc_ice_candidate",
    "candidate": {
        "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host",
        "sdpMLineIndex": 0,
        "sdpMid": "0"
    }
}
```

#### WebRTC Stream Ready
PC notifies server that stream is ready.

```json
{
    "type": "webrtc_stream_ready",
    "stream_type": "camera" | "microphone" | "screen"
}
```

### Implementation Example

**Using `pc_client_webrtc.py` (Recommended):**

The provided `pc_client_webrtc.py` includes full TURN server support. Simply use it:

```python
from pc_client_webrtc import PCClientWebRTC

client = PCClientWebRTC(
    server_url="wss://your-server.com",
    pc_id="PC-001"
)

await client.connect()
await client.listen()  # Handles all WebRTC automatically
```

**Manual Implementation (if building custom client):**

```python
import aiohttp
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer

# Fetch TURN server credentials
async def get_ice_servers():
    try:
        api_url = "https://x1.metered.live/api/v1/turn/credentials?apiKey=4b7268b361c4e1a08789e6415026801bfb20"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    ice_servers_data = await response.json()
                    # Convert to RTCIceServer objects
                    ice_servers = []
                    for server in ice_servers_data:
                        urls = server.get('urls')
                        if isinstance(urls, str):
                            urls = [urls]
                        ice_servers.append(RTCIceServer(
                            urls=urls,
                            username=server.get('username'),
                            credential=server.get('credential')
                        ))
                    return ice_servers
    except Exception as e:
        print(f"Failed to fetch TURN credentials: {e}")
    
    # Fallback to STUN only
    return [
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["stun:stun1.l.google.com:19302"]),
    ]

# When receiving start_stream message
if message_type == "start_stream":
    stream_type = data.get("stream_type")
    
    # Get ICE servers with TURN support
    ice_servers = await get_ice_servers()
    
    # Create peer connection with TURN servers
    configuration = RTCConfiguration(iceServers=ice_servers)
    pc = RTCPeerConnection(configuration=configuration)
    
    # Get media track based on stream type
    if stream_type == "camera":
        player = MediaPlayer("video=Integrated Camera", format="dshow")
        pc.addTrack(player.video)
    elif stream_type == "microphone":
        player = MediaPlayer("audio=Microphone", format="dshow")
        pc.addTrack(player.audio)
    elif stream_type == "screen":
        # Screen capture implementation
        pc.addTrack(screen_track)
    
    # Create offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    
    # Send offer to server
    await websocket.send(json.dumps({
        "type": "webrtc_offer",
        "sdp": pc.localDescription.sdp
    }))
```

### Platform-Specific Media Access

#### Windows
```python
# Camera
MediaPlayer("video=Integrated Camera", format="dshow")

# Microphone
MediaPlayer("audio=Microphone", format="dshow")
```

#### Linux
```python
# Camera
MediaPlayer("/dev/video0", format="v4l2")

# Microphone
MediaPlayer("default", format="pulse")
```

#### macOS
```python
# Camera/Microphone
MediaPlayer("default", format="avfoundation")
```

### Important Notes

1. **Single Stream**: Starting a new stream automatically stops any existing stream
2. **On-Demand**: Streams are not always active - they start when requested
3. **Audio Chunks**: Microphone streams send continuous audio that is automatically recorded into 5-second chunks on the frontend. Each chunk can be played or downloaded individually.
4. **Permissions**: Ensure camera/microphone permissions are granted
5. **Platform Support**: Media access is platform-specific - adjust code accordingly
6. **TURN Servers Required for Cloud**: When server is deployed on cloud (e.g., Render, AWS) and PC is behind NAT, TURN servers are **essential**. The provided `pc_client_webrtc.py` includes automatic TURN server support.
7. **ICE Connection**: If ICE connection fails, check:
   - TURN servers are configured (automatic in `pc_client_webrtc.py`)
   - Firewall allows UDP traffic
   - Network supports WebRTC (some corporate networks block it)

---

## REST API Endpoints

PCs can also use REST API endpoints for additional operations.

### Base URL
```
http://{server_host}:{port}/api
```

### 1. Health Check

**GET** `/api/health`

Check server health and connection status.

**Response:**
```json
{
    "status": "healthy",
    "connected_pcs": 5,
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### 2. List All PCs

**GET** `/api/pcs`

Get list of all registered PCs.

**Query Parameters:**
- `connected_only` (boolean, optional): Filter only connected PCs

**Response:**
```json
{
    "total": 10,
    "connected": 5,
    "pcs": [
        {
            "pc_id": "PC-001",
            "name": "PC-001",
            "connected": true,
            "connected_at": "2024-01-15T10:00:00.000Z",
            "last_seen": "2024-01-15T10:30:00.000Z",
            "ip_address": "192.168.1.100",
            "hostname": "DESKTOP-ABC",
            "os_info": null,
            "metadata": {}
        }
    ]
}
```

### 3. Get Specific PC

**GET** `/api/pcs/{pc_id}`

Get details of a specific PC.

**Response:**
```json
{
    "_id": "507f1f77bcf86cd799439011",
    "pc_id": "PC-001",
    "name": "PC-001",
    "connected": true,
    "connected_at": "2024-01-15T10:00:00.000Z",
    "last_seen": "2024-01-15T10:30:00.000Z"
}
```

### 4. Check Connection Status

**GET** `/api/pcs/{pc_id}/connected`

Check if a specific PC is connected.

**Response:**
```json
{
    "pc_id": "PC-001",
    "connected": true
}
```

### 5. List Available Scripts

**GET** `/api/scripts`

Get list of all available scripts.

**Response:**
```json
{
    "total": 25,
    "scripts": [
        {
            "name": "screenshot.py",
            "size": 2048,
            "path": "/path/to/script",
            "description": null,
            "created_at": "2024-01-15T10:00:00.000Z",
            "updated_at": "2024-01-15T10:00:00.000Z",
            "parameters": {
                "PARAM_NAME": {
                    "type": "text",
                    "default": "default_value",
                    "description": "Parameter description"
                }
            }
        }
    ]
}
```

### 6. Send Script to PC

**POST** `/api/scripts/send`

Send a script to a specific PC for execution.

**Request Body (JSON):**
```json
{
    "pc_id": "PC-001",
    "script_name": "disable_input.py",
    "server_url": "http://localhost:8000",
    "script_params": {
        "DISABLE_DURATION": "30"
    }
}
```

**Request Fields:**
- `pc_id` (string, required): Target PC identifier
- `script_name` (string, required): Name of the script file (e.g., "disable_input.py")
- `server_url` (string, optional): Server HTTP URL to pass to the script. If not provided, uses `Serverurl` from `.env` file or defaults to `http://{HOST}:{PORT}`
- `script_params` (object, optional): Dictionary of script parameters. Keys are parameter names (e.g., "DISABLE_DURATION"), values are parameter values as strings

**Response:**
```json
{
    "status": "success",
    "message": "Script 'disable_input.py' sent to PC 'PC-001'",
    "pc_id": "PC-001",
    "script_name": "disable_input.py"
}
```

**Error Responses:**
- `400`: Invalid request (missing `pc_id` or `script_name`)
- `404`: PC is not connected or script not found
- `500`: Failed to send script

**Example (curl):**
```bash
curl -X POST "http://localhost:8000/api/scripts/send" \
  -H "Content-Type: application/json" \
  -d '{
    "pc_id": "PC-001",
    "script_name": "disable_input.py",
    "script_params": {
        "DISABLE_DURATION": "30"
    }
  }'
```

**Example (Python):**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/scripts/send",
    json={
        "pc_id": "PC-001",
        "script_name": "disable_input.py",
        "script_params": {
            "DISABLE_DURATION": "30"
        }
    }
)
print(response.json())
```

### 7. Broadcast Script to All PCs

**POST** `/api/scripts/broadcast`

Broadcast a script to all connected PCs.

**Request Body (JSON):**
```json
{
    "script_name": "lock_pc.py",
    "server_url": "http://localhost:8000",
    "script_params": {
        "PARAM_NAME": "value"
    }
}
```

**Request Fields:**
- `script_name` (string, required): Name of the script file
- `server_url` (string, optional): Server HTTP URL to pass to the script
- `script_params` (object, optional): Dictionary of script parameters

**Response:**
```json
{
    "status": "success",
    "message": "Script 'lock_pc.py' broadcasted to 5 PC(s)",
    "script_name": "lock_pc.py",
    "recipients": 5
}
```

**Example (curl):**
```bash
curl -X POST "http://localhost:8000/api/scripts/broadcast" \
  -H "Content-Type: application/json" \
  -d '{
    "script_name": "lock_pc.py"
  }'
```

### 8. Get Execution History

**GET** `/api/executions`

Get recent script executions.

**Query Parameters:**
- `limit` (integer, optional): Number of results (default: 100, max: 1000)

**Response:**
```json
{
    "total": 50,
    "executions": [
        {
            "_id": "507f1f77bcf86cd799439011",
            "pc_id": "PC-001",
            "script_name": "screenshot.py",
            "status": "success",
            "executed_at": "2024-01-15T10:30:00.000Z",
            "completed_at": "2024-01-15T10:30:05.000Z",
            "error_message": null,
            "result": {
                "message": "Screenshot captured successfully"
            }
        }
    ]
}
```

### 9. Get PC Execution History

**GET** `/api/executions/pc/{pc_id}`

Get execution history for a specific PC.

**Query Parameters:**
- `limit` (integer, optional): Number of results (default: 50, max: 500)

**Response:**
```json
{
    "pc_id": "PC-001",
    "total": 20,
    "executions": [...]
}
```

### 10. Get Script Execution History

**GET** `/api/executions/script/{script_name}`

Get execution history for a specific script.

**Query Parameters:**
- `limit` (integer, optional): Number of results (default: 50, max: 500)

**Response:**
```json
{
    "script_name": "screenshot.py",
    "total": 15,
    "executions": [...]
}
```

### 11. Start Camera Stream

**POST** `/api/streaming/{pc_id}/camera/start`

Start camera stream for a specific PC. This will automatically stop any existing stream.

**Response:**
```json
{
    "status": "success",
    "message": "Camera stream started for PC 'PC-001'",
    "pc_id": "PC-001",
    "stream_type": "camera"
}
```

**Error Responses:**
- `404`: PC is not connected
- `500`: Failed to start camera stream

### 12. Start Microphone Stream

**POST** `/api/streaming/{pc_id}/microphone/start`

Start microphone stream for a specific PC. Audio is streamed continuously via WebRTC and automatically recorded into 5-second chunks on the frontend. Each chunk can be played directly in the browser or downloaded as an audio file. This will automatically stop any existing stream.

**Response:**
```json
{
    "status": "success",
    "message": "Microphone stream started for PC 'PC-001'",
    "pc_id": "PC-001",
    "stream_type": "microphone"
}
```

**Error Responses:**
- `404`: PC is not connected
- `500`: Failed to start microphone stream

### 11. Start Screen Stream

**POST** `/api/streaming/{pc_id}/screen/start`

Start screen share stream for a specific PC. This will automatically stop any existing stream.

**Response:**
```json
{
    "status": "success",
    "message": "Screen stream started for PC 'PC-001'",
    "pc_id": "PC-001",
    "stream_type": "screen"
}
```

**Error Responses:**
- `404`: PC is not connected
- `500`: Failed to start screen stream

### 12. Stop Stream

**POST** `/api/streaming/{pc_id}/stop`

Stop any active stream for a specific PC.

**Response:**
```json
{
    "status": "success",
    "message": "Stream stopped for PC 'PC-001'",
    "pc_id": "PC-001",
    "stream_type": "camera"
}
```

**Error Responses:**
- `404`: PC is not connected
- `500`: Failed to stop stream

### 13. Get Stream Status

**GET** `/api/streaming/{pc_id}/status`

Get current stream status for a specific PC.

**Response:**
```json
{
    "pc_id": "PC-001",
    "has_active_stream": true,
    "stream_type": "camera",
    "connected": true
}
```

**Error Responses:**
- `404`: PC is not connected

---

## Script Logging System

The server includes a comprehensive logging system that captures all script execution output and results. Each script execution has its own dedicated logs that are stored in MongoDB and displayed in real-time on the frontend.

### Overview

- **Automatic Logging**: All script output (stdout/stderr) is automatically captured and sent to the server
- **Local Log Files**: Logs are saved locally on the PC in a `logs/` folder with proper naming
- **Real-time Streaming**: Logs are streamed to the server in real-time during script execution
- **Execution Results**: Script execution results (success/failure) are automatically logged
- **Grouped by Execution**: Each script execution has its own set of logs identified by `execution_id`

### Log Message Format

PCs should send log messages during script execution:

```json
{
    "type": "log",
    "script_name": "screenshot.py",
    "execution_id": "507f1f77bcf86cd799439011",
    "log_file_path": "logs/screenshot_20240115_103000_507f1f77.log",
    "log_content": "Screenshot captured successfully",
    "log_level": "INFO"
}
```

**Fields:**
- `type`: Must be `"log"`
- `script_name`: Name of the script being executed
- `execution_id`: Execution ID received from the script message
- `log_file_path`: Path to the local log file (optional but recommended)
- `log_content`: The log message content
- `log_level`: Log level - `"INFO"`, `"ERROR"`, `"WARNING"`, `"DEBUG"`, or `"SUCCESS"`

### Log Levels

- **INFO**: General informational messages (default)
- **ERROR**: Error messages and exceptions
- **WARNING**: Warning messages
- **DEBUG**: Debug information
- **SUCCESS**: Success messages (automatically added for successful executions)

### Local Log File Naming

Logs should be saved locally with the following naming pattern:

```
{script_name}_{timestamp}_{execution_id_short}.log
```

**Example:**
```
screenshot_20240115_103000_507f1f77.log
file_explorer_20240115_103500_a1b2c3d4.log
```

### Sending Logs During Execution

PCs should send logs in real-time as the script executes:

```python
# Example: Send log during script execution
await websocket.send(json.dumps({
    "type": "log",
    "script_name": script_name,
    "execution_id": execution_id,
    "log_file_path": log_file_path,
    "log_content": "Processing data...",
    "log_level": "INFO"
}))
```

### Execution Result Logging

When a script completes, the server automatically logs the execution result. PCs should send the `execution_complete` message with result information:

```json
{
    "type": "execution_complete",
    "execution_id": "507f1f77bcf86cd799439011",
    "status": "success",
    "result": {
        "message": "Script executed successfully",
        "log_file": "logs/screenshot_20240115_103000_507f1f77.log"
    }
}
```

The server will automatically create a log entry with level `SUCCESS` or `ERROR` based on the execution status.

### REST API Endpoints for Logs

#### 14. Get Logs

**GET** `/api/logs`

Get logs with optional filters.

**Query Parameters:**
- `limit` (integer, optional): Number of logs to retrieve (default: 200, max: 1000)
- `pc_id` (string, optional): Filter by PC ID
- `script_name` (string, optional): Filter by script name
- `log_level` (string, optional): Filter by log level (INFO, ERROR, WARNING, DEBUG, SUCCESS)

**Response:**
```json
{
    "total": 150,
    "logs": [
        {
            "_id": "507f1f77bcf86cd799439012",
            "pc_id": "PC-001",
            "script_name": "screenshot.py",
            "execution_id": "507f1f77bcf86cd799439011",
            "log_file_path": "logs/screenshot_20240115_103000_507f1f77.log",
            "log_content": "Screenshot captured successfully",
            "log_level": "SUCCESS",
            "timestamp": "2024-01-15T10:30:05.000Z"
        }
    ]
}
```

#### 15. Get PC Logs

**GET** `/api/logs/pc/{pc_id}`

Get logs for a specific PC.

**Query Parameters:**
- `limit` (integer, optional): Number of logs to retrieve (default: 100, max: 500)

**Response:**
```json
{
    "pc_id": "PC-001",
    "total": 50,
    "logs": [...]
}
```

#### 16. Get Script Logs

**GET** `/api/logs/script/{script_name}`

Get logs for a specific script.

**Query Parameters:**
- `limit` (integer, optional): Number of logs to retrieve (default: 100, max: 500)

**Response:**
```json
{
    "script_name": "screenshot.py",
    "total": 30,
    "logs": [...]
}
```

#### 17. Get Execution Logs

**GET** `/api/logs/execution/{execution_id}`

Get all logs for a specific script execution. This is the primary endpoint for viewing logs grouped by execution.

**Response:**
```json
{
    "execution_id": "507f1f77bcf86cd799439011",
    "total": 15,
    "logs": [
        {
            "_id": "507f1f77bcf86cd799439012",
            "pc_id": "PC-001",
            "script_name": "screenshot.py",
            "execution_id": "507f1f77bcf86cd799439011",
            "log_file_path": "logs/screenshot_20240115_103000_507f1f77.log",
            "log_content": "[*] Executing script: screenshot.py",
            "log_level": "INFO",
            "timestamp": "2024-01-15T10:30:00.000Z"
        },
        {
            "_id": "507f1f77bcf86cd799439013",
            "pc_id": "PC-001",
            "script_name": "screenshot.py",
            "execution_id": "507f1f77bcf86cd799439011",
            "log_file_path": "logs/screenshot_20240115_103000_507f1f77.log",
            "log_content": "Screenshot captured successfully",
            "log_level": "SUCCESS",
            "timestamp": "2024-01-15T10:30:05.000Z"
        }
    ]
}
```

### Frontend Logs Page

The frontend includes a dedicated Logs page that displays:

1. **Executions View**: Shows all script executions with expandable log sections
   - Click on an execution to view its logs
   - Logs are grouped by `execution_id`
   - Each execution shows its status, timestamps, and associated logs

2. **Logs View**: Shows all logs grouped by script execution
   - Logs are automatically grouped by `execution_id` or `script_name`
   - Each group shows the script name, PC ID, and number of log entries
   - Logs are displayed with color-coded log levels

### REST API Endpoints for File Downloads

#### 18. Request File Download

**POST** `/api/files/download`

Request a file download from a connected PC.

**Query Parameters:**
- `pc_id` (string, required): ID of the PC to download from
- `file_path` (string, required): Full path to the file on the PC

**Response:**
```json
{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "pc_id": "PC-001",
    "file_path": "C:\\Users\\Username\\Documents\\file.txt",
    "status": "requested"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/files/download?pc_id=PC-001&file_path=C%3A%5CUsers%5CUsername%5CDocuments%5Cfile.txt"
```

**Note:** The PC must be connected. The server will send a `download_file` WebSocket message to the PC, and the PC should respond with a `file_download_response` message containing the file content.

#### 19. List Downloaded Files

**GET** `/api/files`

List all files downloaded from PCs.

**Query Parameters:**
- `pc_id` (string, optional): Filter files by PC ID

**Response:**
```json
{
    "total": 5,
    "total_size_mb": 45.2,
    "files": [
        {
            "file_id": "20240115_103000_file.txt",
            "pc_id": "PC-001",
            "file_name": "20240115_103000_file.txt",
            "saved_path": "downloads/PC-001/20240115_103000_file.txt",
            "original_path": "C:\\Users\\Username\\Documents\\file.txt",
            "size": 1024,
            "size_mb": 0.001,
            "downloaded_at": "2024-01-15T10:30:00.000Z"
        }
    ]
}
```

#### 20. Download File from Server

**GET** `/api/files/{file_id}`

Download a file that was previously downloaded from a PC.

**Query Parameters:**
- `pc_id` (string, required): PC ID that owns the file

**Response:**
- File download (binary content)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/files/20240115_103000_file.txt?pc_id=PC-001" --output file.txt
```

#### 21. Delete Downloaded File

**DELETE** `/api/files/{file_id}`

Delete a downloaded file from the server.

**Query Parameters:**
- `pc_id` (string, required): PC ID that owns the file

**Response:**
```json
{
    "success": true,
    "message": "File deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/files/20240115_103000_file.txt?pc_id=PC-001"
```

### REST API Endpoints for Terminal Sessions

#### 22. Start Terminal Session

**POST** `/api/terminal/start`

Start a new PowerShell terminal session on a connected PC.

**Query Parameters:**
- `pc_id` (string, required): ID of the PC to start terminal on

**Response:**
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "pc_id": "PC-001",
    "status": "starting"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/terminal/start?pc_id=PC-001"
```

**Note:** After starting a session, the frontend should connect to the WebSocket endpoint `/ws/terminal/{pc_id}/{session_id}` to receive terminal output and send commands.

#### 23. Stop Terminal Session

**POST** `/api/terminal/stop`

Stop an active terminal session.

**Query Parameters:**
- `session_id` (string, required): Session ID to stop
- `pc_id` (string, required): PC ID

**Response:**
```json
{
    "success": true,
    "message": "Terminal session stopped"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/api/terminal/stop?session_id=550e8400-e29b-41d4-a716-446655440000&pc_id=PC-001"
```

#### 24. Get Terminal Session Info

**GET** `/api/terminal/session/{session_id}`

Get information about a terminal session.

**Response:**
```json
{
    "pc_id": "PC-001",
    "started_at": "2024-01-15T10:30:00.000Z",
    "status": "active"
}
```

### Terminal Session WebSocket Communication

#### Frontend to Server (via `/ws/terminal/{pc_id}/{session_id}`)

**Command Message:**
```json
{
    "type": "command",
    "command": "ls\r\n"
}
```

**Fields:**
- `type`: Must be `"command"`
- `command`: Command string to send to the terminal (include `\r\n` for Enter key)

#### Server to Frontend (via `/ws/terminal/{pc_id}/{session_id}`)

**Output Message:**
```json
{
    "type": "output",
    "output": "Directory listing...\r\n",
    "is_complete": true
}
```

**Fields:**
- `type`: Must be `"output"`
- `output`: Terminal output text
- `is_complete`: `true` if command completed, `false` if still running (for interactive commands like `python`)

**Error Message:**
```json
{
    "type": "error",
    "message": "Terminal session not active"
}
```

### Messages FROM Server TO PC (Terminal)

#### Start Terminal

Server requests PC to start a PowerShell terminal session.

```json
{
    "type": "start_terminal",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**PC Response:**
- Spawn a PowerShell process with interactive mode
- **CRITICAL**: Start PowerShell in the user's HOME directory (e.g., `C:\Users\shres>`) NOT in the script directory
  - Use `cwd=os.path.expanduser('~')` or `cwd=os.environ.get('USERPROFILE')` in Python
  - This ensures the terminal opens at `PS C:\Users\shres>` not `PS C:\Users\shres\Desktop\Hacking\PC>`
- Set up input/output pipes
- Read the PowerShell welcome message and initial prompt
- Send `terminal_ready` message when ready
- **IMPORTANT**: After sending `terminal_ready`, immediately send the PowerShell welcome message and initial prompt in a `terminal_output` message:
  ```json
  {
      "type": "terminal_output",
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "output": "Windows PowerShell\nCopyright (C) Microsoft Corporation. All rights reserved.\n\nInstall the latest PowerShell for new features and improvements! https://aka.ms/PSWindows\n\nPS C:\\Users\\shres> ",
      "is_complete": false
  }
  ```
- Listen for `terminal_command` messages

#### Terminal Command

Server sends a command to execute in the terminal.

```json
{
    "type": "terminal_command",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "command": "ls\r\n"
}
```

**PC Action:**
- Write command to PowerShell process stdin (include `\r\n` for Enter key)
- Read output from stdout/stderr in real-time
- Send `terminal_output` messages with output as it arrives
- **CRITICAL**: After command completes, the PC must:
  1. Wait for the PowerShell prompt to appear (e.g., `PS C:\Users\shres>`)
  2. **ALWAYS include the prompt in the output** - this is REQUIRED for the user to enter the next command
  3. Set `is_complete: true` when the prompt appears (for non-interactive commands)
  4. Set `is_complete: false` for interactive commands (like `python`, `node`, etc.) and keep streaming output
  5. **If no prompt appears within 10 seconds**, the frontend will automatically show one, but the PC should always send it

#### Terminal Interrupt (Ctrl+C)

Server sends an interrupt signal to stop the current command.

```json
{
    "type": "terminal_interrupt",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**PC Action:**
- Send `\x03` (Ctrl+C) to the PowerShell process stdin
- This will interrupt the currently running command
- Wait for the PowerShell prompt to appear
- Send `terminal_output` with the prompt (e.g., `PS C:\Users\shres> `)
- Set `is_complete: true` to indicate the interrupt is complete and terminal is ready for new input

**Example Output Format:**
```json
{
    "type": "terminal_output",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "output": "ls\r\nfile1.txt\r\nfile2.txt\r\nPS C:\\Users\\Username> ",
    "is_complete": true
}
```

**Important:**
- Always include the PowerShell prompt (`PS C:\Users\Username> `) at the end of output for non-interactive commands
- The prompt should show the current working directory
- Use `\r\n` for line breaks on Windows
- Send output in chunks as it becomes available for better responsiveness

#### Stop Terminal

Server requests PC to stop the terminal session.

```json
{
    "type": "stop_terminal",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**PC Action:**
- Kill the PowerShell process
- Clean up pipes
- Close the session

### Messages FROM PC TO Server (Terminal)

#### Terminal Ready

PC confirms terminal session is ready.

```json
{
    "type": "terminal_ready",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Terminal Output

PC sends terminal output.

```json
{
    "type": "terminal_output",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "output": "PS C:\\Users\\Username> ls\r\nfile1.txt\r\nfile2.txt\r\nPS C:\\Users\\Username> ",
    "is_complete": true
}
```

**Fields:**
- `type`: Must be `"terminal_output"`
- `session_id`: Session ID
- `output`: Terminal output text (can include ANSI escape codes for colors)
- `is_complete`: `true` if command completed, `false` if still running

**Important Notes:**
- For commands like `ls`, `dir`, `echo`, etc., set `is_complete: true` after output is sent
- For interactive commands like `python`, `node`, `cmd`, etc., set `is_complete: false` and keep sending output as it arrives
- Include newlines (`\r\n` on Windows) in output
- Send output in real-time as it becomes available

#### Terminal Error

PC reports terminal error.

```json
{
    "type": "terminal_error",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "error": "Failed to start PowerShell process"
}
```

### PC Client Implementation Example

```python
import subprocess
import threading
import queue

class TerminalSession:
    def __init__(self, session_id, websocket):
        self.session_id = session_id
        self.websocket = websocket
        self.process = None
        self.output_queue = queue.Queue()
        self.running = False
    
    async def start(self):
        """Start PowerShell process"""
        try:
            # CRITICAL: Start in user's HOME directory, NOT script directory
            import os
            home_dir = os.path.expanduser('~')  # Gets C:\Users\shres on Windows
            # Alternative: os.environ.get('USERPROFILE') or os.path.expandvars('%USERPROFILE%')
            
            # Start PowerShell process with interactive mode
            self.process = subprocess.Popen(
                ['powershell.exe', '-NoExit', '-NoProfile'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # Unbuffered for real-time output
                universal_newlines=True,
                cwd=home_dir  # Start in user's home directory (e.g., C:\Users\shres)
            )
            
            self.running = True
            
            # Start output reader thread
            threading.Thread(target=self._read_output, daemon=True).start()
            
            # Send ready message
            await self.websocket.send_json({
                "type": "terminal_ready",
                "session_id": self.session_id
            })
            
        except Exception as e:
            await self.websocket.send_json({
                "type": "terminal_error",
                "session_id": self.session_id,
                "error": str(e)
            })
    
    def _read_output(self):
        """Read output from PowerShell process"""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(line)
                elif self.process.poll() is not None:
                    # Process ended
                    break
            except Exception as e:
                break
    
    async def send_command(self, command):
        """Send command to PowerShell process"""
        if self.process and self.process.stdin:
            try:
                self.current_command_complete = False
                self.process.stdin.write(command)
                self.process.stdin.flush()
            except Exception as e:
                await self.websocket.send_json({
                    "type": "terminal_error",
                    "session_id": self.session_id,
                    "error": f"Failed to send command: {str(e)}"
                })
    
    async def send_interrupt(self):
        """Send Ctrl+C interrupt to PowerShell process"""
        if self.process and self.process.stdin:
            try:
                # Send Ctrl+C signal (\x03)
                self.process.stdin.write('\x03')
                self.process.stdin.flush()
                self.current_command_complete = False
                # Wait a moment for interrupt to process
                await asyncio.sleep(0.2)
            except Exception as e:
                await self.websocket.send_json({
                    "type": "terminal_error",
                    "session_id": self.session_id,
                    "error": f"Failed to send interrupt: {str(e)}"
                })
    
    async def send_output(self):
        """Send queued output to server"""
        while self.running:
            try:
                output = self.output_queue.get(timeout=0.1)
                # Determine if command is complete
                # For simple commands, check if prompt appears
                is_complete = "PS " in output or ">" in output
                
                await self.websocket.send_json({
                    "type": "terminal_output",
                    "session_id": self.session_id,
                    "output": output,
                    "is_complete": is_complete
                })
            except queue.Empty:
                continue
            except Exception as e:
                break
    
    async def stop(self):
        """Stop terminal session"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
```

### Best Practices for Terminal Sessions

1. **Session Management**: Always stop sessions when done or when page closes
2. **Interactive Commands**: Handle both one-off commands (like `ls`) and interactive programs (like `python`)
3. **Output Streaming**: Send output in real-time as it becomes available
4. **Error Handling**: Handle process failures gracefully
5. **Cleanup**: Always clean up processes and pipes when session ends
6. **ANSI Support**: Terminal supports ANSI escape codes for colors and formatting

### Best Practices for Logging

1. **Send Logs in Real-time**: Send log messages as they occur during script execution
2. **Include Execution ID**: Always include the `execution_id` in log messages
3. **Use Appropriate Log Levels**: Use the correct log level for each message
4. **Save Locally**: Save logs to local files for offline access
5. **Include File Paths**: Include `log_file_path` in log messages for reference
6. **Log Execution Results**: Always send `execution_complete` with result information

### Example: Complete Logging Implementation

```python
async def execute_script(self, script_content: str, script_name: str, 
                        server_url: str, execution_id: str):
    """Execute script with comprehensive logging"""
    import logging
    from datetime import datetime
    import os
    
    # Create logs directory
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{script_name.replace('.py', '')}_{timestamp}_{execution_id[:8]}.log"
    log_file_path = os.path.join(logs_dir, log_filename)
    
    # Setup file logging
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    script_logger = logging.getLogger(f"script_{execution_id}")
    script_logger.setLevel(logging.DEBUG)
    script_logger.addHandler(file_handler)
    
    # Send initial log
    await self.send_message({
        "type": "log",
        "script_name": script_name,
        "execution_id": execution_id,
        "log_file_path": log_file_path,
        "log_content": f"[*] Executing script: {script_name}",
        "log_level": "INFO"
    })
    
    try:
        # Execute script (capture stdout/stderr)
        # ... script execution code ...
        
        # Send success log
        await self.send_message({
            "type": "log",
            "script_name": script_name,
            "execution_id": execution_id,
            "log_file_path": log_file_path,
            "log_content": f"Script '{script_name}' executed successfully",
            "log_level": "SUCCESS"
        })
        
        # Send execution complete
        await self.send_message({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "success",
            "result": {
                "message": f"Script '{script_name}' executed successfully",
                "log_file": log_file_path
            }
        })
        
    except Exception as e:
        error_msg = f"Error executing script '{script_name}': {str(e)}"
        
        # Send error log
        await self.send_message({
            "type": "log",
            "script_name": script_name,
            "execution_id": execution_id,
            "log_file_path": log_file_path,
            "log_content": error_msg,
            "log_level": "ERROR"
        })
        
        # Send execution complete with error
        await self.send_message({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": error_msg,
            "result": {
                "log_file": log_file_path
            }
        })
```

---

## Complete Client Example

### Python Client Example

```python
"""
Complete PC Client Example
Connects to server, receives scripts, and executes them
"""
import asyncio
import json
import os
import sys
import tempfile
import socket
from websockets import connect
from websockets.exceptions import ConnectionClosed

# Configuration
SERVER_URL = os.getenv("SERVER_URL", "ws://localhost:8000")
PC_ID = os.getenv("PC_ID", socket.gethostname())


class PCClient:
    """PC Client for Remote Script Server"""
    
    def __init__(self, server_url: str, pc_id: str):
        self.server_url = server_url
        self.pc_id = pc_id
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Connect to the server"""
        uri = f"{self.server_url}/ws/{self.pc_id}"
        print(f"[*] Connecting to {uri}...")
        
        try:
            self.websocket = await connect(uri)
            self.running = True
            print(f"[+] Connected as {self.pc_id}")
            return True
        except Exception as e:
            print(f"[!] Connection failed: {e}")
            return False
    
    async def execute_script(self, script_content: str, script_name: str, 
                            server_url: str, execution_id: str, script_params: dict = None):
        """Execute a Python script received from server"""
        print(f"[*] Executing script: {script_name}")
        
        # CRITICAL: Set script parameters as environment variables
        if script_params:
            for param_name, param_value in script_params.items():
                os.environ[param_name] = str(param_value)
                print(f"[*] Parameter {param_name} = {param_value}")
        
        # Set standard environment variables
        os.environ["SERVER_URL"] = server_url
        os.environ["PC_ID"] = self.pc_id
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        try:
            # Prepare script globals with SERVER_URL
            script_globals = {
                '__name__': '__main__',
                '__file__': temp_script,
                'SERVER_URL': server_url,
                'PC_ID': self.pc_id
            }
            
            # Execute script
            exec(compile(script_content, temp_script, 'exec'), script_globals)
            
            # Send success status
            await self.send_execution_complete(
                execution_id,
                status="success",
                result={"message": f"Script '{script_name}' executed successfully"}
            )
            
            print(f"[+] Script '{script_name}' executed successfully")
            
        except Exception as e:
            error_msg = f"Error executing script '{script_name}': {str(e)}"
            print(f"[!] {error_msg}")
            
            # Send error status
            await self.send_execution_complete(
                execution_id,
                status="failed",
                error_message=error_msg
            )
        
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_script)
            except:
                pass
    
    async def send_message(self, message: dict):
        """Send a message to the server"""
        if self.websocket and self.running:
            try:
                await self.websocket.send(json.dumps(message))
            except Exception as e:
                print(f"[!] Error sending message: {e}")
                self.running = False
    
    async def send_heartbeat(self):
        """Send heartbeat to server"""
        await self.send_message({
            "type": "heartbeat",
            "status": "ok"
        })
    
    async def send_status(self, message: str):
        """Send status update"""
        await self.send_message({
            "type": "status",
            "message": message
        })
    
    async def send_execution_complete(self, execution_id: str, status: str,
                                     error_message: str = None, result: dict = None):
        """Send execution completion status"""
        message = {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": status
        }
        
        if error_message:
            message["error_message"] = error_message
        
        if result:
            message["result"] = result
        
        await self.send_message(message)
    
    async def handle_message(self, data: dict):
        """Handle incoming messages from server"""
        message_type = data.get("type")
        
        if message_type == "connection":
            print(f"[*] {data.get('message', '')}")
            await self.send_status(f"PC {self.pc_id} ready and waiting for scripts")
        
        elif message_type == "script":
            # Execute the script
            await self.execute_script(
                script_content=data.get("script_content"),
                script_name=data.get("script_name"),
                server_url=data.get("server_url", self.server_url.replace("ws://", "http://")),
                execution_id=data.get("execution_id"),
                script_params=data.get("script_params", {})  # Get script parameters
            )
        
        elif message_type == "ping":
            # Respond to ping
            await self.send_message({"type": "pong"})
        
        else:
            print(f"[*] Received message type: {message_type}")
    
    async def listen(self):
        """Listen for messages from server"""
        try:
            while self.running:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=30.0
                    )
                    
                    data = json.loads(message)
                    await self.handle_message(data)
                
                except asyncio.TimeoutError:
                    # Send heartbeat if no message received
                    await self.send_heartbeat()
                
                except ConnectionClosed:
                    print("[!] Connection closed by server")
                    break
                
                except Exception as e:
                    print(f"[!] Error receiving message: {e}")
                    break
        
        except Exception as e:
            print(f"[!] Listen error: {e}")
        finally:
            self.running = False
    
    async def run(self):
        """Main client loop"""
        while True:
            if await self.connect():
                await self.listen()
            
            if self.running:
                print("[*] Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            else:
                break


async def main():
    """Main entry point"""
    print("=" * 60)
    print("  Remote Script Server - PC Client")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"PC ID: {PC_ID}")
    print("=" * 60)
    
    client = PCClient(SERVER_URL, PC_ID)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        print("\n[*] Client shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript/Node.js Client Example

```javascript
/**
 * Complete PC Client Example (Node.js)
 */
const WebSocket = require('ws');
const { exec } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

// Configuration
const SERVER_URL = process.env.SERVER_URL || 'ws://localhost:8000';
const PC_ID = process.env.PC_ID || os.hostname();

class PCClient {
    constructor(serverUrl, pcId) {
        this.serverUrl = serverUrl;
        this.pcId = pcId;
        this.ws = null;
        this.running = false;
        this.reconnectTimeout = null;
    }

    connect() {
        const uri = `${this.serverUrl}/ws/${this.pcId}`;
        console.log(`[*] Connecting to ${uri}...`);

        this.ws = new WebSocket(uri);

        this.ws.on('open', () => {
            console.log(`[+] Connected as ${this.pcId}`);
            this.running = true;
            this.sendStatus(`PC ${this.pcId} ready and waiting for scripts`);
        });

        this.ws.on('message', (data) => {
            try {
                const message = JSON.parse(data.toString());
                this.handleMessage(message);
            } catch (error) {
                console.error('[!] Error parsing message:', error);
            }
        });

        this.ws.on('error', (error) => {
            console.error('[!] WebSocket error:', error);
        });

        this.ws.on('close', () => {
            console.log('[!] Connection closed');
            this.running = false;
            this.reconnect();
        });
    }

    async handleMessage(data) {
        const messageType = data.type;

        if (messageType === 'connection') {
            console.log(`[*] ${data.message || ''}`);
        } else if (messageType === 'script') {
            await this.executeScript(
                data.script_content,
                data.script_name,
                data.server_url || this.serverUrl.replace('ws://', 'http://'),
                data.execution_id,
                data.script_params || {}  // Get script parameters
            );
        } else if (messageType === 'ping') {
            this.sendMessage({ type: 'pong' });
        } else {
            console.log(`[*] Received message type: ${messageType}`);
        }
    }

    async executeScript(scriptContent, scriptName, serverUrl, executionId, scriptParams = {}) {
        console.log(`[*] Executing script: ${scriptName}`);

        // CRITICAL: Set script parameters as environment variables
        const env = {
            ...process.env,
            SERVER_URL: serverUrl,
            PC_ID: this.pcId
        };
        
        // Add script parameters to environment
        for (const [paramName, paramValue] of Object.entries(scriptParams)) {
            env[paramName] = String(paramValue);  // Convert to string
            console.log(`[*] Parameter ${paramName} = ${paramValue}`);
        }

        // Create temporary file
        const tempFile = path.join(os.tmpdir(), `script_${Date.now()}.py`);

        try {
            // Write script to file
            fs.writeFileSync(tempFile, scriptContent);

            // Execute script with environment variables (including script_params)

            exec(`python "${tempFile}"`, { env }, (error, stdout, stderr) => {
                if (error) {
                    const errorMsg = `Error executing script '${scriptName}': ${error.message}`;
                    console.error(`[!] ${errorMsg}`);
                    this.sendExecutionComplete(executionId, 'failed', errorMsg);
                } else {
                    console.log(`[+] Script '${scriptName}' executed successfully`);
                    this.sendExecutionComplete(executionId, 'success', {
                        message: `Script '${scriptName}' executed successfully`,
                        stdout: stdout,
                        stderr: stderr
                    });
                }

                // Clean up temp file
                try {
                    fs.unlinkSync(tempFile);
                } catch (e) {
                    // Ignore cleanup errors
                }
            });
        } catch (error) {
            const errorMsg = `Error executing script '${scriptName}': ${error.message}`;
            console.error(`[!] ${errorMsg}`);
            this.sendExecutionComplete(executionId, 'failed', errorMsg);

            // Clean up temp file
            try {
                if (fs.existsSync(tempFile)) {
                    fs.unlinkSync(tempFile);
                }
            } catch (e) {
                // Ignore cleanup errors
            }
        }
    }

    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        }
    }

    sendHeartbeat() {
        this.sendMessage({
            type: 'heartbeat',
            status: 'ok'
        });
    }

    sendStatus(message) {
        this.sendMessage({
            type: 'status',
            message: message
        });
    }

    sendExecutionComplete(executionId, status, errorMessage = null, result = null) {
        const message = {
            type: 'execution_complete',
            execution_id: executionId,
            status: status
        };

        if (errorMessage) {
            message.error_message = errorMessage;
        }

        if (result) {
            message.result = result;
        }

        this.sendMessage(message);
    }

    reconnect() {
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
        }

        console.log('[*] Reconnecting in 5 seconds...');
        this.reconnectTimeout = setTimeout(() => {
            this.connect();
        }, 5000);
    }

    start() {
        // Send heartbeat every 30 seconds
        setInterval(() => {
            if (this.running) {
                this.sendHeartbeat();
            }
        }, 30000);

        this.connect();
    }
}

// Start client
console.log('='.repeat(60));
console.log('  Remote Script Server - PC Client');
console.log('='.repeat(60));
console.log(`Server: ${SERVER_URL}`);
console.log(`PC ID: ${PC_ID}`);
console.log('='.repeat(60));

const client = new PCClient(SERVER_URL, PC_ID);
client.start();

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n[*] Client shutting down...');
    process.exit(0);
});
```

---

## Error Handling

### Connection Errors

Always implement reconnection logic:

```python
async def connect_with_retry(max_retries=5, delay=5):
    for attempt in range(max_retries):
        if await connect():
            return True
        await asyncio.sleep(delay)
    return False
```

### Script Execution Errors

Always wrap script execution in try-except:

```python
try:
    exec(script_content, script_globals)
    await send_success(execution_id)
except Exception as e:
    await send_error(execution_id, str(e))
```

**⚠️ CRITICAL: Before executing scripts, ALWAYS set environment variables:**

```python
# BEFORE executing script, set these environment variables:
import os

# 1. SERVER_URL (from server_url field in script message)
os.environ["SERVER_URL"] = server_url  # REQUIRED!

# 2. PC_ID (your PC identifier)
os.environ["PC_ID"] = self.pc_id  # REQUIRED!

# 3. Script parameters (from script_params field)
for param_name, param_value in script_params.items():
    os.environ[param_name] = str(param_value)  # REQUIRED if script needs parameters!

# NOW execute the script
exec(script_content, script_globals)
```

**Common Error:** If you see "SERVER_URL not set" or "PC_ID not set", it means you forgot to set these environment variables before executing the script.

### Network Errors

Handle WebSocket disconnections gracefully:

```python
try:
    message = await websocket.recv()
except ConnectionClosed:
    # Reconnect logic
    await reconnect()
```

---

## Best Practices

### 1. PC ID Selection
- Use unique, persistent identifiers
- Recommended: Hostname, MAC address, or custom UUID
- Avoid: Random IDs that change on restart

### 2. Connection Management
- Implement automatic reconnection
- Send periodic heartbeats
- Handle connection drops gracefully

### 3. Script Execution
- Always execute scripts in isolated environments
- Use temporary files for script storage
- Clean up temporary files after execution
- Set proper environment variables (SERVER_URL, PC_ID)

### 4. Status Reporting
- Always send `execution_complete` message after script execution
- Include `execution_id` in all status messages
- Provide detailed error messages for debugging

### 5. Security
- Validate script content before execution (if needed)
- Run scripts with appropriate permissions
- Don't execute untrusted code without validation

### 6. Error Messages
- Provide clear, descriptive error messages
- Include stack traces for debugging
- Log errors locally for troubleshooting

### 7. Performance
- Don't block the WebSocket connection during script execution
- Use async/await for long-running operations
- Implement timeouts for script execution

---

## Environment Variables

PC clients can use these environment variables:

- `SERVER_URL`: WebSocket server URL (default: `ws://localhost:8000`)
- `PC_ID`: Unique PC identifier (default: hostname)
- `METERED_API_KEY`: (Optional) Metered.ca API key for TURN server credentials (default: uses free tier key)
- `METERED_API_URL`: (Optional) Metered.ca API endpoint (default: `https://x1.metered.live/api/v1/turn/credentials`)

**Example:**
```bash
export SERVER_URL=ws://192.168.1.100:8000
export PC_ID=PC-001
python client.py
```

**For WebRTC Streaming (TURN Server Support):**

The PC client automatically fetches TURN server credentials from Metered.ca to enable WebRTC streaming through NAT/firewalls. This is essential for cloud deployments where the server is on a different network.

**Default Configuration:**
- Uses free Metered.ca TURN servers
- Automatically fetches credentials on first connection
- Caches credentials for 1 hour
- Falls back to STUN-only if TURN fetch fails

**Custom TURN Server:**
```bash
export METERED_API_KEY=your_api_key_here
export METERED_API_URL=https://x1.metered.live/api/v1/turn/credentials
python pc_client_webrtc.py
```

**Note:** The PC client (`pc_client_webrtc.py`) includes built-in TURN server support. For basic script execution without streaming, you can use the simpler `example_client.py` which doesn't require TURN servers.

---

## Testing Your Client

### 1. Test Connection
```bash
# Start your client
python client.py

# Check if it appears in connected PCs
curl http://localhost:8000/api/pcs
```

### 2. Test Script Execution
```bash
# Send a test script to your PC (with JSON body)
curl -X POST "http://localhost:8000/api/scripts/send" \
  -H "Content-Type: application/json" \
  -d '{
    "pc_id": "PC-001",
    "script_name": "screenshot.py"
  }'

# Send a script with parameters
curl -X POST "http://localhost:8000/api/scripts/send" \
  -H "Content-Type: application/json" \
  -d '{
    "pc_id": "PC-001",
    "script_name": "disable_input.py",
    "script_params": {
        "DISABLE_DURATION": "30"
    }
  }'
```

### 3. Check Execution History
```bash
# View execution history
curl http://localhost:8000/api/executions/pc/PC-001
```

---

## Support

For issues or questions:
1. Check server logs for connection errors
2. Verify WebSocket endpoint is accessible
3. Ensure PC_ID is unique
4. Check execution history in MongoDB
5. Review error messages in execution records

## Troubleshooting Common Errors

### Error: "SERVER_URL not set. Server should inject this variable."

**Cause:** The PC client is not setting `SERVER_URL` as an environment variable before executing the script.

**Solution:** Make sure your PC client code sets `os.environ["SERVER_URL"]` from the `server_url` field in the script message:

```python
# In your script message handler
if message_type == "script":
    server_url = data.get("server_url")
    
    # CRITICAL: Set SERVER_URL environment variable
    import os
    if server_url:
        os.environ["SERVER_URL"] = server_url
    else:
        # Fallback
        os.environ["SERVER_URL"] = "http://localhost:8000"
    
    # Then execute the script
    exec(script_content, ...)
```

**Check:** Add this debug line before script execution to verify:
```python
print(f"[DEBUG] SERVER_URL = {os.environ.get('SERVER_URL', 'NOT SET!')}")
```

### Error: Script parameters not working (using default values)

**Cause:** The PC client is not setting script parameters as environment variables.

**Solution:** Make sure your PC client sets all parameters from `script_params`:

```python
# Get script_params from message
script_params = data.get("script_params", {})

# Set each parameter as environment variable
for param_name, param_value in script_params.items():
    os.environ[param_name] = str(param_value)
```

### Error: "PC_ID not set"

**Cause:** The PC client is not setting `PC_ID` as an environment variable.

**Solution:** Always set `os.environ["PC_ID"] = self.pc_id` before executing scripts.

---

## Quick Reference

### Required Message After Script Execution

```json
{
    "type": "execution_complete",
    "execution_id": "{execution_id_from_script_message}",
    "status": "success" | "failed",
    "error_message": "{if_failed}",
    "result": "{optional_data}"
}
```

### WebSocket URL Format

```
ws://{host}:{port}/ws/{pc_id}
```

### Script Execution Environment

Scripts receive these global variables:
- `SERVER_URL`: Server HTTP URL
- `PC_ID`: PC identifier

---

**Last Updated**: 2024-01-15

