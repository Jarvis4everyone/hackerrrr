# 🐛 Server-Side Log Saving Issue - Developer Guide

## Problem Statement

The PC client is successfully sending log messages to the server, but the logs are **not being saved in MongoDB**. The PC client reports successful log transmission, but the server is not persisting the logs.

## Evidence from PC Client

From the PC client logs:
```
2026-01-07 20:56:30,652 - INFO - ✓ Sent complete log file (single message): full_report.py - INFO (8872 chars, ~232 lines)
2026-01-07 20:56:30,657 - INFO -   Server should save this as ONE document with execution_id: 695e7aef27da7632261f6102
2026-01-07 20:56:30,657 - INFO - ✓ Complete log file sent successfully (single message: 8872 chars, 232 lines)
```

The PC client is:
- ✅ Sending log messages successfully
- ✅ Including all required fields
- ✅ Using correct message format
- ✅ Sending complete log file content

**But the server is NOT saving these logs to MongoDB.**

## Log Message Format

The PC client sends log messages in the following format:

```json
{
  "type": "log",
  "script_name": "full_report.py",
  "execution_id": "695e7aef27da7632261f6102",
  "log_content": "[*] Executing script: full_report.py\n[*] Execution ID: 695e7aef27da7632261f6102\n... (complete log file content) ...",
  "log_level": "INFO",
  "log_file_path": "c:\\Users\\shres\\Desktop\\Hacking\\PC\\logs\\full_report_20260107_205535_695e7aef.log"
}
```

### Message Fields

- **`type`**: Always `"log"` for log messages
- **`script_name`**: Name of the script that was executed (e.g., `"full_report.py"`)
- **`execution_id`**: Unique execution ID (UUID format, e.g., `"695e7aef27da7632261f6102"`)
- **`log_content`**: **Complete log file content as a single string** (all output from script execution)
- **`log_level`**: Log level (usually `"INFO"`, can be `"ERROR"`, `"WARNING"`, etc.)
- **`log_file_path`**: Path to the log file on the PC (optional but recommended)

**Note:** `pc_id` is NOT included in the message - the server should identify the PC from the WebSocket connection.

## Expected Server Behavior

### 1. Receive Log Message

The server should handle `type: "log"` messages in the WebSocket message handler:

```javascript
// Example (Node.js/Express)
websocket.on('message', async (message) => {
  const data = JSON.parse(message);
  
  if (data.type === 'log') {
    await handleLogMessage(data, pc_id); // pc_id from WebSocket connection
  }
});
```

### 2. Save to MongoDB

The server should save the log to MongoDB with the following schema:

```javascript
{
  execution_id: String,      // From message.execution_id
  pc_id: String,             // From WebSocket connection (NOT from message)
  script_name: String,       // From message.script_name
  log_content: String,       // From message.log_content (complete log file)
  log_level: String,         // From message.log_level
  log_file_path: String,     // From message.log_file_path (optional)
  created_at: Date,          // Timestamp when log was saved
  updated_at: Date           // Timestamp when log was last updated
}
```

### 3. CRITICAL: Single Document Per Execution

**IMPORTANT:** The PC client sends **ONE log message per execution_id** containing the **complete log file content**. The server should:

- **Save as a SINGLE document** per `execution_id`
- **Use `execution_id` as a unique identifier** (or part of compound key)
- **If a log already exists for an `execution_id`, UPDATE it** (don't create duplicate)
- **Do NOT create multiple documents** for the same `execution_id`

### 4. MongoDB Save Implementation

```javascript
// Example MongoDB save (Node.js with Mongoose)
async function saveLogToMongoDB(logData, pcId) {
  try {
    const logDocument = {
      execution_id: logData.execution_id,
      pc_id: pcId,  // From WebSocket connection, NOT from message
      script_name: logData.script_name,
      log_content: logData.log_content,  // Complete log file content
      log_level: logData.log_level || 'INFO',
      log_file_path: logData.log_file_path || null,
      created_at: new Date(),
      updated_at: new Date()
    };
    
    // Use upsert to update if exists, create if not
    await LogModel.findOneAndUpdate(
      { execution_id: logData.execution_id },  // Find by execution_id
      logDocument,
      { upsert: true, new: true }  // Create if not exists, update if exists
    );
    
    console.log(`✓ Log saved for execution_id: ${logData.execution_id}`);
    return true;
  } catch (error) {
    console.error(`✗ Error saving log to MongoDB: ${error}`);
    return false;
  }
}
```

## Common Issues and Solutions

### Issue 1: Log Messages Not Being Handled

**Symptom:** Log messages are received but not processed.

**Solution:**
- Check WebSocket message handler for `type: "log"` case
- Ensure log handler is being called
- Add logging to verify messages are received

```javascript
// Add logging
if (data.type === 'log') {
  console.log(`[LOG] Received log message: execution_id=${data.execution_id}, script=${data.script_name}`);
  await handleLogMessage(data, pc_id);
}
```

### Issue 2: Logs Not Saved to MongoDB

**Symptom:** Log handler is called but nothing appears in MongoDB.

**Solution:**
- Check MongoDB connection
- Verify database/collection names
- Check for MongoDB errors in server logs
- Ensure `execution_id` is being used correctly

```javascript
// Add error handling
try {
  await saveLogToMongoDB(logData, pcId);
} catch (error) {
  console.error(`[ERROR] Failed to save log: ${error.message}`);
  console.error(error.stack);
}
```

### Issue 3: Multiple Documents for Same Execution

**Symptom:** Multiple log documents created for the same `execution_id`.

**Solution:**
- Use `findOneAndUpdate` with `upsert: true` instead of `create`
- Ensure `execution_id` is used as unique identifier
- Don't use `execution_id` + `pc_id` as compound key (use only `execution_id`)

```javascript
// WRONG - Creates multiple documents
await LogModel.create(logDocument);

// CORRECT - Updates if exists, creates if not
await LogModel.findOneAndUpdate(
  { execution_id: logData.execution_id },
  logDocument,
  { upsert: true, new: true }
);
```

### Issue 4: Log Content Not Complete

**Symptom:** Only partial log content is saved.

**Solution:**
- Ensure `log_content` field is large enough (use `String` type, not limited length)
- Don't truncate `log_content` before saving
- Save the complete `log_content` as received

```javascript
// MongoDB Schema (Mongoose example)
const logSchema = new Schema({
  execution_id: { type: String, required: true, unique: true },
  pc_id: { type: String, required: true },
  script_name: { type: String, required: true },
  log_content: { type: String, required: true },  // No maxlength - save complete content
  log_level: { type: String, default: 'INFO' },
  log_file_path: { type: String },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now }
});
```

### Issue 5: WebSocket Connection Closes After Log Send

**Symptom:** Connection closes immediately after log is sent.

**Solution:**
- This is normal - connection may close after sending
- Ensure log is saved **before** connection closes
- Use async/await to ensure save completes
- Don't close connection until log is saved

```javascript
// CORRECT - Wait for save to complete
if (data.type === 'log') {
  await saveLogToMongoDB(data, pcId);  // Wait for save
  // Connection can close after this
}

// WRONG - Don't wait
if (data.type === 'log') {
  saveLogToMongoDB(data, pcId);  // Fire and forget - might not save!
}
```

## Verification Steps

### 1. Check Server Logs

Add logging to verify logs are being received:

```javascript
websocket.on('message', async (message) => {
  const data = JSON.parse(message);
  
  if (data.type === 'log') {
    console.log(`[LOG RECEIVED] execution_id: ${data.execution_id}`);
    console.log(`[LOG RECEIVED] script_name: ${data.script_name}`);
    console.log(`[LOG RECEIVED] log_content length: ${data.log_content.length} chars`);
    
    const saveResult = await saveLogToMongoDB(data, pcId);
    console.log(`[LOG SAVE] Result: ${saveResult ? 'SUCCESS' : 'FAILED'}`);
  }
});
```

### 2. Check MongoDB

Query MongoDB to verify logs are being saved:

```javascript
// Check if log exists
const log = await LogModel.findOne({ execution_id: '695e7aef27da7632261f6102' });
console.log('Log found:', log ? 'YES' : 'NO');
if (log) {
  console.log('Log content length:', log.log_content.length);
  console.log('Log content preview:', log.log_content.substring(0, 200));
}
```

### 3. Test with Simple Log

Send a test log message to verify the flow:

```javascript
// Test log message
const testLog = {
  type: 'log',
  script_name: 'test.py',
  execution_id: 'test-execution-id-123',
  log_content: 'Test log content',
  log_level: 'INFO',
  log_file_path: '/path/to/test.log'
};

await saveLogToMongoDB(testLog, 'test-pc-id');
```

## Required Server-Side Fixes

1. **Implement Log Message Handler**
   - Add `type: "log"` case in WebSocket message handler
   - Extract `execution_id`, `script_name`, `log_content`, etc. from message
   - Get `pc_id` from WebSocket connection (not from message)

2. **Save to MongoDB**
   - Use `findOneAndUpdate` with `upsert: true`
   - Use `execution_id` as unique identifier
   - Save complete `log_content` (don't truncate)
   - Include `pc_id`, `script_name`, `log_level`, `log_file_path`, timestamps

3. **Error Handling**
   - Catch and log all errors
   - Don't let errors prevent other messages from being processed
   - Log MongoDB save failures

4. **Verification**
   - Add logging to verify logs are received
   - Add logging to verify logs are saved
   - Query MongoDB to confirm logs are persisted

## Example Complete Implementation

```javascript
// WebSocket message handler
websocket.on('message', async (message) => {
  try {
    const data = JSON.parse(message);
    const pcId = getPcIdFromWebSocket(websocket);  // Get from connection
    
    if (data.type === 'log') {
      console.log(`[LOG] Received log for execution_id: ${data.execution_id}`);
      
      // Save to MongoDB
      const logDocument = {
        execution_id: data.execution_id,
        pc_id: pcId,
        script_name: data.script_name,
        log_content: data.log_content,  // Complete log content
        log_level: data.log_level || 'INFO',
        log_file_path: data.log_file_path || null,
        created_at: new Date(),
        updated_at: new Date()
      };
      
      try {
        await LogModel.findOneAndUpdate(
          { execution_id: data.execution_id },
          logDocument,
          { upsert: true, new: true }
        );
        console.log(`[LOG] ✓ Saved log for execution_id: ${data.execution_id}`);
      } catch (dbError) {
        console.error(`[LOG] ✗ Failed to save log: ${dbError.message}`);
        console.error(dbError);
      }
    }
  } catch (error) {
    console.error(`[ERROR] Error processing message: ${error.message}`);
  }
});
```

## Testing

After implementing the fix:

1. **Run a script** from the server
2. **Check server logs** - should see "LOG RECEIVED" and "LOG SAVE SUCCESS"
3. **Query MongoDB** - should find log document with `execution_id`
4. **Verify log content** - should contain complete log file content

## Summary

- **PC Client Status:** ✅ Working correctly - sending logs successfully
- **Server Status:** ❌ Not saving logs to MongoDB
- **Fix Required:** Server-side implementation to handle `type: "log"` messages and save to MongoDB
- **Critical:** Use `execution_id` as unique identifier, save as single document per execution

---

**Last Updated:** 2026-01-07  
**Priority:** HIGH - Logs are critical for debugging and monitoring script executions

