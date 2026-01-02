# Agora Setup Guide

Complete setup instructions for Agora integration in the Remote Script Server.

## Prerequisites

1. **Agora Account**: Sign up at https://www.agora.io/
2. **Agora App**: Create a new project in Agora Console
3. **Credentials**: Get your App ID and App Certificate

## Backend Setup

### 1. Install Dependencies

```bash
pip install agora-token-builder
```

**Note**: If `agora-token-builder` is not available, the system will use the fallback temp token from environment variables.

### 2. Configure Environment Variables

Set the following environment variables in your `.env` file or deployment platform:

```bash
# Agora App ID
AGORA_APP_ID=7b3640aaf0394f8d809829db4abbe902

# Agora App Certificate (for token generation)
AGORA_APP_CERTIFICATE=15b63fe200b44aa5a2428ace9d857ba4

# Optional: Temporary token (fallback if token builder fails)
AGORA_TEMP_TOKEN=007eJxTYIgsCZObte2wn++EMNMq9icLi4NZnXrkkzFykwmCcZm5kYJCamGRhbmqRZpFgYWFoYWaYkmSQmJaVaGhhtzw3PbAhkZLh3I5qVkQECQXwmhgpDBgYA3Xga0Q==
```

### 3. Token Generation

The backend automatically generates tokens for:
- **Publishers** (PC clients): Can publish camera/microphone/screen streams
- **Subscribers** (Frontend): Can subscribe to and view streams

Tokens are valid for 1 hour by default and are automatically regenerated when needed.

## Frontend Setup

### 1. Install Agora SDK

```bash
cd frontend
npm install agora-rtc-sdk-ng
```

### 2. Usage

The frontend automatically:
- Fetches subscriber tokens from the backend API
- Joins Agora channels
- Subscribes to remote video/audio tracks
- Handles connection state changes

No additional configuration needed - the frontend uses the Agora credentials from the backend.

## PC Client Setup

### 1. Install Agora Python SDK

**Important**: The Agora Python SDK requires native dependencies and may need additional setup.

#### Option A: Using pip (if available)
```bash
pip install agora-python-sdk
```

#### Option B: Manual Installation
1. Download the Agora Python SDK from: https://docs.agora.io/en/video-calling/get-started/get-started-sdk
2. Follow platform-specific installation instructions
3. For Windows: May require Visual C++ Redistributable
4. For Linux: May require additional system libraries

### 2. Using the PC Client

```python
from pc_client_agora import PCClientAgora

# Create client
client = PCClientAgora(
    server_url="wss://your-server.com",
    pc_id="PC-001"
)

# Run client (handles all Agora streaming automatically)
await client.run()
```

### 3. Platform-Specific Notes

#### Windows
- Camera: Automatically detects available cameras
- Microphone: Uses default audio input device
- Screen: Requires screen capture permissions

#### Linux
- Camera: Uses `/dev/video0`, `/dev/video1`, etc.
- Microphone: Uses default PulseAudio device
- Screen: Requires X11 or Wayland screen capture support

#### macOS
- Camera/Microphone: Requires permissions in System Preferences
- Screen: Requires screen recording permissions

## How It Works

### Stream Flow

1. **Server initiates stream** via REST API:
   ```
   POST /api/streaming/{pc_id}/camera/start
   ```

2. **Server generates Agora token** with publisher role

3. **Server sends WebSocket message** to PC with Agora config:
   ```json
   {
       "type": "start_stream",
       "stream_type": "camera",
       "agora": {
           "channel_name": "PC-001_camera",
           "token": "agora_token",
           "uid": 0,
           "app_id": "7b3640aaf0394f8d809829db4abbe902"
       }
   }
   ```

4. **PC joins Agora channel** and publishes media

5. **Frontend requests subscriber token**:
   ```
   GET /api/streaming/{pc_id}/token?stream_type=camera&uid=0
   ```

6. **Frontend joins channel** and subscribes to remote tracks

7. **Media flows** through Agora's infrastructure

### Channel Naming

Channels follow the pattern: `{pc_id}_{stream_type}`

Examples:
- `PC-001_camera`
- `PC-001_microphone`
- `PC-001_screen`

### Token Roles

- **PUBLISHER**: PC clients that publish media (camera, microphone, screen)
- **SUBSCRIBER**: Frontend clients that subscribe to and view media

## Troubleshooting

### Backend Issues

**Problem**: Token generation fails
- **Solution**: Install `agora-token-builder` or set `AGORA_TEMP_TOKEN` as fallback

**Problem**: Invalid App ID or Certificate
- **Solution**: Verify credentials in Agora Console

### Frontend Issues

**Problem**: Cannot connect to channel
- **Solution**: Check browser console for errors, verify token is valid

**Problem**: Video/audio not playing
- **Solution**: Check browser permissions, verify track is subscribed correctly

### PC Client Issues

**Problem**: Agora SDK not available
- **Solution**: Install Agora Python SDK with platform-specific dependencies

**Problem**: Camera/microphone not accessible
- **Solution**: Grant permissions in system settings

**Problem**: Screen sharing not working
- **Solution**: Grant screen recording permissions (macOS) or use X11 (Linux)

## Security Notes

1. **Token Security**: Tokens are generated server-side and should never be exposed to unauthorized clients
2. **App Certificate**: Keep your App Certificate secure - never commit it to version control
3. **Token Expiration**: Tokens expire after 1 hour - the system automatically generates new ones
4. **Channel Isolation**: Each PC and stream type uses a unique channel name

## Performance Considerations

1. **Concurrent Streams**: Only one stream per PC at a time
2. **Network**: Agora handles NAT traversal automatically - no TURN/STUN needed
3. **Bandwidth**: Video streams use adaptive bitrate based on network conditions
4. **Latency**: Agora provides low-latency streaming (< 400ms typically)

## Support

For Agora-specific issues:
- Agora Documentation: https://docs.agora.io/
- Agora Support: https://www.agora.io/en/support/

For application-specific issues:
- Check server logs for detailed error messages
- Verify all environment variables are set correctly
- Ensure PC client is connected via WebSocket before starting streams

