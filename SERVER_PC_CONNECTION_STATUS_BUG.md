# 🚨 CRITICAL BUG: PC Connection Status Not Updating

## Problem Summary

**PC clients are connecting successfully and sending `pc_info` messages, but the server is NOT updating the `connected` status to `true` in MongoDB.**

### Evidence

**PC Client Logs (Working Correctly):**
```
2026-01-07 19:50:50,359 - INFO - ✓ Connected as ShreshthKaushik
2026-01-07 19:50:51,051 - INFO - Connection message: Connected to server as ShreshthKaushik
2026-01-07 19:50:51,072 - INFO - Sending PC info immediately after connection - Detected IP: 192.168.1.40
```

**MongoDB Document (WRONG - Shows `connected: false`):**
```json
{
  "pc_id": "ShreshthKaushik",
  "connected": false,  // ❌ SHOULD BE true
  "connected_at": "2026-01-07T13:48:24.740Z",
  "last_seen": "2026-01-07T13:58:45.789Z",
  "ip_address": "192.168.1.40",
  "hostname": "ShreshthKaushik"
}
```

## Root Cause

The server WebSocket handler is **NOT** updating the `connected` field to `true` when:
1. A PC client connects to the WebSocket
2. A PC client sends a `pc_info` message
3. A PC client sends a `heartbeat` or `pong` message

## Impact

- **Frontend shows all PCs as OFFLINE** even when they're connected
- **Scripts cannot be sent** because the frontend filters out offline PCs
- **System is unusable** for production with multiple PCs
- **Scalability issue**: Will fail with multiple concurrent connections

## Required Fixes

### Fix 1: Update `connected` Status on WebSocket Connection

**Location:** WebSocket connection handler (likely in `websocket/handlers.py` or similar)

**When:** Immediately when a PC client connects to `/ws/{pc_id}`

**Action:**
```python
# When WebSocket connection is established
async def handle_connection(websocket, pc_id):
    # ... existing connection code ...
    
    # CRITICAL: Update connected status in database
    await update_pc_connection_status(pc_id, connected=True)
    
    # Send connection message
    await websocket.send(json.dumps({
        "type": "connection",
        "status": "connected",
        "message": f"Connected to server as {pc_id}",
        "server_url": get_server_url()
    }))
```

**Database Update Function:**
```python
async def update_pc_connection_status(pc_id: str, connected: bool):
    """Update PC connection status in MongoDB"""
    from datetime import datetime
    
    update_data = {
        "$set": {
            "connected": connected,
            "last_seen": datetime.utcnow()
        }
    }
    
    if connected:
        update_data["$set"]["connected_at"] = datetime.utcnow()
    
    await db.pcs.update_one(
        {"pc_id": pc_id},
        update_data,
        upsert=True  # Create if doesn't exist
    )
```

### Fix 2: Update `connected` Status on `pc_info` Message

**Location:** WebSocket message handler for `pc_info` type

**When:** When receiving a `pc_info` message from PC client

**Action:**
```python
async def handle_pc_info(websocket, pc_id, data):
    """Handle pc_info message from PC client"""
    ip_address = data.get("ip_address")
    hostname = data.get("hostname")
    name = data.get("name")
    os_info = data.get("os_info", {})
    metadata = data.get("metadata", {})
    
    # CRITICAL: Update connected status to true when receiving pc_info
    # This ensures PC is marked as online even if connection handler missed it
    await update_pc_connection_status(pc_id, connected=True)
    
    # Update PC information
    await db.pcs.update_one(
        {"pc_id": pc_id},
        {
            "$set": {
                "ip_address": ip_address,
                "hostname": hostname,
                "name": name,
                "os_info": os_info,
                "metadata": metadata,
                "last_seen": datetime.utcnow(),
                "connected": True  # CRITICAL: Set to true
            },
            "$setOnInsert": {
                "pc_id": pc_id,
                "connected_at": datetime.utcnow()
            }
        },
        upsert=True
    )
```

### Fix 3: Update `last_seen` on Heartbeat/Pong Messages

**Location:** WebSocket message handler for `heartbeat` and `pong` types

**When:** When receiving `heartbeat` or `pong` messages

**Action:**
```python
async def handle_heartbeat(websocket, pc_id, data):
    """Handle heartbeat message from PC client"""
    # Update last_seen timestamp
    await db.pcs.update_one(
        {"pc_id": pc_id},
        {
            "$set": {
                "last_seen": datetime.utcnow(),
                "connected": True  # Ensure it stays true
            }
        }
    )
    
    # Send pong response
    await websocket.send(json.dumps({"type": "pong"}))

async def handle_pong(websocket, pc_id, data):
    """Handle pong response from PC client"""
    # Update last_seen timestamp
    await db.pcs.update_one(
        {"pc_id": pc_id},
        {
            "$set": {
                "last_seen": datetime.utcnow(),
                "connected": True
            }
        }
    )
```

### Fix 4: Set `connected` to `false` on WebSocket Disconnect

**Location:** WebSocket disconnect handler

**When:** When WebSocket connection is closed

**Action:**
```python
async def handle_disconnect(websocket, pc_id):
    """Handle WebSocket disconnection"""
    # CRITICAL: Mark PC as disconnected
    await db.pcs.update_one(
        {"pc_id": pc_id},
        {
            "$set": {
                "connected": False,
                "last_seen": datetime.utcnow()
            }
        }
    )
    
    # Clean up any active sessions
    await cleanup_pc_sessions(pc_id)
```

### Fix 5: Periodic Connection Status Check (Optional but Recommended)

**Location:** Background task or scheduled job

**Purpose:** Mark PCs as offline if they haven't sent a heartbeat in X seconds

**Action:**
```python
async def check_stale_connections():
    """Mark PCs as offline if they haven't sent heartbeat in 60 seconds"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(seconds=60)
    
    result = await db.pcs.update_many(
        {
            "connected": True,
            "last_seen": {"$lt": cutoff_time}
        },
        {
            "$set": {
                "connected": False
            }
        }
    )
    
    if result.modified_count > 0:
        logger.info(f"Marked {result.modified_count} PCs as offline (stale connection)")
```

## Message Flow (What PC Client Sends)

The PC client sends these messages in order:

1. **Connects to WebSocket:** `/ws/{pc_id}`
2. **Receives connection message** from server
3. **Sends `pc_info` message:**
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
       "processor": "Intel64 Family 6 Model 170 Stepping 4, GenuineIntel"
     }
   }
   ```
4. **Sends `heartbeat` every 15 seconds:**
   ```json
   {
     "type": "heartbeat",
     "status": "ok"
   }
   ```
5. **Sends `pc_info` every 60 seconds** (periodic update)

## Testing Checklist

After implementing fixes, test:

- [ ] PC connects → `connected: true` in MongoDB
- [ ] PC sends `pc_info` → `connected: true` in MongoDB
- [ ] PC sends `heartbeat` → `last_seen` updated, `connected: true`
- [ ] PC disconnects → `connected: false` in MongoDB
- [ ] Multiple PCs connect simultaneously → All show `connected: true`
- [ ] Frontend `/api/pcs` endpoint returns correct `connected` status
- [ ] Frontend filters work correctly (connected_only parameter)

## Expected Behavior After Fix

**MongoDB Document (CORRECT):**
```json
{
  "pc_id": "ShreshthKaushik",
  "connected": true,  // ✅ CORRECT
  "connected_at": "2026-01-07T19:50:50.359Z",
  "last_seen": "2026-01-07T19:51:06.789Z",  // Updated every 15s
  "ip_address": "192.168.1.40",
  "hostname": "ShreshthKaushik"
}
```

**Frontend API Response:**
```json
{
  "total": 1,
  "connected": 1,
  "pcs": [
    {
      "pc_id": "ShreshthKaushik",
      "connected": true,  // ✅ CORRECT
      "connected_at": "2026-01-07T19:50:50.359Z",
      "last_seen": "2026-01-07T19:51:06.789Z"
    }
  ]
}
```

## Scalability Considerations

For multiple PCs:

1. **Use database indexes:**
   ```python
   # Create index on pc_id for fast lookups
   await db.pcs.create_index("pc_id", unique=True)
   await db.pcs.create_index("connected")
   await db.pcs.create_index("last_seen")
   ```

2. **Batch updates** if updating many PCs at once

3. **Connection pooling** for database connections

4. **WebSocket connection manager** to track all active connections:
   ```python
   class ConnectionManager:
       def __init__(self):
           self.active_connections: Dict[str, WebSocket] = {}
       
       async def connect(self, pc_id: str, websocket: WebSocket):
           self.active_connections[pc_id] = websocket
           await update_pc_connection_status(pc_id, connected=True)
       
       async def disconnect(self, pc_id: str):
           if pc_id in self.active_connections:
               del self.active_connections[pc_id]
               await update_pc_connection_status(pc_id, connected=False)
   ```

## Priority

**🔴 CRITICAL - FIX IMMEDIATELY**

This bug makes the entire system unusable. Without this fix:
- Frontend cannot identify which PCs are online
- Scripts cannot be sent to PCs
- System cannot scale to multiple PCs
- Production deployment will fail

## Questions?

If you need clarification on:
- Message formats → See `API_DOCUMENTATION.md`
- PC client behavior → See `pc_client.py` (lines 1165-1192, 971-1000)
- Database schema → See PC model in `models/pc.py`

---

**Last Updated:** 2026-01-07  
**Status:** 🔴 URGENT - Blocking production deployment

