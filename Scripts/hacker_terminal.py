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

# Create the matrix rain script that will run in each terminal
matrix_script = f'''
import random
import time
import os
import sys

# Set console to green on black
os.system('color 0a')
os.system('mode con: cols=100 lines=35')

chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*"
katakana = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
all_chars = chars + katakana

try:
    width = os.get_terminal_size().columns
except:
    width = 100

columns = [0] * width

start = time.time()
duration = {duration}

try:
    while time.time() - start < duration:
        line = ""
        for i in range(width):
            if random.random() > 0.95:
                columns[i] = random.randint(5, 20)
            
            if columns[i] > 0:
                line += random.choice(all_chars)
                columns[i] -= 1
            else:
                line += " "
        
        print(line)
        time.sleep(0.03)
except KeyboardInterrupt:
    pass

# Show the hacked message
os.system('cls')
os.system('color 0c')  # Red on black

message = "{message}"
width = 100

print()
print()
print("=" * width)
print()
print(" " * ((width - len(message)) // 2) + message)
print()
print("=" * width)
print()
print()

# Dramatic effect
for i in range(3):
    time.sleep(0.3)
    os.system('color 0a')  # Green
    time.sleep(0.3)
    os.system('color 0c')  # Red

time.sleep(2)
# Terminal will close automatically
'''

# Write the script to temp files (one for each terminal to avoid conflicts)
temp_files = []
for i in range(num_terminals):
    temp_file = os.path.join(tempfile.gettempdir(), f"matrix_rain_{i}.py")
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
