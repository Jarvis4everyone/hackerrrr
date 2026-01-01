"""
Example Client Script for PC Connection
This shows how a PC should connect to the server and execute received scripts
"""
import asyncio
import json
import os
import sys
import subprocess
import tempfile
from websockets import connect
import socket

# Server configuration
SERVER_URL = "ws://localhost:8000"
PC_ID = os.environ.get("PC_ID", socket.gethostname())


async def execute_script(script_content: str, script_name: str, server_url: str):
    """Execute a Python script received from the server"""
    print(f"[*] Executing script: {script_name}")
    
    # Create a temporary file for the script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        temp_script = f.name
    
    try:
        # Inject SERVER_URL into the script's global namespace
        script_globals = {
            '__name__': '__main__',
            '__file__': temp_script,
            'SERVER_URL': server_url
        }
        
        # Execute the script
        exec(compile(script_content, temp_script, 'exec'), script_globals)
        
        print(f"[+] Script '{script_name}' executed successfully")
        
        # Send success status back to server
        return {"type": "status", "message": f"Script '{script_name}' executed successfully"}
        
    except Exception as e:
        error_msg = f"Error executing script '{script_name}': {str(e)}"
        print(f"[!] {error_msg}")
        return {"type": "error", "message": error_msg}
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_script)
        except:
            pass


async def connect_to_server():
    """Connect to the server and handle messages"""
    uri = f"{SERVER_URL}/ws/{PC_ID}"
    
    print(f"[*] Connecting to server: {uri}")
    print(f"[*] PC ID: {PC_ID}")
    
    try:
        async with connect(uri) as websocket:
            print(f"[+] Connected to server!")
            
            # Send initial connection message
            await websocket.send(json.dumps({
                "type": "status",
                "message": f"PC {PC_ID} connected and ready"
            }))
            
            # Listen for messages
            while True:
                try:
                    # Receive message with timeout
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=30.0
                    )
                    
                    data = json.loads(message)
                    message_type = data.get("type")
                    
                    if message_type == "script":
                        # Execute the received script
                        script_name = data.get("script_name")
                        script_content = data.get("script_content")
                        server_url = data.get("server_url", SERVER_URL.replace("ws://", "http://"))
                        
                        result = await execute_script(script_content, script_name, server_url)
                        await websocket.send(json.dumps(result))
                    
                    elif message_type == "ping":
                        # Respond to ping
                        await websocket.send(json.dumps({"type": "pong"}))
                    
                    elif message_type == "connection":
                        print(f"[*] Server message: {data.get('message', '')}")
                    
                    else:
                        print(f"[*] Received message type: {message_type}")
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await websocket.send(json.dumps({
                        "type": "heartbeat",
                        "status": "ok"
                    }))
                
                except Exception as e:
                    print(f"[!] Error handling message: {e}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
    
    except Exception as e:
        print(f"[!] Connection error: {e}")
        print(f"[*] Retrying in 5 seconds...")
        await asyncio.sleep(5)
        await connect_to_server()  # Retry connection


if __name__ == "__main__":
    print("=" * 60)
    print("  Remote Script Client - Starting...")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"PC ID: {PC_ID}")
    print("=" * 60)
    
    try:
        asyncio.run(connect_to_server())
    except KeyboardInterrupt:
        print("\n[*] Client shutting down...")
        sys.exit(0)

