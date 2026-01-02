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

### 1. Using the Web-Based PC Client

The PC client uses **Agora Web SDK** (JavaScript) which runs in any modern web browser. This is much simpler than the Python SDK - no native dependencies or complex installation required!

#### Quick Start

1. **Open the PC Client:**
   - Open `pc_client_agora.html` in any modern web browser (Chrome, Firefox, Edge, Safari)
   - Or serve it via a local web server

2. **Configure Connection:**
   - Enter your server URL (e.g., `ws://localhost:8000` or `wss://your-server.com`)
   - Enter your PC ID (or leave blank to use hostname)
   - Click "Connect"

3. **That's it!** The client will:
   - Connect to the server via WebSocket
   - Automatically handle Agora streaming when requested
   - Display connection status and logs

#### Serving the Client

**Option 1: Direct File Open**
- Simply double-click `pc_client_agora.html` to open in your default browser
- Works for local development (localhost server)

**Option 2: Local Web Server (Recommended for Production)**
```bash
# Using Python
python -m http.server 8080

# Using Node.js
npx http-server -p 8080

# Then open: http://localhost:8080/pc_client_agora.html
```

**Option 3: Deploy to Web Server**
- Upload `pc_client_agora.html` to any web server
- Access via URL: `https://your-domain.com/pc_client_agora.html`

#### Browser Requirements

- **Chrome/Edge**: Full support (recommended)
- **Firefox**: Full support
- **Safari**: Full support (macOS/iOS)
- **Opera**: Full support

**Required Permissions:**
- Camera access (for camera streaming)
- Microphone access (for microphone streaming)
- Screen sharing permissions (for screen streaming)

The browser will prompt for these permissions when you start a stream.

### 2. How It Works

1. **WebSocket Connection**: Client connects to server via WebSocket
2. **Agora Web SDK**: Uses Agora Web SDK (loaded from CDN) for streaming
3. **Automatic Handling**: When server sends `start_stream` message with Agora config, client:
   - Joins Agora channel
   - Creates and publishes appropriate media tracks (camera/microphone/screen)
   - Sends confirmation back to server

### 3. Platform-Specific Notes

#### Windows
- Camera: Browser automatically detects available cameras
- Microphone: Browser uses default audio input device
- Screen: Browser handles screen sharing (Chrome/Edge recommended)

#### Linux
- Camera: Browser accesses `/dev/video0`, `/dev/video1`, etc.
- Microphone: Browser uses default PulseAudio device
- Screen: Browser handles screen sharing (may require X11)

#### macOS
- Camera/Microphone: Browser requests permissions automatically
- Screen: Browser handles screen sharing (requires screen recording permission in System Preferences)

### 4. Troubleshooting

**Problem: Cannot access camera/microphone**
- **Solution**: Grant permissions in browser settings
  - Chrome: Settings > Privacy and Security > Site Settings > Camera/Microphone
  - Firefox: Preferences > Privacy & Security > Permissions
  - Safari: System Preferences > Security & Privacy > Camera/Microphone

**Problem: Screen sharing not working**
- **Solution**: 
  - Chrome/Edge: Click the screen share button and select screen/window
  - Firefox: Grant screen sharing permission
  - macOS: Grant screen recording permission in System Preferences

**Problem: WebSocket connection fails**
- **Solution**: 
  - Check server URL is correct
  - For `wss://`, ensure server has valid SSL certificate
  - Check firewall/network settings

**Problem: Agora SDK not loading**
- **Solution**: 
  - Check internet connection (SDK loads from CDN)
  - Verify browser console for errors
  - Try using a different browser

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

**Problem**: Browser cannot access camera/microphone
- **Solution**: 
  - Grant permissions in browser settings
  - Chrome: Settings > Privacy and Security > Site Settings > Camera/Microphone
  - Firefox: Preferences > Privacy & Security > Permissions
  - Ensure the page is served over HTTPS or localhost (required for camera/mic access)

**Problem**: Screen sharing not working
- **Solution**: 
  - Grant screen sharing permission when browser prompts
  - macOS: Also grant screen recording permission in System Preferences > Security & Privacy
  - Use Chrome/Edge for best screen sharing support

**Problem**: WebSocket connection fails
- **Solution**: 
  - Verify server URL is correct (use `ws://` for HTTP, `wss://` for HTTPS)
  - Check browser console for connection errors
  - Ensure server is running and accessible

**Problem**: Agora SDK not loading
- **Solution**: 
  - Check internet connection (SDK loads from CDN)
  - Verify browser console for script loading errors
  - Try refreshing the page or clearing browser cache

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

