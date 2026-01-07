# 📜 PC Client Script Execution - Developer Guide

## Overview

This guide explains how the PC client handles script execution requests from the server. The PC client receives scripts via WebSocket, executes them, and sends logs/results back to the server.

## Architecture

The script execution flow uses the **main WebSocket connection** (`/ws/{pc_id}`):

```
Server → WebSocket → PC Client → Execute Script → Send Logs → Server → MongoDB
```

## Message Flow

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Server    │         │   Server     │         │  PC Client  │
│  (Frontend) │         │  (Backend)   │         │             │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. POST /api/scripts/send                      │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 2. script message      │
       │                       │───────────────────────>│
       │                       │                        │
       │                       │ 3. log messages       │
       │                       │<───────────────────────│
       │                       │                        │
       │                       │ 4. execution_complete  │
       │                       │<───────────────────────│
       │                       │                        │
       │ 5. Status updated     │                        │
       │<──────────────────────│                        │
```

## Messages PC Client Receives

### 1. `script` Message

**When:** Server wants to execute a script on the PC

**Message Format:**
```json
{
  "type": "script",
  "script_name": "wifi_passwords.py",
  "script_content": "# Script content here...",
  "server_url": "http://localhost:8000/",
  "execution_id": "695e54828e46bf7a69f2c826",
  "script_params": {
    "PARAM_NAME": "value"
  }
}
```

**Fields:**
- `type`: Always `"script"`
- `script_name`: Name of the script file (e.g., `"wifi_passwords.py"`)
- `script_content`: Full content of the script to execute
- `server_url`: Base URL of the server (for script to send results/logs)
- `execution_id`: Unique ID for this execution (used for tracking)
- `script_params`: Optional dictionary of parameters to pass to script

**PC Client Action:**
1. Store the `execution_id` for this execution
2. Save the script content to a temporary file or execute directly
3. Set environment variables for the script:
   - `SERVER_URL`: The server URL
   - `PC_ID`: The PC's ID
   - `EXECUTION_ID`: The execution ID
   - Any parameters from `script_params` as environment variables
4. Execute the script using the appropriate Python interpreter
5. Capture stdout, stderr, and return code
6. Send logs to server during execution (if script supports it)
7. Send `execution_complete` message when done

## Messages PC Client Sends

### 1. `log` Message

**When:** Script produces output or logs

**Message Format:**
```json
{
  "type": "log",
  "execution_id": "695e54828e46bf7a69f2c826",
  "log_content": "Script output or log message",
  "log_level": "INFO",
  "log_file_path": "c:\\path\\to\\log\\file.log"
}
```

**Fields:**
- `type`: Always `"log"`
- `execution_id`: The execution ID received in the script message
- `log_content`: The log message or script output
- `log_level`: Log level (`"INFO"`, `"ERROR"`, `"WARNING"`, `"SUCCESS"`, `"DEBUG"`)
- `log_file_path`: Path to the log file (optional, but recommended)

**When to Send:**
- **During execution**: Send logs as the script produces output
- **After execution**: Send final logs, including any error messages
- **On errors**: Send error logs with `log_level: "ERROR"`

**Example:**
```python
# During script execution
await websocket.send_json({
    "type": "log",
    "execution_id": execution_id,
    "log_content": "Script started executing...",
    "log_level": "INFO",
    "log_file_path": log_file_path
})

# On error
await websocket.send_json({
    "type": "log",
    "execution_id": execution_id,
    "log_content": f"Error: {str(e)}",
    "log_level": "ERROR",
    "log_file_path": log_file_path
})
```

### 2. `execution_complete` Message

**When:** Script execution finishes (success or failure)

**Message Format:**
```json
{
  "type": "execution_complete",
  "execution_id": "695e54828e46bf7a69f2c826",
  "status": "success",
  "result": {
    "message": "Script executed successfully",
    "return_code": 0
  }
}
```

**Fields:**
- `type`: Always `"execution_complete"`
- `execution_id`: The execution ID received in the script message
- `status`: Execution status (`"success"` or `"failed"`)
- `result`: Optional result object with:
  - `message`: Human-readable message
  - `return_code`: Process return code (0 = success, non-zero = failure)
  - `data`: Optional additional data

**Example (Success):**
```json
{
  "type": "execution_complete",
  "execution_id": "695e54828e46bf7a69f2c826",
  "status": "success",
  "result": {
    "message": "Script executed successfully",
    "return_code": 0
  }
}
```

**Example (Failure):**
```json
{
  "type": "execution_complete",
  "execution_id": "695e54828e46bf7a69f2c826",
  "status": "failed",
  "result": {
    "message": "Script execution failed",
    "return_code": 1,
    "error": "Error details here"
  }
}
```

### 3. `error` Message

**When:** PC client encounters an error before or during script execution

**Message Format:**
```json
{
  "type": "error",
  "execution_id": "695e54828e46bf7a69f2c826",
  "message": "Error message here"
}
```

**When to Send:**
- Script file cannot be created
- Python interpreter not found
- Script execution fails to start
- Critical errors during execution

## Complete Implementation Example

```python
import subprocess
import os
import tempfile
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class ScriptExecutor:
    """Handles script execution"""
    
    def __init__(self, pc_id: str, base_path: str, python_path: str):
        self.pc_id = pc_id
        self.base_path = Path(base_path)
        self.python_path = python_path
        self.logs_dir = self.base_path / "logs"
        self.logs_dir.mkdir(exist_ok=True)
    
    async def execute_script(self, websocket, message: dict):
        """Execute a script received from server"""
        script_name = message.get("script_name")
        script_content = message.get("script_content")
        server_url = message.get("server_url", "")
        execution_id = message.get("execution_id")
        script_params = message.get("script_params", {})
        
        if not execution_id:
            logger.error("No execution_id in script message")
            return
        
        logger.info(f"Received script: {script_name}, execution_id: {execution_id}")
        
        # Create log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{script_name.replace('.py', '')}_{timestamp}_{execution_id[:8]}.log"
        log_file_path = self.logs_dir / log_filename
        
        try:
            # Save script to temporary file
            script_file = self.base_path / script_name
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Set up environment variables
            env = os.environ.copy()
            env["SERVER_URL"] = server_url
            env["PC_ID"] = self.pc_id
            env["EXECUTION_ID"] = execution_id
            
            # Add script parameters as environment variables
            for key, value in script_params.items():
                env[key] = str(value)
            
            # Send initial log
            await self.send_log(websocket, execution_id, 
                              f"[*] Executing script: {script_name}",
                              "INFO", log_file_path)
            
            # Execute script
            process = subprocess.Popen(
                [self.python_path, str(script_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=str(self.base_path),
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            with open(log_file_path, 'w', encoding='utf-8') as log_file:
                log_file.write(f"[*] Executing script: {script_name}\n")
                log_file.write(f"[*] Execution ID: {execution_id}\n")
                log_file.write(f"[*] Server URL: {server_url}\n")
                log_file.write("=" * 60 + "\n\n")
                
                # Read output line by line
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    
                    if line:
                        # Write to log file
                        log_file.write(line)
                        log_file.flush()
                        
                        # Send log to server
                        await self.send_log(websocket, execution_id, 
                                          line.rstrip(), "INFO", log_file_path)
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Send final log with complete log file
            if log_file_path.exists():
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    complete_log = f.read()
                    await self.send_log(websocket, execution_id, 
                                      complete_log, "INFO", log_file_path)
            
            # Send execution complete
            if return_code == 0:
                await websocket.send_json({
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "status": "success",
                    "result": {
                        "message": f"Script '{script_name}' executed successfully",
                        "return_code": return_code
                    }
                })
            else:
                await websocket.send_json({
                    "type": "execution_complete",
                    "execution_id": execution_id,
                    "status": "failed",
                    "result": {
                        "message": f"Script '{script_name}' failed with return code {return_code}",
                        "return_code": return_code
                    }
                })
            
            # Clean up script file (optional)
            # script_file.unlink()
            
        except Exception as e:
            logger.error(f"Error executing script: {e}", exc_info=True)
            
            # Send error log
            error_msg = f"Error executing script: {str(e)}"
            await self.send_log(websocket, execution_id, error_msg, "ERROR", log_file_path)
            
            # Send execution complete with error
            await websocket.send_json({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "failed",
                "result": {
                    "message": error_msg,
                    "return_code": -1,
                    "error": str(e)
                }
            })
            
            # Send error message
            await websocket.send_json({
                "type": "error",
                "execution_id": execution_id,
                "message": error_msg
            })
    
    async def send_log(self, websocket, execution_id: str, log_content: str, 
                      log_level: str, log_file_path: Path):
        """Send log message to server"""
        try:
            await websocket.send_json({
                "type": "log",
                "execution_id": execution_id,
                "log_content": log_content,
                "log_level": log_level,
                "log_file_path": str(log_file_path)
            })
        except Exception as e:
            logger.error(f"Error sending log: {e}")


# Usage in WebSocket handler
script_executor = ScriptExecutor(
    pc_id="ShreshthKaushik",
    base_path="c:\\Users\\shres\\Desktop\\Hacking\\PC",
    python_path="C:\\Users\\shres\\Desktop\\Hacking\\PC\\.venv\\Scripts\\python.exe"
)

async def handle_websocket_message(websocket, pc_id: str, message: dict):
    """Handle WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "script":
        await script_executor.execute_script(websocket, message)
    
    # ... handle other message types
```

## Environment Variables for Scripts

The PC client sets these environment variables before executing scripts:

- `SERVER_URL`: Base URL of the server (e.g., `"http://localhost:8000/"`)
- `PC_ID`: The PC's ID (e.g., `"ShreshthKaushik"`)
- `EXECUTION_ID`: Unique execution ID for this run
- `{PARAM_NAME}`: Any parameters from `script_params` are set as environment variables

**Example Script Usage:**
```python
import os

server_url = os.getenv("SERVER_URL", "http://localhost:8000/")
pc_id = os.getenv("PC_ID")
execution_id = os.getenv("EXECUTION_ID")

# Access script parameters
param_value = os.getenv("PARAM_NAME", "default_value")

print(f"Server URL: {server_url}")
print(f"PC ID: {pc_id}")
print(f"Execution ID: {execution_id}")
```

## Log File Management

**Best Practices:**
1. **Create log files** in a dedicated `logs/` directory
2. **Use descriptive names**: `{script_name}_{timestamp}_{execution_id}.log`
3. **Include execution metadata** at the start of log file
4. **Send complete log file** at the end of execution
5. **Clean up old log files** periodically (optional)

**Log File Format:**
```
[*] Executing script: wifi_passwords.py
[*] Execution ID: 695e54828e46bf7a69f2c826
[*] Server URL: http://localhost:8000/
============================================================

[Script output here...]
```

## Error Handling

### Script Execution Errors
- **Python not found**: Send error message, don't attempt execution
- **Script syntax error**: Capture stderr, send as error log
- **Script runtime error**: Capture exception, send error log
- **Process timeout**: Kill process, send timeout error

### WebSocket Errors
- **Connection lost**: Log locally, attempt to reconnect
- **Send failed**: Retry sending logs (optional)
- **Message format error**: Log error, continue with other messages

## Best Practices

1. **Real-time Logging**: Send logs as script produces output (don't wait for completion)
2. **Complete Log Files**: Always send the complete log file at the end
3. **Error Handling**: Always send `execution_complete` even on errors
4. **Resource Cleanup**: Clean up temporary files and processes
5. **Log Levels**: Use appropriate log levels (INFO, ERROR, WARNING, SUCCESS, DEBUG)
6. **Encoding**: Use UTF-8 encoding for all text files
7. **Timeout**: Consider adding timeout for long-running scripts
8. **Process Management**: Properly manage subprocess lifecycle

## Testing

1. **Test Basic Script**: Simple Python script that prints output
2. **Test Script with Parameters**: Script that uses environment variables
3. **Test Error Handling**: Script that raises exceptions
4. **Test Long Output**: Script that produces lots of output
5. **Test Log File Creation**: Verify log files are created correctly
6. **Test WebSocket Disconnection**: What happens if connection is lost during execution

## Troubleshooting

### Script Not Executing
- Check Python interpreter path
- Verify script file is created correctly
- Check file permissions
- Verify environment variables are set

### Logs Not Appearing on Server
- Verify `execution_id` matches
- Check WebSocket connection is active
- Verify log message format is correct
- Check server logs for errors

### Execution Complete Not Received
- Always send `execution_complete` even on errors
- Verify `execution_id` is included
- Check WebSocket connection before sending

## Security Considerations

1. **Script Validation**: Consider validating script content before execution (optional)
2. **Sandboxing**: Scripts run with PC client's user permissions
3. **Path Restrictions**: Consider restricting script file locations
4. **Resource Limits**: Consider limiting memory/CPU usage
5. **Timeout**: Always set timeout for script execution

## Connection Status

**Important:** The PC client must maintain the WebSocket connection throughout script execution. If the connection is lost:

1. **During Execution**: Script may continue running, but logs won't be sent
2. **Before Execution**: Script won't be received
3. **After Execution**: Results won't be sent

**Best Practice:** Implement reconnection logic and retry sending logs if connection is restored.

## Support

For issues or questions:
- Check server logs for error messages
- Verify WebSocket connection is stable
- Test with simple scripts first
- Check environment variables are set correctly

---

**Last Updated:** 2026-01-07  
**Version:** 1.0

