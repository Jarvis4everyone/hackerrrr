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

# Launch terminals independently (non-blocking)
# Create batch files for each terminal to ensure proper execution
for i in range(num_terminals):
    # Create a batch file that will execute the Python script
    batch_file = os.path.join(tempfile.gettempdir(), f"matrix_terminal_{i}.bat")
    with open(batch_file, 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('color 0a\n')
        f.write('title Hacker Terminal {}\n'.format(i+1))
        f.write('mode con: cols=100 lines=35\n')
        if python_exe == 'python':
            f.write(f'python "{temp_files[i]}"\n')
        else:
            python_path_escaped = python_exe.replace('"', '""')
            f.write(f'"{python_path_escaped}" "{temp_files[i]}"\n')
        f.write('if errorlevel 1 (\n')
        f.write('    echo.\n')
        f.write('    echo [ERROR] Failed to execute Python script\n')
        f.write('    pause\n')
        f.write(')\n')
        f.write('pause\n')
    
    # Launch using start command with /K to keep terminal open
    # Use quotes around batch file path to handle spaces
    batch_file_quoted = f'"{batch_file}"'
    cmd = f'start "Hacker Terminal {i+1}" cmd /K {batch_file_quoted}'
    
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[+] Terminal {i+1}/{num_terminals} launched")
    except Exception as e:
        print(f"[!] Error launching terminal {i+1}: {e}")
    
    time.sleep(0.5)  # Small delay between terminals

print()
print("[OK] All terminals launched!")
print(f"[*] Each will run for {duration} seconds then show message and close")
print("[*] This script is done - terminals run independently")
