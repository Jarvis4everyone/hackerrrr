# Server-Side Script Development Guide

## Overview

This guide is for developers creating scripts that will be executed on remote PCs via the PC Client. Scripts are executed in a special context that requires specific considerations.

---

## ⚠️ CRITICAL: Async/Await Context

### Problem: `asyncio.run()` Cannot Be Used

**Scripts are executed in a context where an event loop is already running.** If your script tries to use `asyncio.run()`, you will get this error:

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

### Solution: Use Event Loop Methods Instead

**❌ DON'T DO THIS:**
```python
import asyncio

async def my_async_function():
    # Your async code here
    pass

# This will FAIL:
result = asyncio.run(my_async_function())
```

**✅ DO THIS INSTEAD:**

**Option 1: Create a new event loop (Recommended)**
```python
import asyncio

async def my_async_function():
    # Your async code here
    pass

# Create a new event loop for this script
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    result = loop.run_until_complete(my_async_function())
finally:
    loop.close()
```

**Option 2: Use get_event_loop() if no loop exists**
```python
import asyncio

async def my_async_function():
    # Your async code here
    pass

# Try to get existing loop, create new one if needed
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

result = loop.run_until_complete(my_async_function())
```

**Option 3: Helper function (Best for reusable code)**
```python
import asyncio

def run_async(coro):
    """Helper function to run async code in scripts"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Usage:
async def my_async_function():
    # Your async code here
    pass

result = run_async(my_async_function())
```

---

## Example: Fixing Text-to-Speech Script

### ❌ Broken Code (causes error):
```python
import asyncio
import edge_tts

async def generate_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# This will FAIL:
asyncio.run(generate_speech("Hello", "en-US-AriaNeural", "output.mp3"))
```

### ✅ Fixed Code:
```python
import asyncio
import edge_tts

async def generate_speech(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# Create new event loop for this script
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(generate_speech("Hello", "en-US-AriaNeural", "output.mp3"))
finally:
    loop.close()
```

---

## Environment Variables

Scripts have access to these environment variables (set automatically by the client):

- `SERVER_URL`: The HTTP URL of the server (e.g., `http://0.0.0.0:8000`)
- `PC_ID`: The identifier of the PC running the script
- `EXECUTION_ID`: Unique ID for this script execution
- **Script Parameters**: All parameters from `script_params` are set as environment variables

### Accessing Environment Variables:

```python
import os

server_url = os.environ.get("SERVER_URL")
pc_id = os.environ.get("PC_ID")
execution_id = os.environ.get("EXECUTION_ID")

# Script parameters (example: if script_params = {"MESSAGE": "Hello"})
message = os.environ.get("MESSAGE")
```

---

## Sending Data to Server

Scripts can send data to the server using HTTP POST requests to `SERVER_URL/api/pc/{PC_ID}/script/{EXECUTION_ID}/data`:

```python
import os
import requests

server_url = os.environ.get("SERVER_URL")
pc_id = os.environ.get("PC_ID")
execution_id = os.environ.get("EXECUTION_ID")

# Send data to server
data = {
    "key": "value",
    "result": "some result"
}

response = requests.post(
    f"{server_url}/api/pc/{pc_id}/script/{execution_id}/data",
    json=data
)

if response.status_code == 200:
    print("[+] Data sent successfully")
else:
    print(f"[!] Failed to send data: {response.status_code}")
```

---

## Logging and Output

### Standard Output/Error

All `print()` statements and stdout/stderr output are automatically captured and sent to the server as log files.

```python
print("[*] Starting script execution...")
print("[+] Operation completed successfully")
print("[!] Warning: Something happened")
```

### Log File Location

Scripts can write to log files, but the client automatically captures all output. The log file is saved as:
```
logs/{script_name}_{timestamp}_{execution_id_short}.log
```

---

## Common Patterns

### 1. Making HTTP Requests

```python
import os
import requests

server_url = os.environ.get("SERVER_URL")
pc_id = os.environ.get("PC_ID")
execution_id = os.environ.get("EXECUTION_ID")

# Make GET request
response = requests.get(f"{server_url}/api/endpoint")
data = response.json()

# Make POST request
response = requests.post(
    f"{server_url}/api/endpoint",
    json={"key": "value"}
)
```

### 2. File Operations

```python
import os

# Read file
with open("file.txt", "r") as f:
    content = f.read()

# Write file
with open("output.txt", "w") as f:
    f.write("content")

# Send file to server
import requests
server_url = os.environ.get("SERVER_URL")
pc_id = os.environ.get("PC_ID")
execution_id = os.environ.get("EXECUTION_ID")

with open("output.txt", "rb") as f:
    files = {"file": f}
    response = requests.post(
        f"{server_url}/api/pc/{pc_id}/script/{execution_id}/upload",
        files=files
    )
```

### 3. Running System Commands

```python
import subprocess
import os

# Run command (headless - no visible windows)
result = subprocess.run(
    ["command", "args"],
    capture_output=True,
    text=True
)

print(f"Output: {result.stdout}")
print(f"Error: {result.stderr}")
```

**Note:** All subprocess calls are automatically patched to run headless (no visible windows).

---

## Known Issues and Workarounds

### Issue 1: Fake BSOD Script - Text Above QR Code

**Problem:** In the `fake_bsod.py` script, text appears above the QR code instead of below it.

**Status:** This is a known issue in the script. The text positioning needs to be adjusted in the script code.

**Workaround:** Modify the script to adjust the text position coordinates.

### Issue 2: Edge TTS Async Issues

**Problem:** Edge TTS requires async operations, but `asyncio.run()` fails.

**Solution:** Use the event loop pattern shown in the "Async/Await Context" section above.

---

## Best Practices

1. **Always handle errors gracefully:**
   ```python
   try:
       # Your code
       pass
   except Exception as e:
       print(f"[!] Error: {e}")
   ```

2. **Use environment variables for configuration:**
   ```python
   import os
   message = os.environ.get("MESSAGE", "default value")
   ```

3. **Log important steps:**
   ```python
   print("[*] Starting operation...")
   print("[+] Operation completed")
   print("[!] Warning message")
   ```

4. **Send results to server:**
   ```python
   import requests
   import os
   
   server_url = os.environ.get("SERVER_URL")
   pc_id = os.environ.get("PC_ID")
   execution_id = os.environ.get("EXECUTION_ID")
   
   requests.post(
       f"{server_url}/api/pc/{pc_id}/script/{execution_id}/data",
       json={"result": "success"}
   )
   ```

5. **For async operations, always create a new event loop:**
   ```python
   loop = asyncio.new_event_loop()
   asyncio.set_event_loop(loop)
   try:
       result = loop.run_until_complete(async_function())
   finally:
       loop.close()
   ```

---

## Testing Scripts Locally

Before sending scripts to remote PCs, test them locally:

1. Set environment variables:
   ```bash
   export SERVER_URL="http://localhost:8000"
   export PC_ID="TEST-PC"
   export EXECUTION_ID="test-123"
   ```

2. Run the script:
   ```bash
   python your_script.py
   ```

3. Check for async issues - if your script uses `asyncio.run()`, it will fail in the client context.

---

## Summary

- **❌ Never use `asyncio.run()`** - it will fail
- **✅ Always create a new event loop** for async operations
- **✅ Use environment variables** for configuration
- **✅ Send results via HTTP POST** to the server
- **✅ Handle errors gracefully** and log important steps
- **⚠️ Fix the fake BSOD script** - text positioning issue with QR code

---

## Questions or Issues?

If you encounter issues with script execution:
1. Check the log file in `logs/` directory on the PC
2. Verify environment variables are set correctly
3. Ensure async code uses the event loop pattern (not `asyncio.run()`)
4. Check server logs for HTTP request errors

