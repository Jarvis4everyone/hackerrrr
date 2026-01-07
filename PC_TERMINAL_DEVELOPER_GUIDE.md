# 🖥️ PC Client Terminal Feature - Developer Guide

## Overview

This guide explains how to implement terminal functionality in the PC client. The terminal feature allows the server to remotely execute PowerShell commands on the PC and receive real-time output.

## Architecture

The terminal feature uses **two WebSocket connections**:

1. **Main WebSocket** (`/ws/{pc_id}`) - Used for all PC communication including terminal control messages
2. **Terminal WebSocket** (`/ws/terminal/{pc_id}/{session_id}`) - Used by frontend to receive terminal output (handled by server)

**Important:** The PC client only uses the **main WebSocket**. The server forwards terminal output to the frontend's terminal WebSocket.

## Message Flow

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │         │    Server   │         │  PC Client  │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. POST /api/terminal/start                     │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 2. start_terminal      │
       │                       │───────────────────────>│
       │                       │                        │
       │ 3. {session_id}       │                        │
       │<──────────────────────│                        │
       │                       │                        │
       │ 4. Connect to /ws/terminal/{pc_id}/{sess_id}    │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 5. terminal_ready      │
       │                       │<───────────────────────│
       │                       │                        │
       │                       │ 6. terminal_output     │
       │                       │<───────────────────────│
       │                       │                        │
       │ 7. {type: "output"}  │                        │
       │<──────────────────────│                        │
       │                       │                        │
       │ 8. {type: "command"} │                        │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 9. terminal_command    │
       │                       │───────────────────────>│
       │                       │                        │
       │                       │ 10. terminal_output    │
       │                       │<───────────────────────│
       │                       │                        │
       │ 11. {type: "output"}  │                        │
       │<──────────────────────│                        │
```

## Messages PC Client Receives (via Main WebSocket)

### 1. `start_terminal`

**When:** Server wants to start a new terminal session

**Message Format:**
```json
{
  "type": "start_terminal",
  "session_id": "uuid-here"
}
```

**PC Client Action:**
1. Store the `session_id`
2. Start a PowerShell process (or appropriate shell for your OS)
3. Set up output capture (stdout/stderr)
4. Send `terminal_ready` message when terminal is ready
5. Send initial prompt via `terminal_output`

**Example Implementation (Python):**
```python
import subprocess
import threading
import queue

class TerminalSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.process = None
        self.output_queue = queue.Queue()
        self.running = False
    
    def start(self, websocket):
        """Start PowerShell process"""
        # Windows PowerShell
        self.process = subprocess.Popen(
            ["powershell.exe", "-NoExit", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Start output reader thread
        self.running = True
        threading.Thread(target=self._read_output, args=(websocket,), daemon=True).start()
        
        # Send ready message
        await websocket.send_json({
            "type": "terminal_ready",
            "session_id": self.session_id
        })
        
        # Send initial prompt
        await websocket.send_json({
            "type": "terminal_output",
            "session_id": self.session_id,
            "output": "PS C:\\Users\\user> ",
            "is_complete": False
        })
    
    def _read_output(self, websocket):
        """Read output from process and send to server"""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    await websocket.send_json({
                        "type": "terminal_output",
                        "session_id": self.session_id,
                        "output": line,
                        "is_complete": False
                    })
                elif self.process.poll() is not None:
                    # Process ended
                    break
            except Exception as e:
                logger.error(f"Error reading terminal output: {e}")
                break
```

### 2. `terminal_command`

**When:** Server wants to execute a command in the terminal

**Message Format:**
```json
{
  "type": "terminal_command",
  "session_id": "uuid-here",
  "command": "dir\r\n"
}
```

**PC Client Action:**
1. Write the command to the terminal process's stdin
2. The process will execute the command
3. Output will be captured and sent via `terminal_output` messages

**Example Implementation:**
```python
def handle_terminal_command(self, session_id, command):
    """Handle command from server"""
    if session_id in self.terminal_sessions:
        session = self.terminal_sessions[session_id]
        if session.process and session.process.stdin:
            try:
                session.process.stdin.write(command)
                session.process.stdin.flush()
            except Exception as e:
                logger.error(f"Error writing command: {e}")
                await websocket.send_json({
                    "type": "terminal_error",
                    "session_id": session_id,
                    "error": str(e)
                })
```

### 3. `terminal_interrupt`

**When:** Server wants to send Ctrl+C to interrupt current command

**Message Format:**
```json
{
  "type": "terminal_interrupt",
  "session_id": "uuid-here"
}
```

**PC Client Action:**
1. Send interrupt signal (Ctrl+C) to the terminal process
2. On Windows: Use `CTRL_C_EVENT` signal
3. On Linux/Mac: Use `SIGINT` signal

**Example Implementation (Windows):**
```python
import signal

def handle_terminal_interrupt(self, session_id):
    """Send Ctrl+C to terminal process"""
    if session_id in self.terminal_sessions:
        session = self.terminal_sessions[session_id]
        if session.process:
            try:
                # Windows: Send CTRL_C_EVENT
                session.process.send_signal(signal.CTRL_C_EVENT)
            except Exception as e:
                logger.error(f"Error sending interrupt: {e}")
```

### 4. `stop_terminal`

**When:** Server wants to stop the terminal session

**Message Format:**
```json
{
  "type": "stop_terminal",
  "session_id": "uuid-here"
}
```

**PC Client Action:**
1. Stop reading output
2. Terminate the terminal process
3. Clean up session resources
4. Remove session from active sessions

**Example Implementation:**
```python
def handle_stop_terminal(self, session_id):
    """Stop terminal session"""
    if session_id in self.terminal_sessions:
        session = self.terminal_sessions[session_id]
        session.running = False
        
        if session.process:
            try:
                session.process.terminate()
                session.process.wait(timeout=5)
            except:
                session.process.kill()
        
        del self.terminal_sessions[session_id]
```

## Messages PC Client Sends (via Main WebSocket)

### 1. `terminal_ready`

**When:** Terminal process is ready and initialized

**Message Format:**
```json
{
  "type": "terminal_ready",
  "session_id": "uuid-here"
}
```

**Example:**
```python
await websocket.send_json({
    "type": "terminal_ready",
    "session_id": session_id
})
```

### 2. `terminal_output`

**When:** Terminal produces output (stdout/stderr)

**Message Format:**
```json
{
  "type": "terminal_output",
  "session_id": "uuid-here",
  "output": "PS C:\\Users\\user> dir\r\n",
  "is_complete": false
}
```

**Fields:**
- `session_id`: The terminal session ID
- `output`: The terminal output (can be partial or complete)
- `is_complete`: `true` if this is the final output for a command, `false` for streaming output

**Important Notes:**
- Send output **as soon as it's available** (streaming)
- Include newlines (`\r\n` on Windows, `\n` on Unix)
- Set `is_complete: true` when command execution is finished
- Send output in **chunks** if it's large (don't wait for entire output)

**Example:**
```python
# Streaming output
await websocket.send_json({
    "type": "terminal_output",
    "session_id": session_id,
    "output": line,  # Single line or chunk
    "is_complete": False
})

# Final output (when command completes)
await websocket.send_json({
    "type": "terminal_output",
    "session_id": session_id,
    "output": final_output,
    "is_complete": True
})
```

### 3. `terminal_error`

**When:** Terminal encounters an error

**Message Format:**
```json
{
  "type": "terminal_error",
  "session_id": "uuid-here",
  "error": "Error message here"
}
```

**Example:**
```python
await websocket.send_json({
    "type": "terminal_error",
    "session_id": session_id,
    "error": "Failed to start PowerShell process: Access denied"
})
```

## Complete Implementation Example

```python
import subprocess
import threading
import queue
import logging
import signal
from typing import Dict

logger = logging.getLogger(__name__)

class TerminalManager:
    """Manages terminal sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
    
    async def handle_start_terminal(self, websocket, session_id: str):
        """Handle start_terminal message"""
        if session_id in self.sessions:
            # Stop existing session
            await self.handle_stop_terminal(session_id)
        
        # Create new session
        session = TerminalSession(session_id)
        self.sessions[session_id] = session
        await session.start(websocket)
    
    async def handle_terminal_command(self, session_id: str, command: str):
        """Handle terminal_command message"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.send_command(command)
    
    async def handle_terminal_interrupt(self, session_id: str):
        """Handle terminal_interrupt message"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.interrupt()
    
    async def handle_stop_terminal(self, session_id: str):
        """Handle stop_terminal message"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.stop()
            del self.sessions[session_id]


class TerminalSession:
    """Represents a single terminal session"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.process = None
        self.running = False
        self.output_thread = None
    
    async def start(self, websocket):
        """Start PowerShell process"""
        try:
            # Start PowerShell process
            self.process = subprocess.Popen(
                ["powershell.exe", "-NoExit", "-Command", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Windows: Hide window
            )
            
            # Start output reader
            self.running = True
            self.output_thread = threading.Thread(
                target=self._read_output,
                args=(websocket,),
                daemon=True
            )
            self.output_thread.start()
            
            # Send ready message
            await websocket.send_json({
                "type": "terminal_ready",
                "session_id": self.session_id
            })
            
            logger.info(f"Terminal session {self.session_id} started")
            
        except Exception as e:
            logger.error(f"Error starting terminal: {e}")
            await websocket.send_json({
                "type": "terminal_error",
                "session_id": self.session_id,
                "error": str(e)
            })
    
    def _read_output(self, websocket):
        """Read output from process"""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if line:
                    # Send output asynchronously
                    asyncio.create_task(websocket.send_json({
                        "type": "terminal_output",
                        "session_id": self.session_id,
                        "output": line,
                        "is_complete": False
                    }))
                elif self.process.poll() is not None:
                    # Process ended
                    break
            except Exception as e:
                logger.error(f"Error reading terminal output: {e}")
                break
    
    async def send_command(self, command: str):
        """Send command to terminal"""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(command)
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"Error sending command: {e}")
    
    def interrupt(self):
        """Send Ctrl+C interrupt"""
        if self.process:
            try:
                self.process.send_signal(signal.CTRL_C_EVENT)
            except Exception as e:
                logger.error(f"Error sending interrupt: {e}")
    
    async def stop(self):
        """Stop terminal session"""
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
        
        if self.output_thread:
            self.output_thread.join(timeout=2)
        
        logger.info(f"Terminal session {self.session_id} stopped")


# Usage in WebSocket handler
terminal_manager = TerminalManager()

async def handle_websocket_message(websocket, pc_id: str, message: dict):
    """Handle WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "start_terminal":
        session_id = message.get("session_id")
        await terminal_manager.handle_start_terminal(websocket, session_id)
    
    elif message_type == "terminal_command":
        session_id = message.get("session_id")
        command = message.get("command", "")
        await terminal_manager.handle_terminal_command(session_id, command)
    
    elif message_type == "terminal_interrupt":
        session_id = message.get("session_id")
        await terminal_manager.handle_terminal_interrupt(session_id)
    
    elif message_type == "stop_terminal":
        session_id = message.get("session_id")
        await terminal_manager.handle_stop_terminal(session_id)
```

## Platform-Specific Notes

### Windows

- Use `powershell.exe` for PowerShell
- Use `cmd.exe` for Command Prompt
- Use `subprocess.CREATE_NO_WINDOW` to hide terminal window
- Use `signal.CTRL_C_EVENT` for Ctrl+C

### Linux/Mac

- Use `/bin/bash` or `/bin/zsh` for shell
- Use `signal.SIGINT` for Ctrl+C
- May need to set up pseudo-terminal (PTY) for better terminal emulation

## Best Practices

1. **Stream Output Immediately**: Don't buffer output - send it as soon as it's available
2. **Handle Errors Gracefully**: Always send `terminal_error` if something goes wrong
3. **Clean Up Resources**: Always clean up processes and threads when session ends
4. **Use Threading**: Read output in a separate thread to avoid blocking
5. **Handle Disconnections**: Clean up sessions if WebSocket disconnects
6. **Buffer Management**: For large outputs, send in chunks to avoid overwhelming the connection
7. **Encoding**: Use UTF-8 encoding for text output
8. **Newlines**: Use `\r\n` on Windows, `\n` on Unix

## Testing

1. **Test Basic Commands**: `dir`, `ls`, `echo`, `pwd`
2. **Test Long Output**: Commands that produce lots of output
3. **Test Interrupt**: Send Ctrl+C and verify it works
4. **Test Multiple Sessions**: Multiple terminal sessions simultaneously
5. **Test Error Handling**: Invalid commands, process failures
6. **Test Disconnection**: What happens when WebSocket disconnects

## Troubleshooting

### Terminal Not Starting
- Check if PowerShell/Shell is available in PATH
- Check process permissions
- Verify subprocess creation flags

### Output Not Appearing
- Verify output is being read from stdout
- Check if `terminal_output` messages are being sent
- Verify `session_id` matches

### Commands Not Executing
- Check if stdin is being written correctly
- Verify process is still running
- Check for encoding issues

### Ctrl+C Not Working
- Verify signal is being sent correctly
- Check process signal handling
- Test on different platforms

## Security Considerations

1. **Command Validation**: Consider validating commands before execution (optional)
2. **User Permissions**: Terminal runs with PC client's user permissions
3. **Path Restrictions**: Consider restricting access to certain directories
4. **Process Isolation**: Each session should be isolated
5. **Resource Limits**: Consider limiting memory/CPU usage per session

## Support

For issues or questions:
- Check server logs for error messages
- Verify WebSocket connection is stable
- Test with simple commands first
- Check platform-specific requirements

---

**Last Updated:** 2026-01-07  
**Version:** 1.0

