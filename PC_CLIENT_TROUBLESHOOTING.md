# PC Client Troubleshooting Guide

## Common Errors and Solutions

### Error: `'NoneType' object has no attribute 'write'`

**Symptoms:**
```
AttributeError: 'NoneType' object has no attribute 'write'
Traceback:
  File "pc_client.py", line 1731, in write
    self.file_obj.write(s)
```

**Cause:**
This error occurs when the PC client's `FileWriter` class tries to write to stdout/stderr, but the file object is `None` or has been closed. This can happen in edge cases where:
- The script execution environment has redirected or closed stdout/stderr
- The script is running in a context where standard streams are not available
- System-level redirections have occurred

**Solution:**
This has been fixed in the PC client code. The `FileWriter.write()` and `flush()` methods now include proper null checks and error handling:

```python
def write(self, s):
    if s:
        # Write to original stdout/stderr (if available)
        if self.file_obj is not None:
            try:
                self.file_obj.write(s)
                self.file_obj.flush()
            except (AttributeError, OSError):
                # Handle case where file_obj doesn't have write method or is closed
                pass
        # Write to log file
        if self.log_file_obj is not None:
            try:
                self.log_file_obj.write(s)
                self.log_file_obj.flush()
            except (AttributeError, OSError):
                pass
        # Also buffer for later retrieval and sending
        self.buffer.write(s)
```

**For Script Developers:**
- Scripts should use standard `print()` statements - they will be captured automatically
- Avoid manually redirecting `sys.stdout` or `sys.stderr` in your scripts
- If you need to write to files, use `open()` and file handles directly
- The PC client automatically captures all print output and sends it to the server

**Status:** ✅ Fixed in PC client version with null checks

---

## Script Execution Best Practices

### 1. Use Standard Print Statements
```python
# ✅ Good
print("Starting script...")
print(f"Processing {count} items")

# ❌ Avoid
sys.stdout.write("Starting script...")
```

### 2. Handle Errors Gracefully
```python
# ✅ Good
try:
    result = risky_operation()
    print(f"[OK] Operation completed: {result}")
except Exception as e:
    print(f"[!] Error: {e}")
    # Script continues or exits gracefully

# ❌ Avoid
result = risky_operation()  # May crash script
```

### 3. Don't Redirect stdout/stderr
```python
# ❌ Avoid - This can cause issues
sys.stdout = open('output.txt', 'w')
sys.stderr = open('error.txt', 'w')

# ✅ Good - Use file handles directly
with open('output.txt', 'w') as f:
    f.write("Output data")
```

### 4. Use Environment Variables
```python
# ✅ Good - Use provided environment variables
import os
server_url = os.environ.get('SERVER_URL')
pc_id = os.environ.get('PC_ID')
execution_id = os.environ.get('EXECUTION_ID')
```

---

## Reporting Issues

If you encounter errors that aren't covered here:

1. **Check the execution logs** in the server UI (Logs page)
2. **Check the PC client logs** in the terminal where `pc_client.py` is running
3. **Verify environment variables** are set correctly (SERVER_URL, PC_ID, EXECUTION_ID)
4. **Test with a simple script** first to isolate the issue

---

## Version Information

- **PC Client Version:** Latest (with FileWriter null checks)
- **Last Updated:** 2026-01-08
- **Fixed Issues:** NoneType write error in FileWriter class

