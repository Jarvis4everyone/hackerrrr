# Server-Side Issue: Log Messages Not Being Received

## Problem Description

The PC client is successfully sending log messages to the server, but the server is not receiving or processing them. The PC client console shows successful transmission, but logs are not appearing on the server side.

## Evidence from PC Client

The PC client logs show:
```
2026-01-07 18:05:09,280 - INFO - Sending complete log file to server: c:\Users\shres\Desktop\Hacking\PC\logs\open_app_20260107_180507_695e52fb.log
2026-01-07 18:05:09,280 - INFO - Complete log file sent successfully
2026-01-07 18:05:09,283 - INFO - Execution complete message sent: 695e52fb8e46bf7a69f2c824 - success
```

The client is sending messages, but they're not being received/processed by the server.

## Expected Message Format

### 1. Log Messages (type: "log")

The PC client sends log messages in the following format:

```json
{
    "type": "log",
    "script_name": "open_app.py",
    "execution_id": "695e52fb8e46bf7a69f2c824",
    "log_content": "[*] Executing script: open_app.py\n[*] Execution ID: 695e52fb8e46bf7a69f2c824\n...",
    "log_level": "INFO",
    "log_file_path": "logs/open_app_20260107_180507_695e52fb.log"
}
```

**Key Points:**
- `type`: Always `"log"`
- `script_name`: Name of the script being executed
- `execution_id`: Execution ID received from the script message (MUST match)
- `log_content`: The actual log content (can be multiline, can be the complete log file)
- `log_level`: One of `"INFO"`, `"ERROR"`, `"WARNING"`, `"DEBUG"`, or `"SUCCESS"`
- `log_file_path`: Path to the local log file (optional but recommended)

### 2. Execution Complete Messages (type: "execution_complete")

The PC client sends execution complete messages:

```json
{
    "type": "execution_complete",
    "execution_id": "695e52fb8e46bf7a69f2c824",
    "status": "success",
    "result": {
        "message": "Script 'open_app.py' executed successfully",
        "log_file": "logs/open_app_20260107_180507_695e52fb.log"
    }
}
```

**For Failed Executions:**
```json
{
    "type": "execution_complete",
    "execution_id": "695e52fb8e46bf7a69f2c824",
    "status": "failed",
    "error_message": "Error description here",
    "result": {
        "log_file": "logs/open_app_20260107_180507_695e52fb.log"
    }
}
```

## When Logs Are Sent

The PC client sends logs at multiple points:

1. **Initial log** - When script execution starts
2. **Chunked logs** - During script execution (stdout/stderr output in chunks)
3. **Success/Error log** - After script completes (with SUCCESS or ERROR level)
4. **Complete log file** - After execution, sends the ENTIRE log file content as a single log message
5. **Execution complete** - Final message with execution status

## What to Check on Server Side

### 1. WebSocket Message Handler

Verify that the server's WebSocket message handler is:
- ✅ Receiving messages with `type: "log"`
- ✅ Receiving messages with `type: "execution_complete"`
- ✅ Properly parsing the JSON message
- ✅ Extracting all required fields (script_name, execution_id, log_content, log_level)

### 2. Log Storage

Ensure the server is:
- ✅ Storing log messages in MongoDB (or your database)
- ✅ Associating logs with the correct `execution_id`
- ✅ Storing the `log_content` field (this contains the actual log text)
- ✅ Storing the `log_level` field
- ✅ Storing the `log_file_path` field (optional but useful)

### 3. Execution ID Matching

**CRITICAL:** The server must match log messages to executions using the `execution_id` field. The `execution_id` in log messages MUST match the `execution_id` from the original script message.

### 4. Message Processing

Check if the server is:
- ✅ Processing log messages asynchronously (not blocking)
- ✅ Handling large log content (complete log files can be several KB)
- ✅ Not silently dropping messages due to errors
- ✅ Logging errors when message processing fails

## Debugging Steps

### Step 1: Verify Message Reception

Add logging to the server's WebSocket message handler to confirm messages are being received:

```javascript
// Example (Node.js/JavaScript)
ws.on('message', (data) => {
    try {
        const message = JSON.parse(data);
        console.log('Received message type:', message.type);
        console.log('Message content:', JSON.stringify(message, null, 2));
        
        if (message.type === 'log') {
            console.log('LOG MESSAGE RECEIVED:');
            console.log('  Script:', message.script_name);
            console.log('  Execution ID:', message.execution_id);
            console.log('  Log Level:', message.log_level);
            console.log('  Log Content Length:', message.log_content?.length || 0);
        }
    } catch (error) {
        console.error('Error parsing message:', error);
    }
});
```

### Step 2: Check Database Storage

Verify that log messages are being stored:

```javascript
// After receiving log message
if (message.type === 'log') {
    await LogModel.create({
        pc_id: pcId,  // From WebSocket connection
        script_name: message.script_name,
        execution_id: message.execution_id,
        log_content: message.log_content,
        log_level: message.log_level,
        log_file_path: message.log_file_path,
        timestamp: new Date()
    });
    
    console.log('Log stored in database');
}
```

### Step 3: Check for Silent Failures

Ensure errors are being logged:

```javascript
try {
    // Process log message
    await processLogMessage(message);
} catch (error) {
    console.error('ERROR PROCESSING LOG MESSAGE:', error);
    console.error('Message that failed:', JSON.stringify(message, null, 2));
    // Don't silently fail - log the error!
}
```

### Step 4: Verify Execution ID Matching

Ensure logs are being associated with the correct execution:

```javascript
// When receiving log message
const execution = await ExecutionModel.findOne({ 
    execution_id: message.execution_id 
});

if (!execution) {
    console.warning(`Execution ${message.execution_id} not found for log message`);
    // Should we still store the log? Probably yes, but log the warning
}
```

## Expected Behavior

When a script is executed:

1. Server sends script message with `execution_id: "695e52fb8e46bf7a69f2c824"`
2. PC client receives script and starts execution
3. PC client sends initial log: `"[*] Executing script: open_app.py"`
4. PC client sends chunked logs during execution (stdout/stderr output)
5. PC client sends success log: `"Script 'open_app.py' executed successfully"` with level `"SUCCESS"`
6. PC client sends complete log file content (entire log file as one message)
7. PC client sends execution_complete message with status `"success"`

**All of these messages should be received and stored by the server.**

## API Endpoint Verification

According to the API documentation, the server should provide:

- `GET /api/logs` - List all logs
- `GET /api/logs/execution/{execution_id}` - Get logs for specific execution
- `GET /api/logs/pc/{pc_id}` - Get logs for specific PC
- `GET /api/logs/script/{script_name}` - Get logs for specific script

**Action:** Verify these endpoints are working and returning the log messages that the PC client is sending.

## Common Issues to Check

1. **Message Type Not Handled**: Server might not have a handler for `type: "log"`
2. **Execution ID Mismatch**: Server might be looking for logs with wrong execution_id format
3. **Database Schema**: Log model might be missing required fields
4. **Silent Errors**: Server might be catching errors but not logging them
5. **Message Size**: Large log files might be getting rejected due to size limits
6. **Async Processing**: Log processing might be failing silently in async operations
7. **WebSocket Connection**: Server might not be properly identifying which PC sent the message

## Test Case

To verify the fix works:

1. Send a script to a PC (e.g., `open_app.py`)
2. Check server logs to see if log messages are received
3. Query `GET /api/logs/execution/{execution_id}` to see if logs are stored
4. Verify the log content matches what the PC client sent

## Priority

**HIGH** - This is blocking log visibility on the server. Scripts execute successfully, but logs are not visible in the server dashboard/logs page.

---

**Last Updated:** 2026-01-07
**Issue Reported By:** PC Client Developer
**PC Client Version:** Latest (with real-time logging support)

