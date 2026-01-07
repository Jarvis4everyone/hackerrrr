# 🚨 CRITICAL: Terminal Session Issues

## Problems

1. **404 Error on `/api/terminal/start`** - Endpoint doesn't exist or route is wrong
2. **Terminal output not displaying** - PC sends output but frontend doesn't receive it

## Root Cause Analysis

### Issue 1: 404 on Terminal Start

**Error:**
```
hackerrrr-backend.onrender.com/api/terminal/start?pc_id=ShreshthKaushik:1  
Failed to load resource: the server responded with a status of 404 ()
```

**Expected Behavior:**
- Frontend calls: `POST /api/terminal/start?pc_id=ShreshthKaushik`
- Server should:
  1. Create a terminal session
  2. Generate a `session_id`
  3. Send `start_terminal` message to PC via main WebSocket (`/ws/{pc_id}`)
  4. Return `session_id` to frontend
  5. Frontend connects to terminal WebSocket: `/ws/terminal/{pc_id}/{session_id}`

**Current Status:** Endpoint returns 404 - **ENDPOINT MISSING OR ROUTE MISCONFIGURED**

### Issue 2: Terminal Output Not Displaying

**Expected Flow:**
```
PC Client (Main WebSocket) → Server → Terminal WebSocket → Frontend
```

1. PC receives `start_terminal` message via main WebSocket
2. PC starts PowerShell process
3. PC sends `terminal_output` messages via main WebSocket
4. **Server must forward** `terminal_output` to terminal WebSocket
5. Frontend terminal WebSocket receives and displays output

**Current Status:** PC is sending output, but server isn't forwarding it to terminal WebSocket

## Required Fixes

### Fix 1: Create/Verify Terminal Start Endpoint

**Location:** `routes/terminal.py` or `app/routes/terminal.py`

**Endpoint:** `POST /api/terminal/start`

**Required Code:**
```python
from fastapi import APIRouter, Query
from uuid import uuid4
from datetime import datetime

router = APIRouter()

@router.post("/api/terminal/start")
async def start_terminal_session(pc_id: str = Query(...)):
    """
    Start a terminal session for a PC
    
    Flow:
    1. Generate session_id
    2. Send start_terminal message to PC via main WebSocket
    3. Return session_id to frontend
    4. Frontend connects to /ws/terminal/{pc_id}/{session_id}
    """
    # Generate unique session ID
    session_id = str(uuid4())
    
    # Check if PC is connected
    pc = await db.pcs.find_one({"pc_id": pc_id, "connected": True})
    if not pc:
        raise HTTPException(status_code=404, detail=f"PC {pc_id} is not connected")
    
    # Get PC's main WebSocket connection
    websocket_manager = get_websocket_manager()  # Your WebSocket manager
    pc_websocket = websocket_manager.get_connection(pc_id)
    
    if not pc_websocket:
        raise HTTPException(status_code=404, detail=f"PC {pc_id} WebSocket connection not found")
    
    # Send start_terminal message to PC via main WebSocket
    try:
        await pc_websocket.send(json.dumps({
            "type": "start_terminal",
            "session_id": session_id
        }))
    except Exception as e:
        logger.error(f"Error sending start_terminal to PC {pc_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start terminal session: {str(e)}")
    
    # Store session info (optional, for tracking)
    await db.terminal_sessions.insert_one({
        "session_id": session_id,
        "pc_id": pc_id,
        "created_at": datetime.utcnow(),
        "status": "starting"
    })
    
    return {
        "session_id": session_id,
        "pc_id": pc_id,
        "status": "started"
    }
```

### Fix 2: Forward Terminal Output to Terminal WebSocket

**Location:** WebSocket message handler for main PC connection (`/ws/{pc_id}`)

**When:** Receiving `terminal_output` message from PC

**Required Code:**
```python
async def handle_pc_message(websocket, pc_id, message):
    """Handle messages from PC via main WebSocket"""
    data = json.loads(message)
    message_type = data.get("type")
    
    if message_type == "terminal_output":
        # CRITICAL: Forward terminal output to terminal WebSocket
        session_id = data.get("session_id")
        output = data.get("output")
        is_complete = data.get("is_complete", False)
        
        if not session_id:
            logger.error("terminal_output message missing session_id")
            return
        
        # Get terminal WebSocket connection
        terminal_ws_manager = get_terminal_websocket_manager()
        terminal_ws = terminal_ws_manager.get_connection(pc_id, session_id)
        
        if terminal_ws:
            # Forward output to terminal WebSocket
            try:
                await terminal_ws.send(json.dumps({
                    "type": "output",
                    "output": output,
                    "is_complete": is_complete
                }))
            except Exception as e:
                logger.error(f"Error forwarding terminal output: {e}")
        else:
            logger.warning(f"Terminal WebSocket not found for {pc_id}/{session_id}")
    
    elif message_type == "terminal_ready":
        # PC terminal is ready
        session_id = data.get("session_id")
        logger.info(f"Terminal session {session_id} is ready")
        
        # Update session status
        await db.terminal_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "ready"}}
        )
    
    elif message_type == "terminal_error":
        # Forward terminal error to terminal WebSocket
        session_id = data.get("session_id")
        error = data.get("error")
        
        terminal_ws_manager = get_terminal_websocket_manager()
        terminal_ws = terminal_ws_manager.get_connection(pc_id, session_id)
        
        if terminal_ws:
            await terminal_ws.send(json.dumps({
                "type": "error",
                "message": error
            }))
```

### Fix 3: Terminal WebSocket Handler

**Location:** `websocket/terminal_handlers.py` or similar

**Endpoint:** `/ws/terminal/{pc_id}/{session_id}`

**Required Code:**
```python
async def handle_terminal_websocket(websocket, pc_id: str, session_id: str):
    """Handle terminal WebSocket connection from frontend"""
    # Store connection in manager
    terminal_ws_manager = get_terminal_websocket_manager()
    terminal_ws_manager.add_connection(pc_id, session_id, websocket)
    
    try:
        # Wait for messages from frontend (commands)
        async for message in websocket:
            data = json.loads(message)
            
            if data.get("type") == "command":
                # Forward command to PC via main WebSocket
                command = data.get("command")
                
                # Get PC's main WebSocket
                main_ws_manager = get_websocket_manager()
                pc_websocket = main_ws_manager.get_connection(pc_id)
                
                if pc_websocket:
                    await pc_websocket.send(json.dumps({
                        "type": "terminal_command",
                        "session_id": session_id,
                        "command": command
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": f"PC {pc_id} is not connected"
                    }))
            
            elif data.get("type") == "interrupt":
                # Forward Ctrl+C to PC
                main_ws_manager = get_websocket_manager()
                pc_websocket = main_ws_manager.get_connection(pc_id)
                
                if pc_websocket:
                    await pc_websocket.send(json.dumps({
                        "type": "terminal_interrupt",
                        "session_id": session_id
                    }))
    
    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected: {pc_id}/{session_id}")
    finally:
        # Remove from manager
        terminal_ws_manager.remove_connection(pc_id, session_id)
```

### Fix 4: WebSocket Connection Manager

**Location:** `websocket/connection_manager.py` or similar

**Required Code:**
```python
class TerminalWebSocketManager:
    """Manages terminal WebSocket connections"""
    
    def __init__(self):
        self.connections: Dict[Tuple[str, str], WebSocket] = {}
    
    def add_connection(self, pc_id: str, session_id: str, websocket: WebSocket):
        """Add a terminal WebSocket connection"""
        key = (pc_id, session_id)
        self.connections[key] = websocket
        logger.info(f"Terminal WebSocket connected: {pc_id}/{session_id}")
    
    def remove_connection(self, pc_id: str, session_id: str):
        """Remove a terminal WebSocket connection"""
        key = (pc_id, session_id)
        if key in self.connections:
            del self.connections[key]
            logger.info(f"Terminal WebSocket disconnected: {pc_id}/{session_id}")
    
    def get_connection(self, pc_id: str, session_id: str) -> Optional[WebSocket]:
        """Get terminal WebSocket connection"""
        key = (pc_id, session_id)
        return self.connections.get(key)

# Global instance
_terminal_ws_manager = None

def get_terminal_websocket_manager():
    global _terminal_ws_manager
    if _terminal_ws_manager is None:
        _terminal_ws_manager = TerminalWebSocketManager()
    return _terminal_ws_manager
```

## Message Flow Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │         │    Server    │         │  PC Client  │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. POST /api/terminal/start                    │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 2. start_terminal      │
       │                       │───────────────────────>│
       │                       │                        │
       │ 3. {session_id}       │                        │
       │<──────────────────────│                        │
       │                       │                        │
       │ 4. Connect to /ws/terminal/{pc_id}/{sess_id}  │
       │──────────────────────>│                        │
       │                       │                        │
       │                       │ 5. terminal_ready      │
       │                       │<───────────────────────│
       │                       │                        │
       │                       │ 6. terminal_output     │
       │                       │<───────────────────────│
       │                       │                        │
       │ 7. {type: "output"}   │                        │
       │<──────────────────────│                        │
       │                       │                        │
       │ 8. {type: "command"}  │                        │
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
       │                       │                        │
```

## Testing Checklist

After implementing fixes:

- [ ] `POST /api/terminal/start?pc_id=X` returns `{session_id: "..."}`
- [ ] Server sends `start_terminal` message to PC via main WebSocket
- [ ] PC receives `start_terminal` and starts PowerShell
- [ ] PC sends `terminal_ready` message
- [ ] PC sends `terminal_output` with initial prompt
- [ ] Server forwards `terminal_output` to terminal WebSocket
- [ ] Frontend terminal WebSocket receives output and displays it
- [ ] Frontend sends command → Server forwards to PC
- [ ] PC executes command → Sends output → Server forwards → Frontend displays
- [ ] Multiple terminal sessions work simultaneously

## PC Client Message Types (What PC Sends)

The PC client sends these messages via **main WebSocket** (`/ws/{pc_id}`):

1. **`terminal_ready`** - When terminal process is ready
   ```json
   {
     "type": "terminal_ready",
     "session_id": "uuid-here"
   }
   ```

2. **`terminal_output`** - Terminal output from PowerShell
   ```json
   {
     "type": "terminal_output",
     "session_id": "uuid-here",
     "output": "PS C:\\Users\\shres> ",
     "is_complete": false
   }
   ```

3. **`terminal_error`** - Terminal error
   ```json
   {
     "type": "terminal_error",
     "session_id": "uuid-here",
     "error": "Error message"
   }
   ```

## Server Message Types (What Server Sends to PC)

The server sends these messages via **main WebSocket** (`/ws/{pc_id}`):

1. **`start_terminal`** - Start terminal session
   ```json
   {
     "type": "start_terminal",
     "session_id": "uuid-here"
   }
   ```

2. **`terminal_command`** - Execute command
   ```json
   {
     "type": "terminal_command",
     "session_id": "uuid-here",
     "command": "dir\r\n"
   }
   ```

3. **`terminal_interrupt`** - Send Ctrl+C
   ```json
   {
     "type": "terminal_interrupt",
     "session_id": "uuid-here"
   }
   ```

4. **`stop_terminal`** - Stop terminal session
   ```json
   {
     "type": "stop_terminal",
     "session_id": "uuid-here"
   }
   ```

## Critical Points

1. **Two WebSocket Connections:**
   - Main WebSocket: `/ws/{pc_id}` - For all PC communication
   - Terminal WebSocket: `/ws/terminal/{pc_id}/{session_id}` - For terminal UI

2. **Message Forwarding:**
   - PC sends `terminal_output` via **main WebSocket**
   - Server **must forward** to **terminal WebSocket**
   - Frontend receives via **terminal WebSocket**

3. **Session Management:**
   - Each terminal session has unique `session_id`
   - Server tracks active terminal WebSocket connections
   - Server forwards messages based on `session_id`

## Priority

**🔴 CRITICAL - FIX IMMEDIATELY**

Terminal functionality is completely broken. Without these fixes:
- Users cannot use terminal feature
- System is incomplete
- Production deployment will fail

---

**Last Updated:** 2026-01-07  
**Status:** 🔴 URGENT - Terminal feature non-functional

