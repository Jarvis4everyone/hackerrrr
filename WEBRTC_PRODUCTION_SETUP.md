# WebRTC Production Setup Guide

## Problem
WebRTC works on localhost but fails in production due to:
1. **HTTPS Requirement**: Browsers require HTTPS (or localhost) for `getUserMedia()`
2. **NAT Traversal**: STUN servers alone may not be enough; TURN servers are often needed
3. **WebSocket Security**: Must use WSS (secure WebSocket) when site is served over HTTPS

## Solution Implemented

### 1. Automatic WSS/HTTPS Detection
- Frontend automatically uses `wss://` when served over HTTPS
- WebSocket URLs are constructed correctly for production

### 2. Enhanced ICE Server Configuration
- Multiple STUN servers for redundancy
- Optional TURN server support for better NAT traversal
- Configurable via environment variables

### 3. Updated Components
- All WebRTC components (Camera, Screen, Microphone) now use shared utilities
- Consistent ICE server configuration across all components

## Configuration

### Backend Environment Variables (Render Dashboard)

```bash
# Optional: TURN Server Configuration
TURN_SERVER_URL=turn:your-turn-server.com:3478?transport=udp
TURN_SERVER_USERNAME=your_username  # If required
TURN_SERVER_PASSWORD=your_password  # If required
```

### Frontend Environment Variables (Render Dashboard)

```bash
# Backend URL (required)
VITE_API_URL=https://hackerrrr-backend.onrender.com

# Optional: TURN Server (must match backend)
VITE_TURN_SERVER_URL=turn:your-turn-server.com:3478?transport=udp
VITE_TURN_SERVER_USERNAME=your_username  # If required
VITE_TURN_SERVER_PASSWORD=your_password  # If required
```

## Free TURN Server Options

### Option 1: Use Public STUN Servers (Current Default)
- Works for most cases
- No configuration needed
- May fail behind strict NATs/firewalls

### Option 2: Free TURN Servers
1. **Xirsys** (Free tier available): https://xirsys.com
2. **Twilio STUN/TURN** (Free tier): https://www.twilio.com/stun-turn
3. **Metered TURN** (Free tier): https://www.metered.ca/tools/openrelay/

### Option 3: Self-Hosted TURN Server
Use `coturn` (open-source TURN server):
```bash
# Install coturn
sudo apt-get install coturn

# Configure /etc/turnserver.conf
listening-port=3478
realm=your-domain.com
user=username:password

# Start service
sudo systemctl start coturn
```

## Testing

1. **Check HTTPS**: Ensure your frontend is served over HTTPS
2. **Check WebSocket**: Open browser console, verify WebSocket uses `wss://`
3. **Check ICE Servers**: In browser console, check `RTCPeerConnection` configuration
4. **Monitor Connection**: Watch browser console for WebRTC connection state changes

## Troubleshooting

### Issue: "getUserMedia() is not allowed"
- **Solution**: Ensure site is served over HTTPS (or localhost)

### Issue: Connection fails with "ICE connection failed"
- **Solution**: Add TURN server configuration
- **Check**: Firewall/NAT settings may be blocking direct connections

### Issue: WebSocket connection fails
- **Solution**: Ensure WebSocket URL uses `wss://` in production
- **Check**: Backend must support WSS (Render handles this automatically)

### Issue: "No video/audio track received"
- **Solution**: Check PC client is connected and streaming
- **Check**: Browser console for WebRTC errors
- **Check**: Network tab for WebSocket messages

## Next Steps

1. Deploy updated code to Render
2. Set environment variables in Render dashboard
3. Test WebRTC connections
4. If issues persist, add TURN server configuration

## Additional Resources

- WebRTC Best Practices: https://webrtc.org/getting-started/testing
- TURN Server Setup: https://github.com/coturn/coturn
- NAT Traversal Guide: https://webrtc.org/getting-started/peer-connections-overview

