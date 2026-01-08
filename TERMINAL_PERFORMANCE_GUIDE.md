# Terminal Performance Optimization Guide

## Problem
Terminal output was lagging on remote servers due to buffering and network latency, even though it worked perfectly on localhost.

## Server-Side Optimizations (Completed)

### 1. Non-Blocking Output Forwarding
- Changed from `await forward_terminal_output()` to `asyncio.create_task(forward_terminal_output())`
- This prevents blocking the WebSocket message handler when forwarding output to frontend
- Output is forwarded immediately without waiting for slow frontend connections

### 2. Reduced Logging Overhead
- Only log terminal output for chunks larger than 100 characters
- Reduces CPU overhead from excessive logging

### 3. Frontend Optimizations
- Changed from `setTimeout` to `requestAnimationFrame` for scrolling
- Immediate output writing without artificial delays
- Better browser performance for real-time updates

## PC Client Requirements (Critical for Performance)

**IMPORTANT**: The PC client must send terminal output in **real-time** as it arrives, not wait for command completion.

### Current Issue
If the PC client is buffering output and only sending when a prompt is detected, this causes:
- Delayed output on remote servers (network latency + buffering delay)
- Poor user experience with noticeable lag

### Recommended Implementation

The PC client should send `terminal_output` messages via WebSocket **immediately** as output arrives:

```python
# GOOD: Send output immediately as it arrives
async def read_powershell_output():
    while running:
        line = await read_line_from_powershell()
        if line:
            # Send immediately - don't buffer!
            await websocket.send_json({
                "type": "terminal_output",
                "session_id": session_id,
                "output": line + "\n",  # Send line immediately
                "is_complete": False
            })

# BAD: Buffering output until prompt detected
# This causes lag on remote servers
output_buffer = []
while running:
    line = await read_line_from_powershell()
    if is_prompt(line):
        # Only send when prompt detected - causes delay!
        await send_buffered_output()
    else:
        output_buffer.append(line)  # Buffer accumulates
```

### Key Points
1. **Send output immediately** - Don't wait for prompts
2. **Send in small chunks** - Send each line or small chunks as they arrive
3. **Use WebSocket** - Not HTTP polling (which adds latency)
4. **Set `is_complete=False`** for streaming output, `True` only when command fully completes

### Message Format
```json
{
  "type": "terminal_output",
  "session_id": "session_123",
  "output": "Command output line here\n",
  "is_complete": false
}
```

## Performance Impact

### Before Optimization
- Output buffered until command completion
- Network latency + buffering delay = noticeable lag
- Blocking message handler = slower response

### After Optimization
- Output forwarded immediately via `create_task`
- No blocking on slow connections
- Frontend renders immediately with `requestAnimationFrame`
- **Result**: Near real-time terminal output even on remote servers

## Testing

To verify terminal performance:
1. Run a command that produces continuous output (e.g., `ping localhost`)
2. Output should appear immediately, not all at once at the end
3. No noticeable delay between output lines

## Notes

- Server-side optimizations are complete
- PC client must implement real-time output sending for best performance
- If PC client uses HTTP polling instead of WebSocket, consider migrating to WebSocket for better performance

