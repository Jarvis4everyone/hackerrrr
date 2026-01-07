# 🔌 PC Client Connection Management - Developer Guide

## Overview

This guide explains how the PC client should handle WebSocket connections, reconnections, and maintain a robust connection to the server.

## Connection Architecture

The PC client uses a **single persistent WebSocket connection** (`/ws/{pc_id}`) for all communication:
- Script execution
- Terminal sessions
- File downloads
- Status updates
- Heartbeats

## Connection Lifecycle

### 1. Initial Connection

**When:** PC client starts

**Steps:**
1. Connect to WebSocket: `wss://server.com/ws/{pc_id}`
2. Wait for connection message from server
3. Send `pc_info` message immediately
4. Start heartbeat loop
5. Start message listener

**Example:**
```python
import asyncio
import websockets
import json
import logging

logger = logging.getLogger(__name__)

async def connect_to_server(server_url: str, pc_id: str):
    """Connect to server WebSocket"""
    ws_url = server_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_uri = f"{ws_url}/ws/{pc_id}"
    
    logger.info(f"Connecting to {ws_uri}...")
    
    try:
        async with websockets.connect(ws_uri) as websocket:
            logger.info(f"✓ Connected as {pc_id}")
            
            # Wait for connection message
            connection_msg = await websocket.recv()
            logger.info(f"Connection message: {json.loads(connection_msg)}")
            
            # Send PC info immediately
            await send_pc_info(websocket, pc_id)
            
            # Start heartbeat and message listener
            await asyncio.gather(
                heartbeat_loop(websocket),
                message_listener(websocket, pc_id)
            )
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise
```

### 2. Reconnection Logic

**Critical:** PC client **MUST** implement automatic reconnection.

**When to Reconnect:**
- WebSocket connection is closed
- Connection timeout
- Network error
- Server restart

**Reconnection Strategy:**
- **Exponential backoff**: Start with 1 second, double each retry (max 60 seconds)
- **Infinite retries**: Keep trying until connection is established
- **Immediate retry on disconnect**: Don't wait if connection drops

**Example:**
```python
async def connect_with_reconnect(server_url: str, pc_id: str):
    """Connect with automatic reconnection"""
    retry_delay = 1  # Start with 1 second
    max_delay = 60   # Max 60 seconds
    
    while True:
        try:
            await connect_to_server(server_url, pc_id)
            # If we get here, connection was successful
            retry_delay = 1  # Reset delay on success
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            logger.info(f"Reconnecting in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            
            # Exponential backoff
            retry_delay = min(retry_delay * 2, max_delay)
```

### 3. Heartbeat

**Purpose:** Keep connection alive and inform server that PC is online

**Frequency:** Every 15-30 seconds

**Message Format:**
```json
{
  "type": "heartbeat",
  "status": "ok"
}
```

**Example:**
```python
async def heartbeat_loop(websocket):
    """Send heartbeat every 15 seconds"""
    while True:
        try:
            await asyncio.sleep(15)
            await websocket.send(json.dumps({
                "type": "heartbeat",
                "status": "ok"
            }))
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            break  # Exit loop, will trigger reconnection
```

### 4. PC Info Message

**When to Send:**
- Immediately after connection
- Every 60 seconds (periodic update)
- When IP address changes
- When hostname changes

**Message Format:**
```json
{
  "type": "pc_info",
  "ip_address": "192.168.1.40",
  "hostname": "ShreshthKaushik",
  "name": "ShreshthKaushik",
  "os_info": {
    "platform": "Windows",
    "version": "10.0.26100",
    "architecture": "AMD64"
  },
  "metadata": {
    "processor": "Intel64 Family 6 Model 170 Stepping 4"
  }
}
```

**Example:**
```python
async def send_pc_info(websocket, pc_id: str):
    """Send PC information to server"""
    import platform
    import socket
    
    # Detect IP address
    ip_address = detect_ip_address()
    
    # Get hostname
    hostname = platform.node()
    
    # Get OS info
    os_info = {
        "platform": platform.system(),
        "version": platform.version(),
        "architecture": platform.machine()
    }
    
    # Get metadata
    metadata = {
        "processor": platform.processor()
    }
    
    message = {
        "type": "pc_info",
        "ip_address": ip_address,
        "hostname": hostname,
        "name": pc_id,
        "os_info": os_info,
        "metadata": metadata
    }
    
    await websocket.send(json.dumps(message))
    logger.info(f"Sending PC info - Detected IP: {ip_address}")

def detect_ip_address() -> str:
    """Detect local IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "unknown"
```

## Message Handling

### Receiving Messages

**Always listen for messages from server:**

```python
async def message_listener(websocket, pc_id: str):
    """Listen for messages from server"""
    try:
        async for message in websocket:
            data = json.loads(message)
            await handle_message(websocket, pc_id, data)
    except websockets.exceptions.ConnectionClosed:
        logger.warning("WebSocket connection closed")
        raise  # Will trigger reconnection
    except Exception as e:
        logger.error(f"Message listener error: {e}")
        raise

async def handle_message(websocket, pc_id: str, message: dict):
    """Handle incoming messages"""
    message_type = message.get("type")
    
    if message_type == "connection":
        logger.info(f"Connection message: {message.get('message')}")
    
    elif message_type == "script":
        await handle_script_message(websocket, message)
    
    elif message_type == "start_terminal":
        await handle_start_terminal(websocket, message)
    
    elif message_type == "ping":
        # Respond to ping
        await websocket.send(json.dumps({"type": "pong"}))
    
    # ... handle other message types
```

## Best Practices

### 1. Always Reconnect
- **Never give up**: Keep trying to reconnect forever
- **Handle all exceptions**: Catch all connection errors
- **Log reconnection attempts**: Help with debugging

### 2. Send PC Info Frequently
- **Immediately after connection**: Send within 1 second
- **Periodically**: Every 60 seconds
- **On changes**: When IP or hostname changes

### 3. Maintain Heartbeat
- **Regular intervals**: Every 15-30 seconds
- **Handle failures**: If heartbeat fails, reconnect
- **Don't skip**: Always send heartbeat, even during script execution

### 4. Handle Disconnections Gracefully
- **Clean up resources**: Stop scripts, close files
- **Save state**: Save any important state before reconnecting
- **Resume operations**: After reconnection, resume normal operations

### 5. Error Handling
- **Log all errors**: Help with debugging
- **Don't crash**: Catch all exceptions
- **Retry operations**: Retry failed operations after reconnection

## Complete Implementation Example

```python
import asyncio
import websockets
import json
import logging
import platform
import socket
from typing import Optional

logger = logging.getLogger(__name__)

class PCClient:
    """PC Client with robust connection management"""
    
    def __init__(self, server_url: str, pc_id: str):
        self.server_url = server_url
        self.pc_id = pc_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.retry_delay = 1
        self.max_retry_delay = 60
    
    async def connect(self):
        """Connect to server with automatic reconnection"""
        while True:
            try:
                await self._connect_once()
                # If we get here, connection was successful
                self.retry_delay = 1  # Reset delay
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                logger.info(f"Reconnecting in {self.retry_delay} seconds...")
                await asyncio.sleep(self.retry_delay)
                self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
    
    async def _connect_once(self):
        """Connect to server once"""
        ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_uri = f"{ws_url}/ws/{self.pc_id}"
        
        logger.info(f"Connecting to {ws_uri}...")
        
        self.websocket = await websockets.connect(ws_uri)
        self.running = True
        
        logger.info(f"✓ Connected as {self.pc_id}")
        
        # Wait for connection message
        connection_msg = await self.websocket.recv()
        logger.info(f"Connection message: {json.loads(connection_msg)}")
        
        # Send PC info immediately
        await self.send_pc_info()
        
        # Start background tasks
        await asyncio.gather(
            self.heartbeat_loop(),
            self.message_listener(),
            self.pc_info_loop()
        )
    
    async def heartbeat_loop(self):
        """Send heartbeat every 15 seconds"""
        while self.running:
            try:
                await asyncio.sleep(15)
                if self.websocket:
                    await self.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "status": "ok"
                    }))
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                self.running = False
                break
    
    async def pc_info_loop(self):
        """Send PC info every 60 seconds"""
        while self.running:
            try:
                await asyncio.sleep(60)
                if self.websocket:
                    await self.send_pc_info()
            except Exception as e:
                logger.error(f"PC info loop error: {e}")
                self.running = False
                break
    
    async def message_listener(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.running = False
            raise
        except Exception as e:
            logger.error(f"Message listener error: {e}")
            self.running = False
            raise
    
    async def send_pc_info(self):
        """Send PC information to server"""
        ip_address = self.detect_ip_address()
        hostname = platform.node()
        
        message = {
            "type": "pc_info",
            "ip_address": ip_address,
            "hostname": hostname,
            "name": self.pc_id,
            "os_info": {
                "platform": platform.system(),
                "version": platform.version(),
                "architecture": platform.machine()
            },
            "metadata": {
                "processor": platform.processor()
            }
        }
        
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sending PC info - Detected IP: {ip_address}")
    
    def detect_ip_address(self) -> str:
        """Detect local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    async def handle_message(self, message: dict):
        """Handle incoming messages"""
        message_type = message.get("type")
        
        if message_type == "script":
            await self.handle_script(message)
        elif message_type == "start_terminal":
            await self.handle_start_terminal(message)
        # ... handle other message types
    
    async def handle_script(self, message: dict):
        """Handle script execution message"""
        # Implement script execution
        pass
    
    async def handle_start_terminal(self, message: dict):
        """Handle terminal start message"""
        # Implement terminal handling
        pass


# Usage
async def main():
    client = PCClient(
        server_url="wss://hackerrrr-backend.onrender.com",
        pc_id="ShreshthKaushik"
    )
    await client.connect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Connection Keeps Dropping
- **Check network**: Ensure stable internet connection
- **Check firewall**: Ensure WebSocket ports are open
- **Check server**: Verify server is running and accessible
- **Increase timeout**: Increase WebSocket timeout if needed

### PC Shows as Offline
- **Send PC info**: Ensure `pc_info` is sent immediately after connection
- **Send heartbeat**: Ensure heartbeat is sent regularly
- **Check logs**: Verify messages are being sent successfully

### Reconnection Not Working
- **Check exception handling**: Ensure all exceptions are caught
- **Check retry logic**: Verify retry loop is working
- **Check logs**: Look for reconnection attempts in logs

## Security Considerations

1. **Authentication**: Server may require authentication (future feature)
2. **TLS/SSL**: Always use `wss://` for secure connections
3. **Validation**: Validate all messages from server
4. **Rate Limiting**: Don't send messages too frequently

## Support

For issues or questions:
- Check server logs for error messages
- Verify WebSocket connection is stable
- Test with simple connection first
- Check network connectivity

---

**Last Updated:** 2026-01-07  
**Version:** 1.0

