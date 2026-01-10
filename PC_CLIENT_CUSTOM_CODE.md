# PC Client Custom Code Execution Documentation

## Overview

The PC client supports executing **custom Python code** sent from the server. This feature allows the server to run any Python code on the target PC, with automatic dependency installation support.

## Message Format

When the server sends custom code for execution, the PC client receives a WebSocket message with the following format:

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

- **`type`** (required): Must be `"custom_code"` to identify this message type
- **`code`** (required): The Python code to execute (as a string)
- **`requirements`** (optional): pip install commands to run before executing the code
  - Can be a single command: `"pip install pyqt5"`
  - Or multiple commands separated by newlines: `"pip install pyqt5\npip install requests"`
- **`server_url`** (required): HTTP URL of the server (for sending results back)
- **`execution_id`** (required): Unique identifier for this execution

## Implementation Guide

### Step 1: Handle the Message Type

In your PC client's message handler, add a case for `custom_code`:

```python
async def handle_message(self, message: dict):
    message_type = message.get("type")
    
    if message_type == "custom_code":
        await self.handle_custom_code(message)
    elif message_type == "script":
        # Existing script handler
        ...
    # ... other message types
```

### Step 2: Implement Custom Code Handler

Create a handler method that:

1. **Installs requirements** (if provided)
2. **Executes the code**
3. **Captures output** (stdout/stderr)
4. **Sends results back** to the server

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
            # Split requirements by newlines to handle multiple pip install commands
            req_lines = [line.strip() for line in requirements.strip().split('\n') if line.strip()]
            
            for req_line in req_lines:
                if req_line.startswith('pip install'):
                    # Extract package names (handle "pip install package1 package2")
                    cmd = req_line.split()
                    if len(cmd) >= 3:
                        # Run pip install command
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout for installations
                        )
                        if result.returncode == 0:
                            logger.info(f"[Custom Code] Successfully installed: {req_line}")
                        else:
                            logger.warning(f"[Custom Code] Installation warning: {result.stderr}")
                else:
                    logger.warning(f"[Custom Code] Skipping invalid requirement line: {req_line}")
        except Exception as e:
            logger.error(f"[Custom Code] Error installing requirements: {e}")
            # Continue with code execution even if requirements fail
    
    # Step 2: Execute the code
    try:
        # Create a temporary file for the code
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
            
            # Set environment variables (same as script execution)
            os.environ['SERVER_URL'] = server_url
            os.environ['PC_ID'] = self.pc_id
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
            
            logger.info(f"[Custom Code] Execution completed successfully (ID: {execution_id})")
            
            # Send success message back to server
            await self.send_message({
                "type": "execution_complete",
                "execution_id": execution_id,
                "status": "success",
                "script_name": "custom_code.py",
                "output": stdout_content,
                "error": stderr_content
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
        logger.error(f"[Custom Code] Traceback: {error_traceback}")
        
        # Send error message back to server
        await self.send_message({
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": "error",
            "script_name": "custom_code.py",
            "error": f"{error_msg}\n\n{error_traceback}"
        })
```

### Step 3: Send Logs (Optional but Recommended)

To send execution logs to the server (similar to script execution), you can also send a log message:

```python
# After execution completes, send log
log_content = f"=== Custom Code Execution ===\n"
log_content += f"Execution ID: {execution_id}\n"
log_content += f"Status: {'Success' if success else 'Error'}\n\n"
log_content += f"=== STDOUT ===\n{stdout_content}\n\n"
if stderr_content:
    log_content += f"=== STDERR ===\n{stderr_content}\n\n"
if error_msg:
    log_content += f"=== ERROR ===\n{error_msg}\n"

await self.send_message({
    "type": "log",
    "execution_id": execution_id,
    "script_name": "custom_code.py",
    "log_content": log_content,
    "log_level": "INFO" if success else "ERROR"
})
```

## Important Considerations

### 1. Requirements Installation

- **Timeout**: Set a reasonable timeout (e.g., 5 minutes) for pip install commands
- **Error Handling**: Continue with code execution even if requirements installation fails
- **Multiple Commands**: Support multiple pip install commands separated by newlines
- **Security**: Be cautious about executing arbitrary pip install commands

### 2. Code Execution

- **Environment Variables**: Set `SERVER_URL`, `PC_ID`, and `EXECUTION_ID` before execution
- **Output Capture**: Capture both stdout and stderr
- **Error Handling**: Catch all exceptions and send error details back to server
- **Cleanup**: Always clean up temporary files, even on error

### 3. Security

- **Sandboxing**: Consider running custom code in a sandboxed environment if possible
- **Resource Limits**: Consider setting timeouts and resource limits for code execution
- **Validation**: Validate code before execution (optional, for advanced implementations)

### 4. Async Operations

If the custom code uses async operations, follow the pattern from `SERVER_SCRIPT_DEVELOPMENT_GUIDE.md`:

```python
# In the code execution handler, if code uses async:
import asyncio

# Create a new event loop for the code
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    # Execute async code
    result = loop.run_until_complete(async_function())
finally:
    loop.close()
```

## Example: Complete Implementation

Here's a complete example that integrates with an existing PC client:

```python
class PCClient:
    # ... existing code ...
    
    async def handle_message(self, message: dict):
        """Handle incoming WebSocket messages"""
        message_type = message.get("type")
        
        if message_type == "custom_code":
            await self.handle_custom_code(message)
        elif message_type == "script":
            await self.handle_script(message)
        # ... other handlers
    
    async def handle_custom_code(self, message: dict):
        """Execute custom Python code with optional requirements"""
        # Implementation from Step 2 above
        ...
```

## Testing

To test the custom code execution:

1. **Simple Test**:
   ```python
   # Code:
   print("Hello from custom code!")
   import sys
   print(f"Python version: {sys.version}")
   ```

2. **With Requirements**:
   ```python
   # Requirements:
   pip install requests
   
   # Code:
   import requests
   print("Requests library imported successfully!")
   ```

3. **Error Handling Test**:
   ```python
   # Code:
   raise ValueError("This is a test error")
   ```

## Integration Checklist

- [ ] Add `custom_code` message type handler
- [ ] Implement requirements installation (pip install)
- [ ] Implement code execution with output capture
- [ ] Send execution results back to server
- [ ] Send logs to server (optional)
- [ ] Handle errors gracefully
- [ ] Clean up temporary files
- [ ] Set environment variables (SERVER_URL, PC_ID, EXECUTION_ID)
- [ ] Test with simple code
- [ ] Test with requirements
- [ ] Test error handling

## Server-Side Integration

The server sends custom code via:
- **Endpoint**: `POST /api/code/execute`
- **WebSocket Message**: `{"type": "custom_code", ...}`

The PC client should respond with:
- **Success**: `{"type": "execution_complete", "status": "success", ...}`
- **Error**: `{"type": "execution_complete", "status": "error", ...}`

## Notes

- Custom code execution follows the same pattern as script execution
- All output (print statements, errors) is captured and sent to the server
- Requirements are installed **before** code execution
- The execution is tracked with an `execution_id` for logging and monitoring
- Custom code has access to the same environment variables as regular scripts

