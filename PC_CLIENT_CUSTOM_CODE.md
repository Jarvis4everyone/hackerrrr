# PC Client Custom Code Execution & Connection Management Documentation

## Overview

This document provides comprehensive guidance for PC client developers on implementing:
1. **Custom Code Execution** - Running arbitrary Python code sent from the server
2. **Connection Management** - Ensuring the server recognizes the PC as connected
3. **Heartbeat System** - Maintaining connection status through regular heartbeats
4. **Logging Fixes** - Preventing logging errors during script execution

## Table of Contents

1. [Connection Management](#connection-management)
2. [Custom Code Execution](#custom-code-execution)
3. [Message Types](#message-types)
4. [Implementation Guide](#implementation-guide)
5. [Logging Fixes](#logging-fixes) ⚠️ **CRITICAL**
6. [Troubleshooting](#troubleshooting)

---

## Connection Management

### Critical: PC ID vs MongoDB ObjectId

**IMPORTANT**: The server uses **`pc_id`** (the PC identifier, e.g., "ShreshthKaushik") to identify PCs, NOT the MongoDB `_id` (ObjectId like "6956efe211c9b833c46f31bd").

- ✅ **Correct**: Use `pc_id` = "ShreshthKaushik" (hostname or custom ID)
- ❌ **Wrong**: Use MongoDB `_id` = "6956efe211c9b833c46f31bd"

### Connection Status Requirements

For the server to recognize your PC as connected, you **MUST**:

1. **Connect via WebSocket** using your `pc_id`:
   ```python
   # Connect to: wss://server.com/ws/{pc_id}
   # Example: wss://hackerrrr-backend.onrender.com/ws/ShreshthKaushik
   ```

2. **Send `pc_info` message immediately after connection**:
   ```python
   await websocket.send_json({
       "type": "pc_info",
       "hostname": "ShreshthKaushik",  # Your PC's hostname
       "name": "ShreshthKaushik",      # Display name
       "ip_address": "192.168.1.53",  # Your PC's IP address
       "metadata": {
           "processor": "Intel Core i7",
           # ... other hardware info
       }
   })
   ```

3. **Send heartbeats every 5 seconds**:
   ```python
   # In a background task:
   while True:
       await asyncio.sleep(5)  # Every 5 seconds
       await websocket.send_json({
           "type": "heartbeat"
       })
   ```

### Heartbeat System

The heartbeat system is **CRITICAL** for maintaining connection status:

- **Frequency**: Send a heartbeat every **5 seconds**
- **Message Format**:
  ```json
  {
    "type": "heartbeat"
  }
  ```
- **Purpose**: 
  - Updates `last_seen` timestamp in database
  - Keeps `connected` status as `true`
  - Allows server to detect if PC goes offline

**Implementation Example**:
```python
async def send_heartbeat_loop(self):
    """Background task to send heartbeats every 5 seconds"""
    while self.running:
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.send_json({"type": "heartbeat"})
                logger.debug("Heartbeat sent")
            else:
                logger.warning("Cannot send heartbeat - WebSocket not connected")
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
        
        await asyncio.sleep(5)  # Wait 5 seconds before next heartbeat
```

### PC Info Message

The `pc_info` message should be sent:
1. **Immediately after WebSocket connection** is established
2. **Whenever PC information changes** (IP address, hostname, etc.)

**Complete PC Info Message Example**:
```python
async def send_pc_info(self):
    """Send PC information to server"""
    import socket
    import platform
    
    # Detect IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except:
        ip_address = "unknown"
    
    # Get hostname
    hostname = socket.gethostname()
    
    # Prepare metadata
    metadata = {
        "processor": platform.processor(),
        "platform": platform.system(),
        "python_version": platform.python_version()
    }
    
    # Send pc_info message
    await self.websocket.send_json({
        "type": "pc_info",
        "hostname": hostname,
        "name": hostname,  # Or use a custom name
        "ip_address": ip_address,
        "os_info": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version()
        },
        "metadata": metadata
    })
    
    logger.info(f"Sent PC info: hostname={hostname}, ip={ip_address}")
```

### Connection Status Verification

To verify your PC is recognized as connected:

1. **Check server logs** - Look for:
   ```
   [+] PC connected: ShreshthKaushik
   [ShreshthKaushik] PC info updated: connected: True
   ```

2. **Check database** - The server updates `connected: true` when:
   - WebSocket connection is established
   - `pc_info` message is received
   - `heartbeat` message is received

3. **Common Issues**:
   - ❌ **PC not recognized**: Not sending `pc_info` or heartbeats
   - ❌ **Wrong PC ID**: Using MongoDB `_id` instead of `pc_id`
   - ❌ **Connection lost**: WebSocket closed but heartbeats still being sent

---

## Custom Code Execution

### Message Format

When the server sends custom code for execution, the PC client receives a WebSocket message:

```json
{
  "type": "custom_code",
  "code": "print('Hello World')\nimport sys\nprint(f'Python: {sys.version}')",
  "requirements": "pip install pyqt5",
  "server_url": "http://0.0.0.0:8000",
  "execution_id": "execution-uuid-here"
}
```

### Message Fields

- **`type`** (required): Must be `"custom_code"`
- **`code`** (required): Python code to execute (as a string)
- **`requirements`** (optional): pip install commands
  - Single: `"pip install pyqt5"`
  - Multiple: `"pip install pyqt5\npip install requests"`
- **`server_url`** (required): HTTP URL of the server
- **`execution_id`** (required): Unique identifier for this execution

---

## Implementation Guide

### Step 1: Handle the Message Type

Add a case for `custom_code` in your message handler:

```python
async def handle_message(self, message: dict):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "custom_code":
        await self.handle_custom_code(message)
    elif message_type == "script":
        await self.handle_script(message)
    elif message_type == "heartbeat":
        # Server response to heartbeat - no action needed
        pass
    # ... other message types
```

### Step 2: Implement Custom Code Handler

```python
async def handle_custom_code(self, message: dict):
    """Handle custom code execution request"""
    import subprocess
    import sys
    import tempfile
    import os
    from io import StringIO
    
    code = message.get("code", "")
    requirements = message.get("requirements", "")
    server_url = message.get("server_url", "")
    execution_id = message.get("execution_id", "")
    
    if not code:
        logger.error("No code provided in custom_code message")
        return
    
    logger.info(f"[Custom Code] Starting execution (ID: {execution_id})")
    
    # Step 1: Install requirements if provided
    if requirements and requirements.strip():
        logger.info(f"[Custom Code] Installing requirements: {requirements}")
        try:
            req_lines = [line.strip() for line in requirements.strip().split('\n') if line.strip()]
            
            for req_line in req_lines:
                if req_line.startswith('pip install'):
                    cmd = req_line.split()
                    if len(cmd) >= 3:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        if result.returncode == 0:
                            logger.info(f"[Custom Code] Successfully installed: {req_line}")
                        else:
                            logger.warning(f"[Custom Code] Installation warning: {result.stderr}")
                else:
                    logger.warning(f"[Custom Code] Skipping invalid requirement: {req_line}")
        except Exception as e:
            logger.error(f"[Custom Code] Error installing requirements: {e}")
            # Continue with execution even if requirements fail
    
    # Step 2: Execute the code
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_script = f.name
        
        # Capture stdout and stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Set environment variables
            os.environ['SERVER_URL'] = server_url
            os.environ['PC_ID'] = self.pc_id  # Your PC ID
            os.environ['EXECUTION_ID'] = execution_id
            
            # Execute the code
            script_globals = {
                '__name__': '__main__',
                '__file__': temp_script,
                'SERVER_URL': server_url
            }
            
            exec(compile(code, temp_script, 'exec'), script_globals)
            
            # Get captured output
            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()
            
            logger.info(f"[Custom Code] Execution completed (ID: {execution_id})")
            
            # Send success message
            await self.send_message({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "success",
                "script_name": "custom_code.py",
                "output": stdout_content,
                "error": stderr_content,
                "return_code": 0
            })
            
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # Clean up temp file
            try:
                os.unlink(temp_script)
            except:
                pass
                
    except Exception as e:
        error_msg = str(e)
        import traceback
        error_traceback = traceback.format_exc()
        
        logger.error(f"[Custom Code] Execution failed (ID: {execution_id}): {error_msg}")
        
        # Send error message
        await self.send_message({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "error",
            "script_name": "custom_code.py",
            "error": f"{error_msg}\n\n{error_traceback}",
            "return_code": -1
        })
```

### Step 3: Complete Connection Setup

Ensure your PC client:

1. **Connects with correct PC ID**:
   ```python
   # Use hostname or custom PC ID
   self.pc_id = socket.gethostname()  # e.g., "ShreshthKaushik"
   uri = f"wss://{server_url}/ws/{self.pc_id}"
   ```

2. **Sends pc_info immediately after connection**:
   ```python
   async def on_connect(self):
       """Called when WebSocket connection is established"""
       await self.send_pc_info()  # Send immediately
       await self.start_heartbeat_loop()  # Start heartbeat background task
   ```

3. **Maintains heartbeat loop**:
   ```python
   async def start_heartbeat_loop(self):
       """Start background heartbeat task"""
       asyncio.create_task(self.send_heartbeat_loop())
   ```

---

## Logging Fixes

### ⚠️ CRITICAL: Fix Logging Errors During Script Execution

**Problem:** You may see errors like:
```
--- Logging error ---
AttributeError: 'NoneType' object has no attribute 'write'
```

This happens when logging tries to write to `stdout`/`stderr` while they're redirected during script execution.

**Solution:** See `PC_CLIENT_SCRIPT_EXECUTION_FIX.md` for complete implementation.

**Quick Fix:**
1. Use `SafeStreamHandler` for console logging (handles None streams)
2. Use file logging for background tasks
3. Disable console logging during script execution
4. Ensure scripts never redirect `stdout`/`stderr`

**See:** `PC_CLIENT_SCRIPT_EXECUTION_FIX.md` for detailed implementation.

---

## Troubleshooting

### Issue: Server says "PC not connected" but PC is online

**Symptoms**:
- PC client is running and connected
- Heartbeats are being sent every 5 seconds
- Server logs show: `PC 'ShreshthKaushik' is not connected`

**Solutions**:

1. **Verify PC ID matches**:
   - Check WebSocket URI: `wss://server/ws/ShreshthKaushik`
   - Ensure `pc_id` in messages matches WebSocket path
   - **DO NOT** use MongoDB `_id` - use `pc_id` (hostname)

2. **Verify heartbeats are being sent**:
   ```python
   # Add logging to heartbeat function
   logger.info(f"Sending heartbeat - PC ID: {self.pc_id}")
   await websocket.send_json({"type": "heartbeat"})
   ```

3. **Verify pc_info was sent**:
   - Check server logs for: `[ShreshthKaushik] PC info updated: connected: True`
   - Send `pc_info` again if connection was lost and re-established

4. **Check WebSocket connection**:
   - Ensure WebSocket is not closed
   - Handle reconnection properly
   - Re-send `pc_info` after reconnection

### Issue: Custom code execution fails

**Check**:
1. Requirements installation succeeded
2. Code syntax is valid
3. Environment variables are set
4. Output is being captured correctly

### Issue: Connection lost frequently

**Solutions**:
1. Implement automatic reconnection
2. Re-send `pc_info` after reconnection
3. Restart heartbeat loop after reconnection
4. Handle WebSocket errors gracefully

---

## Complete Example

```python
import asyncio
import websockets
import json
import socket
import platform
import logging

logger = logging.getLogger(__name__)

class PCClient:
    def __init__(self, server_url: str, pc_id: str):
        self.server_url = server_url
        self.pc_id = pc_id  # Use hostname or custom ID
        self.websocket = None
        self.running = False
    
    async def connect(self):
        """Connect to server and maintain connection"""
        uri = f"wss://{self.server_url}/ws/{self.pc_id}"
        
        while True:
            try:
                logger.info(f"Connecting to {uri}...")
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    self.running = True
                    
                    # Send PC info immediately
                    await self.send_pc_info()
                    
                    # Start heartbeat loop
                    heartbeat_task = asyncio.create_task(self.send_heartbeat_loop())
                    
                    # Listen for messages
                    async for message in websocket:
                        data = json.loads(message)
                        await self.handle_message(data)
                        
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.running = False
                await asyncio.sleep(5)  # Wait before reconnecting
    
    async def send_pc_info(self):
        """Send PC information to server"""
        # ... (implementation from above)
        pass
    
    async def send_heartbeat_loop(self):
        """Send heartbeats every 5 seconds"""
        while self.running:
            try:
                if self.websocket and not self.websocket.closed:
                    await self.websocket.send(json.dumps({"type": "heartbeat"}))
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def handle_message(self, message: dict):
        """Handle incoming messages"""
        message_type = message.get("type")
        
        if message_type == "custom_code":
            await self.handle_custom_code(message)
        # ... other handlers
    
    async def handle_custom_code(self, message: dict):
        """Handle custom code execution"""
        # ... (implementation from above)
        pass

# Usage
if __name__ == "__main__":
    pc_id = socket.gethostname()  # Use hostname as PC ID
    client = PCClient("hackerrrr-backend.onrender.com", pc_id)
    asyncio.run(client.connect())
```

---

## Integration Checklist

### Connection Management
- [ ] WebSocket connects using `pc_id` (hostname), not MongoDB `_id`
- [ ] `pc_info` message sent immediately after connection
- [ ] Heartbeat sent every 5 seconds
- [ ] Reconnection logic implemented
- [ ] `pc_info` re-sent after reconnection

### Custom Code Execution
- [ ] `custom_code` message type handler implemented
- [ ] Requirements installation (pip install) works
- [ ] Code execution with output capture
- [ ] Execution results sent back to server
- [ ] Error handling implemented
- [ ] Environment variables set (SERVER_URL, PC_ID, EXECUTION_ID)

### Testing
- [ ] PC appears as "connected" on server
- [ ] Heartbeats update `last_seen` timestamp
- [ ] Custom code execution works
- [ ] Requirements installation works
- [ ] Error handling works correctly

---

## Notes

- **PC ID**: Always use `pc_id` (hostname or custom identifier), never MongoDB `_id`
- **Heartbeats**: Critical for maintaining connection status - send every 5 seconds
- **pc_info**: Must be sent immediately after connection and after reconnection
- **Connection Status**: Server checks both WebSocket state and database `connected` field
- **Reconnection**: Always re-send `pc_info` after reconnecting
