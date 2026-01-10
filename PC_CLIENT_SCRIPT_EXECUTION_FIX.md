# PC Client Script Execution Fix & Best Practices

## Critical Issue: Logging Errors During Script Execution

### Problem

When scripts are executed, you may see errors like:
```
--- Logging error ---
Traceback (most recent call last):
  File "logging\__init__.py", line 1103, in emit
AttributeError: 'NoneType' object has no attribute 'write'
```

**Root Cause:**
- The logging system tries to write to `stdout`/`stderr` during script execution
- When scripts redirect or capture `stdout`/`stderr`, these streams become `None` or closed
- Background tasks (like heartbeat loop) continue logging while streams are redirected
- This causes the logging handler to fail

### Solution: Fix Logging Configuration

#### Step 1: Configure Logging to Handle None Streams

In your `pc_client.py`, ensure logging handlers can handle `None` or closed streams:

```python
import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Setup logging with proper error handling"""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create file handler (always works, even if stdout is redirected)
    log_file = os.path.join(logs_dir, 'pc_client.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Create console handler with None check
    class SafeStreamHandler(logging.StreamHandler):
        """Stream handler that handles None or closed streams"""
        def emit(self, record):
            try:
                # Check if stream is available
                if self.stream is None:
                    return
                # Check if stream has write method
                if not hasattr(self.stream, 'write'):
                    return
                # Try to write
                super().emit(record)
            except (AttributeError, OSError, ValueError):
                # Stream is closed or None - silently ignore
                pass
    
    # Only add console handler if stdout is available
    if sys.stdout is not None and hasattr(sys.stdout, 'write'):
        try:
            console_handler = SafeStreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        except (AttributeError, OSError):
            # stdout not available - skip console handler
            pass
```

#### Step 2: Protect Logging During Script Execution

When executing scripts, temporarily disable console logging:

```python
def execute_script(self, script_content, script_name, server_url, execution_id):
    """Execute a script with proper logging protection"""
    import sys
    import io
    from contextlib import redirect_stdout, redirect_stderr
    
    # Store original stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # Create capture streams
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    # Temporarily disable console logging handlers
    console_handlers = [
        h for h in logging.getLogger().handlers
        if isinstance(h, logging.StreamHandler) and h.stream in (sys.stdout, sys.stderr)
    ]
    
    # Disable console handlers during script execution
    for handler in console_handlers:
        handler.setLevel(logging.CRITICAL)  # Only show critical errors
    
    try:
        # Redirect stdout/stderr for script execution
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        # Execute script
        # ... your script execution code ...
        
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        
        # Re-enable console handlers
        for handler in console_handlers:
            handler.setLevel(logging.INFO)
        
        # Get captured output
        stdout_content = stdout_capture.getvalue()
        stderr_capture_content = stderr_capture.getvalue()
```

#### Step 3: Fix Background Task Logging

For background tasks (like heartbeat loop), use file logging only:

```python
async def _hardware_heartbeat_loop(self):
    """Background task for hardware info and heartbeat"""
    # Use a logger that only writes to file, not console
    file_logger = logging.getLogger('pc_client.file')
    
    # Remove console handlers from this logger
    for handler in list(file_logger.handlers):
        if isinstance(handler, logging.StreamHandler):
            file_logger.removeHandler(handler)
    
    # Add only file handler
    if not file_logger.handlers:
        log_file = os.path.join(self.logs_dir, 'pc_client.log')
        file_handler = RotatingFileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        file_logger.addHandler(file_handler)
    
    while self.running:
        try:
            # Use file_logger instead of regular logger
            file_logger.info("Detected IP via socket method: ...")
            
            # Send heartbeat
            await self.send_heartbeat()
            
        except Exception as e:
            # Log to file only
            file_logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
        
        await asyncio.sleep(5)
```

### Complete Fix Implementation

Here's a complete example of how to fix logging in `pc_client.py`:

```python
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

class SafeLoggingSetup:
    """Safe logging setup that handles None streams"""
    
    @staticmethod
    def setup_logging(logs_dir):
        """Setup logging with file and safe console handlers"""
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        
        # File handler (always works)
        log_file = os.path.join(logs_dir, 'pc_client.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
        
        # Safe console handler
        class SafeConsoleHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    if self.stream is None or not hasattr(self.stream, 'write'):
                        return
                    super().emit(record)
                except (AttributeError, OSError, ValueError):
                    pass
        
        # Only add if stdout is available
        if sys.stdout and hasattr(sys.stdout, 'write'):
            try:
                console_handler = SafeConsoleHandler(sys.stdout)
                console_handler.setFormatter(
                    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
                )
                logger.addHandler(console_handler)
            except:
                pass
        
        return logger

# Usage in pc_client.py
def main():
    # Setup logging first
    logs_dir = os.path.join(os.path.expanduser("~"), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logger = SafeLoggingSetup.setup_logging(logs_dir)
    
    # ... rest of your code
```

---

## Script Execution Best Practices

### 1. Never Redirect stdout/stderr in Scripts

**❌ Bad:**
```python
# In your script
import sys
sys.stdout = open('output.txt', 'w')  # This breaks logging!
sys.stderr = open('error.txt', 'w')
```

**✅ Good:**
```python
# Use file handles directly
with open('output.txt', 'w') as f:
    f.write("Output data")
```

### 2. Use Print Statements

**✅ Good:**
```python
print("[*] Starting attack...")
print(f"[OK] Processed {count} items")
```

**❌ Avoid:**
```python
sys.stdout.write("Starting attack...")  # May not be captured
```

### 3. Handle Errors Gracefully

**✅ Good:**
```python
try:
    result = risky_operation()
    print(f"[OK] Success: {result}")
except Exception as e:
    print(f"[!] Error: {e}")
    # Continue or exit gracefully
```

### 4. Don't Modify sys.stdout/stderr in Scripts

Scripts should **never** modify `sys.stdout` or `sys.stderr`. The PC client handles output capture automatically.

---

## Fixing the Hacker Attack Script

The `hacker_attack.py` script should work correctly if:

1. **PC client logging is fixed** (see above)
2. **Script doesn't redirect stdout/stderr**
3. **Script uses print() statements**
4. **Script handles errors gracefully**

### Example: Proper Script Structure

```python
# hacker_attack.py
import os
import sys
import time

# ✅ Good: Use print statements
print("=" * 60)
print("HACKER ATTACK - INITIALIZING...")
print("=" * 60)

try:
    # Your attack code here
    print("[*] Starting attack...")
    
    # ✅ Good: Handle errors
    try:
        result = some_operation()
        print(f"[OK] Operation completed: {result}")
    except Exception as e:
        print(f"[!] Error in operation: {e}")
        # Continue or exit
    
    print("[OK] Attack completed successfully!")
    
except Exception as e:
    # ✅ Good: Catch all errors
    print(f"[!] Fatal error: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)
```

---

## Testing Your Fix

### Test 1: Simple Script
```python
# test_simple.py
print("Test 1: Simple print")
print("Test 2: Print with variable")
x = 42
print(f"Test 3: Variable value: {x}")
```

**Expected:** No logging errors, output captured correctly.

### Test 2: Script with Errors
```python
# test_error.py
print("Starting test...")
try:
    raise ValueError("Test error")
except Exception as e:
    print(f"Caught error: {e}")
print("Test completed")
```

**Expected:** Error caught and printed, no logging errors.

### Test 3: Background Task Logging
Run the PC client and let it send heartbeats for 30 seconds.

**Expected:** No logging errors in heartbeat loop.

---

## Complete PC Client Logging Fix

Add this to your `pc_client.py`:

```python
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_safe_logging(logs_dir):
    """Setup logging that won't fail when stdout/stderr are None"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler (always works)
    log_file = os.path.join(logs_dir, 'pc_client.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(file_handler)
    
    # Safe console handler
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                if self.stream is None:
                    return
                if not hasattr(self.stream, 'write'):
                    return
                super().emit(record)
            except (AttributeError, OSError, ValueError, TypeError):
                # Silently ignore - stream is closed or None
                pass
    
    # Add console handler only if stdout is available
    if sys.stdout is not None:
        try:
            console_handler = SafeStreamHandler(sys.stdout)
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(console_handler)
        except:
            pass
    
    return logger

# In your main() function:
def main():
    # Setup logging
    logs_dir = os.path.join(os.path.expanduser("~"), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    logger = setup_safe_logging(logs_dir)
    
    logger.info("PC Client starting...")
    # ... rest of your code
```

---

## Summary

**Key Points:**
1. ✅ **Fix logging handlers** to handle None/closed streams
2. ✅ **Use file logging** for background tasks
3. ✅ **Disable console logging** during script execution
4. ✅ **Scripts should use print()** not sys.stdout.write()
5. ✅ **Scripts should never redirect** stdout/stderr
6. ✅ **Handle errors gracefully** in scripts

**Result:**
- No more logging errors during script execution
- Scripts execute correctly
- Background tasks continue logging to file
- All output is captured and sent to server

---

## For PC Client Developers

**Priority Fixes:**
1. **Implement SafeStreamHandler** (see code above)
2. **Setup file logging** for background tasks
3. **Disable console logging** during script execution
4. **Test with hacker_attack.py** to verify fix

**Testing Checklist:**
- [ ] No logging errors when running scripts
- [ ] Script output is captured correctly
- [ ] Background tasks (heartbeat) don't cause errors
- [ ] File logging works even when console logging fails
- [ ] Scripts complete successfully

---

## Version Information

- **Document Created:** 2026-01-10
- **Issue:** Logging errors during script execution
- **Status:** ✅ Fix documented and ready for implementation
- **Priority:** HIGH - Affects all script execution

