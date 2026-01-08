# PC Client Stop Feature Documentation

## Overview

The PC client supports a **one-time stop command** that allows the server to remotely terminate the PC client completely. This feature is useful when you need to stop a PC client from the server interface without physically accessing the PC.

## How It Works

### Server-Side

1. **API Endpoint**: `POST /api/pcs/{pc_id}/stop`
   - Sends a `stop_pc` message to the connected PC client
   - Returns success/error status

2. **WebSocket Message**: The server sends a WebSocket message with:
   ```json
   {
     "type": "stop_pc"
   }
   ```

### PC Client-Side

When the PC client receives a `stop_pc` message:

1. **Immediate Actions**:
   - Sets `self.running = False` to stop all loops
   - Calls `await self.close()` to clean up all resources:
     - Closes all terminal sessions
     - Stops all streaming (camera, microphone, screen)
     - Closes WebSocket connection
   - Calls `sys.exit(0)` to terminate the process completely

2. **Graceful Shutdown**:
   - All cleanup operations are performed before exit
   - Logs are written before termination
   - No data loss or corruption

## Important Notes

### ⚠️ One-Time Action

**This is a ONE-TIME action.** If the PC client:
- Auto-starts on system boot
- Is restarted manually
- Is launched again

**You will need to stop it again** from the server. The stop command does not persist across restarts.

### ✅ When to Use

- Testing and development
- Emergency shutdown
- Stopping a misbehaving client
- Temporary maintenance

### ❌ When NOT to Use

- Permanent shutdown (use system shutdown commands instead)
- Preventing auto-start (configure system startup settings)
- Long-term access control (use firewall/network rules)

## Implementation Details

### PC Client Handler

The PC client handles the `stop_pc` message in the `handle_message()` method:

```python
elif message_type == "stop_pc":
    # Handle PC stop request from server - terminate gracefully
    try:
        logger.info("Received stop_pc command from server - shutting down gracefully")
        # Set running to False to stop all loops
        self.running = False
        # Close all connections and clean up
        await self.close()
        # Exit the process completely
        logger.info("PC client stopped by server command - exiting")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error handling stop_pc: {e}", exc_info=True)
        # Even if there's an error, try to exit
        try:
            sys.exit(0)
        except:
            pass
```

### Server Implementation

**Connection Manager** (`app/websocket/connection_manager.py`):
```python
async def send_stop_command(self, pc_id: str) -> bool:
    """
    Send stop command to a PC client to terminate it completely
    
    This is a one-time action - if the PC client restarts,
    it will need to be stopped again.
    """
    message = {
        "type": "stop_pc"
    }
    logger.info(f"Sending stop command to PC: {pc_id}")
    success = await self.send_personal_message(message, pc_id)
    return success
```

**API Endpoint** (`app/routes/pcs.py`):
```python
@router.post("/{pc_id}/stop")
async def stop_pc(pc_id: str):
    """
    Stop a PC client completely (one-time action)
    """
    if not manager.is_connected(pc_id):
        raise HTTPException(status_code=404, detail=f"PC '{pc_id}' is not connected")
    
    success = await manager.send_stop_command(pc_id)
    
    if success:
        return {
            "status": "success",
            "message": f"Stop command sent to PC '{pc_id}'. The PC client will terminate shortly.",
            "pc_id": pc_id
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send stop command to PC '{pc_id}'."
        )
```

## Frontend Usage

### UI Button

The stop button appears in the PCs page:
- **Location**: Next to the "View" and "Delete" buttons
- **Visibility**: Only shown when PC is connected (online)
- **Icon**: PowerOff icon (orange color)
- **Behavior**: 
  - Shows confirmation dialog before stopping
  - Displays loading state while stopping
  - Shows success/error toast notifications

### API Call

```javascript
import { stopPC } from '../services/api'

// Stop a PC client
try {
  await stopPC(pcId)
  // Success - PC will terminate shortly
} catch (error) {
  // Handle error
}
```

## Troubleshooting

### PC Client Doesn't Stop

**Possible Causes**:
1. **PC is not connected**: Check if PC shows as "ONLINE" in the server
2. **WebSocket connection lost**: The stop command requires an active WebSocket connection
3. **PC client crashed**: If the PC client crashed before receiving the command, it won't stop

**Solutions**:
- Verify PC is connected before sending stop command
- Check PC client logs for errors
- Manually terminate the PC client process if needed

### PC Client Restarts After Stop

**This is expected behavior** if:
- PC client is configured to auto-start on boot
- PC client is launched via startup script
- PC client is running as a Windows service

**To prevent auto-restart**:
- Disable auto-start in system settings
- Remove from startup programs
- Stop the Windows service (if running as service)

### Stop Command Not Received

**Check**:
1. PC client WebSocket connection is active
2. Server logs show the stop command was sent
3. PC client logs show the message was received
4. Network connectivity between server and PC

## Security Considerations

### ⚠️ Important Security Notes

1. **Authentication Required**: The stop endpoint requires authentication (same as other endpoints)

2. **One-Time Only**: The stop command does not persist - it only affects the current running instance

3. **No Remote Restart**: This feature only stops the client - it does NOT restart it. To restart, the PC client must be launched again (manually or via auto-start)

4. **Logging**: All stop commands are logged on both server and client side for audit purposes

## Best Practices

1. **Use Confirmation**: Always confirm before stopping a PC client (implemented in frontend)

2. **Check Status**: Verify PC is connected before attempting to stop

3. **Monitor Logs**: Check both server and client logs after stopping to ensure clean shutdown

4. **Handle Auto-Start**: If you need to prevent auto-restart, configure system settings, not the stop command

5. **Graceful Shutdown**: The stop command performs graceful shutdown - allow a few seconds for cleanup

## Example Usage Flow

1. **Server**: User clicks "Stop" button on PC card in the PCs page
2. **Frontend**: Shows confirmation dialog
3. **User**: Confirms stop action
4. **Frontend**: Calls `POST /api/pcs/{pc_id}/stop`
5. **Backend**: Sends `stop_pc` WebSocket message to PC
6. **PC Client**: Receives message, sets `running = False`, calls `close()`, exits
7. **Server**: Updates PC status to offline
8. **Frontend**: Shows success message and refreshes PC list

## Related Features

- **Terminal Sessions**: Terminal sessions are automatically closed when PC stops
- **Streaming**: All active streams (camera, microphone, screen) are stopped
- **Script Execution**: Any running scripts are terminated (no graceful script shutdown)
- **File Downloads**: Pending file downloads are cancelled

## Version Information

- **Feature Added**: 2026-01-08
- **PC Client Version**: Latest (with stop_pc handler)
- **Server Version**: Latest (with stop endpoint)
- **Frontend Version**: Latest (with stop button)

---

**Note**: This feature is designed for administrative control and testing. For production environments, consider implementing additional access controls and audit logging.

