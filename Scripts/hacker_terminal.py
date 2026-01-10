# -*- coding: utf-8 -*-
"""Matrix Rain Effect - Opens 10 terminal windows with green matrix effect"""
import subprocess
import os
import sys
import tempfile
import time

# Get settings from environment variables
duration = int(os.environ.get("MATRIX_DURATION", "15"))
num_terminals = int(os.environ.get("MATRIX_TERMINALS", "10"))
message = os.environ.get("MATRIX_MESSAGE", "YOUR PC HAS BEEN HACKED! CONGRATS!")

print("[*] MATRIX RAIN ATTACK")
print(f"[*] Opening {num_terminals} terminal windows...")
print(f"[*] Duration: {duration} seconds each")
print(f"[*] Message: {message}")
print("[*] Launching terminals (non-blocking)...")

# Use GUI matrix terminal instead of cmd.exe
# Create launcher script that uses matrix_gui_terminal.py
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
matrix_gui_source = os.path.join(script_dir, "matrix_gui_terminal.py")
if not os.path.exists(matrix_gui_source):
    matrix_gui_source = os.path.join(os.path.dirname(script_dir), "matrix_gui_terminal.py")

# Copy matrix_gui_terminal.py to temp directory
matrix_gui_temp = os.path.join(tempfile.gettempdir(), "matrix_gui_terminal.py")
if os.path.exists(matrix_gui_source):
    import shutil
    shutil.copy2(matrix_gui_source, matrix_gui_temp)

# Create launcher script for each terminal
matrix_script_template = '''
import sys
import os
import tempfile

# Set environment variables for the GUI terminal
os.environ["MATRIX_DURATION"] = "{duration}"
os.environ["MATRIX_MESSAGE"] = "{message}"
os.environ["MATRIX_AUTO_CLOSE"] = "true"

# Import and run the GUI terminal
try:
    # Try to import from temp directory
    matrix_gui_path = os.path.join(tempfile.gettempdir(), "matrix_gui_terminal.py")
    if os.path.exists(matrix_gui_path):
        import importlib.util
        spec = importlib.util.spec_from_file_location("matrix_gui_terminal", matrix_gui_path)
        matrix_gui_terminal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(matrix_gui_terminal)
        matrix_gui_terminal.main()
    else:
        # Try to find it in script directory
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        possible_paths = [
            os.path.join(script_dir, "matrix_gui_terminal.py"),
            os.path.join(os.path.dirname(script_dir), "matrix_gui_terminal.py"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("matrix_gui_terminal", path)
                matrix_gui_terminal = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(matrix_gui_terminal)
                matrix_gui_terminal.main()
                break
        else:
            print("ERROR: Could not find matrix_gui_terminal.py")
            input("Press Enter to exit...")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
'''

# Write the launcher script to temp files (one for each terminal)
temp_files = []
for i in range(num_terminals):
    temp_file = os.path.join(tempfile.gettempdir(), f"matrix_terminal_{i}.py")
    matrix_script = matrix_script_template.format(duration=duration, message=message)
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(matrix_script)
    temp_files.append(temp_file)

# Get Python executable path
python_exe = sys.executable
if not python_exe or not os.path.exists(python_exe):
    # Try common Python paths
    username = os.environ.get('USERNAME', '')
    python_paths = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python310', 'python.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python311', 'python.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python312', 'python.exe'),
        r'C:\Python310\python.exe',
        r'C:\Python311\python.exe',
        r'C:\Python312\python.exe',
        r'C:\Program Files\Python310\python.exe',
        r'C:\Program Files\Python311\python.exe',
        r'C:\Program Files\Python312\python.exe',
    ]
    if username:
        python_paths.extend([
            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python310\python.exe',
            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python311\python.exe',
            rf'C:\Users\{username}\AppData\Local\Programs\Python\Python312\python.exe',
        ])
    for path in python_paths:
        if os.path.exists(path):
            python_exe = path
            break
    else:
        python_exe = 'python'  # Fallback to PATH

print(f"[*] Using Python: {python_exe}")

# Find or use the GUI matrix terminal script
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
matrix_gui_script = os.path.join(script_dir, "matrix_gui_terminal.py")

# If not found, try other locations
if not os.path.exists(matrix_gui_script):
    possible_paths = [
        os.path.join(os.path.dirname(script_dir), "matrix_gui_terminal.py"),
        os.path.join(os.path.dirname(os.path.dirname(script_dir)), "Scripts", "matrix_gui_terminal.py"),
        os.path.join(tempfile.gettempdir(), "matrix_gui_terminal.py"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            matrix_gui_script = path
            break

if not matrix_gui_script or not os.path.exists(matrix_gui_script):
    print("[!] ERROR: matrix_gui_terminal.py not found!")
    print("[!] Please ensure matrix_gui_terminal.py is in the Scripts directory")
    print("[!] Terminals will not be launched without the GUI script")
    sys.exit(1)

# Use GUI terminals (no fallback - GUI is required)
    # Use GUI terminals
    print(f"[*] Using GUI matrix terminals from: {matrix_gui_script}")
    
    # Calculate positions for terminals (distribute across screen)
    screen_width = 1920  # Default, will be adjusted
    screen_height = 1080
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.destroy()
    except:
        pass
    
    terminals_per_row = min(4, num_terminals)
    terminal_width = 850
    terminal_height = 450
    spacing = 20
    
    for i in range(num_terminals):
        # Calculate position
        row = i // terminals_per_row
        col = i % terminals_per_row
        x = col * (terminal_width + spacing) + spacing
        y = row * (terminal_height + spacing) + spacing
        
        # Create launcher script
        launcher_script = os.path.join(tempfile.gettempdir(), f"matrix_launcher_{i}.py")
        with open(launcher_script, 'w', encoding='utf-8') as f:
            f.write('''import sys
import os
import importlib.util

# Set environment variables
os.environ["TERMINAL_MESSAGE"] = "{}"

# Load and run the GUI terminal module
gui_script_path = r"{}"
try:
    spec = importlib.util.spec_from_file_location("matrix_gui_terminal", gui_script_path)
    matrix_gui_terminal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matrix_gui_terminal)
    
    # Create terminal with position and duration
    terminal = matrix_gui_terminal.MatrixTerminal(
        title="Hacker Terminal {}",
        width={},
        height={},
        x={},
        y={},
        flag_file=None,
        duration={},
        message="{}"
    )
    terminal.run()
except Exception as e:
    import traceback
    print(f"Error: {{e}}")
    traceback.print_exc()
    input("Press Enter to exit...")
'''.format(message,
           matrix_gui_script.replace("\\", "\\\\"),
           i+1,
           terminal_width,
           terminal_height,
           x, y,
           duration,
           message))
        
        # Launch Python script
        try:
            if python_exe == 'python':
                subprocess.Popen(
                    [python_exe, launcher_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            else:
                subprocess.Popen(
                    [python_exe, launcher_script],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            print(f"[+] Terminal {i+1}/{num_terminals} launched (GUI)")
        except Exception as e:
            print(f"[!] Error launching terminal {i+1}: {e}")
        
        time.sleep(0.3)  # Small delay between terminals

print()
print("[OK] All terminals launched!")
print(f"[*] Each will run for {duration} seconds then show message and close")
print("[*] This script is done - terminals run independently")
