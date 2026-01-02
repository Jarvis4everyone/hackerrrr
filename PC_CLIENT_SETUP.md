# PC Client Setup Guide

## Overview
The PC client connects to the remote script server and enables WebRTC streaming (camera, microphone, screen) and script execution.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Install Dependencies

```bash
pip install websockets aiortc
```

**Note**: `aiortc` is required for WebRTC streaming. If you only need script execution, you can skip it, but WebRTC features will be disabled.

## Configuration

### Environment Variables

The PC client can be configured using environment variables:

#### Required
- `SERVER_URL`: Server WebSocket URL
  - **Development**: `ws://localhost:8000` or `http://localhost:8000`
  - **Production**: `wss://your-server.com` or `https://your-server.com`
  - The client automatically converts HTTP/HTTPS to WS/WSS

#### Optional
- `PC_ID`: Unique identifier for this PC (defaults to hostname)
- `TURN_SERVER_URL`: TURN server URL for WebRTC (optional, for better NAT traversal)
  - Example: `turn:your-turn-server.com:3478?transport=udp`
- `TURN_SERVER_USERNAME`: TURN server username (if required)
- `TURN_SERVER_PASSWORD`: TURN server password (if required)

### Setting Environment Variables

#### Windows (PowerShell)
```powershell
$env:SERVER_URL="wss://your-server.com"
$env:PC_ID="MyPC-001"
python pc_client_webrtc.py
```

#### Windows (Command Prompt)
```cmd
set SERVER_URL=wss://your-server.com
set PC_ID=MyPC-001
python pc_client_webrtc.py
```

#### Linux/macOS
```bash
export SERVER_URL="wss://your-server.com"
export PC_ID="MyPC-001"
python pc_client_webrtc.py
```

#### Using .env file (Recommended)
Create a `.env` file in the same directory:

```env
SERVER_URL=wss://your-server.com
PC_ID=MyPC-001
TURN_SERVER_URL=turn:your-turn-server.com:3478?transport=udp
TURN_SERVER_USERNAME=your_username
TURN_SERVER_PASSWORD=your_password
```

Then use a library like `python-dotenv`:
```bash
pip install python-dotenv
```

And modify the client to load the .env file.

## Usage

### Basic Usage

```bash
python pc_client_webrtc.py
```

### Production Setup

For production servers (HTTPS), the client automatically:
- Converts `https://` URLs to `wss://` (secure WebSocket)
- Uses multiple STUN servers for better connectivity
- Supports TURN servers for NAT traversal

**Example for production:**
```bash
export SERVER_URL="https://hackerrrr-backend.onrender.com"
python pc_client_webrtc.py
```

The client will automatically use `wss://hackerrrr-backend.onrender.com` for WebSocket connections.

## WebRTC Streaming

### Camera Stream
The client supports camera streaming. Camera access is platform-specific:

- **Windows**: Uses DirectShow (`dshow`)
  - Example: `MediaPlayer("video=Integrated Camera", format="dshow")`
- **Linux**: Uses V4L2
  - Example: `MediaPlayer("/dev/video0", format="v4l2")`
- **macOS**: Uses AVFoundation
  - Example: `MediaPlayer("default", format="avfoundation")`

### Microphone Stream
Similar to camera, microphone access is platform-specific:

- **Windows**: `MediaPlayer("audio=Microphone", format="dshow")`
- **Linux**: `MediaPlayer("default", format="pulse")`
- **macOS**: `MediaPlayer("default", format="avfoundation")`

### Screen Share
Screen sharing implementation is platform-specific and may require additional libraries.

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to server
- **Solution**: Check `SERVER_URL` is correct
- **Solution**: Ensure server is running and accessible
- **Solution**: For production, use `wss://` (secure WebSocket)

**Problem**: WebSocket connection fails with SSL error
- **Solution**: Ensure you're using `wss://` for HTTPS servers
- **Solution**: Check server SSL certificate is valid

### WebRTC Issues

**Problem**: WebRTC not available
- **Solution**: Install `aiortc`: `pip install aiortc`
- **Solution**: Check Python version (3.8+ required)

**Problem**: Camera/microphone not accessible
- **Solution**: Check platform-specific media access (see above)
- **Solution**: Ensure camera/microphone permissions are granted
- **Solution**: Verify device name/ID is correct

**Problem**: WebRTC connection fails (ICE connection failed)
- **Solution**: Add TURN server configuration
- **Solution**: Check firewall/NAT settings
- **Solution**: Ensure STUN/TURN servers are accessible

### NAT Traversal

If you're behind a strict NAT or firewall, you may need a TURN server:

1. **Get a TURN server** (see main README for options)
2. **Set environment variables**:
   ```bash
   export TURN_SERVER_URL="turn:your-server.com:3478?transport=udp"
   export TURN_SERVER_USERNAME="your_username"
   export TURN_SERVER_PASSWORD="your_password"
   ```
3. **Restart the client**

## Advanced Configuration

### Custom ICE Servers

You can modify the `get_ice_servers()` function in `pc_client_webrtc.py` to add custom STUN/TURN servers:

```python
def get_ice_servers():
    ice_servers = [
        RTCIceServer(urls=["stun:stun.l.google.com:19302"]),
        RTCIceServer(urls=["stun:your-custom-stun.com:19302"]),
    ]
    
    # Add TURN server
    if TURN_SERVER_URL:
        turn_config = {"urls": [TURN_SERVER_URL]}
        if TURN_SERVER_USERNAME and TURN_SERVER_PASSWORD:
            turn_config["username"] = TURN_SERVER_USERNAME
            turn_config["credential"] = TURN_SERVER_PASSWORD
        ice_servers.append(RTCIceServer(**turn_config))
    
    return ice_servers
```

### Running as a Service

#### Windows (Task Scheduler)
1. Create a batch file (`start_client.bat`):
   ```batch
   @echo off
   cd /d "C:\path\to\client"
   set SERVER_URL=wss://your-server.com
   python pc_client_webrtc.py
   ```
2. Schedule it to run at startup

#### Linux (systemd)
Create `/etc/systemd/system/pc-client.service`:
```ini
[Unit]
Description=PC Client for Remote Script Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/client
Environment="SERVER_URL=wss://your-server.com"
Environment="PC_ID=MyPC-001"
ExecStart=/usr/bin/python3 /path/to/client/pc_client_webrtc.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable pc-client
sudo systemctl start pc-client
```

## Security Notes

1. **Use WSS in production**: Always use `wss://` (or `https://` which auto-converts) for production servers
2. **TURN credentials**: Store TURN server credentials securely (environment variables, not in code)
3. **PC_ID**: Use unique, identifiable PC IDs for easier management
4. **Network security**: Ensure your network allows WebSocket and WebRTC traffic

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review server logs for connection errors
3. Check browser console (for frontend) and client logs (for PC client)
4. Verify all environment variables are set correctly

