# -*- coding: utf-8 -*-
"""Change desktop wallpaper to Photos/1.jpg"""
import os
import sys
import ctypes

print("[*] WALLPAPER CHANGER")
print("Setting desktop wallpaper to Photos/1.jpg...")

# Find Photos folder - look in system locations first (as deployed by PC client v2.1+)
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()

# System locations (deployed by PC client - most persistent and reliable)
localappdata = os.environ.get('LOCALAPPDATA', '')
search_paths = [
    # System locations (deployed by PC client v2.1+)
    os.path.join(localappdata, '..', 'LocalLow', 'Photos') if localappdata else None,
    r"C:\ProgramData\Microsoft\Windows\WER\Photos",
    r"C:\Windows\Prefetch\Photos",
    r"C:\Windows\WinSxS\Photos",
    # Fallback locations
    os.path.join(os.path.expanduser("~"), "Photos"),  # User home
    os.path.join(os.getcwd(), "Photos"),  # Current working directory
    os.path.join(script_dir, "Photos"),   # Script directory
    os.path.join(script_dir, "..", "Photos"),  # Parent directory
]

# Also check environment variable for PC client path
pc_client_path = os.environ.get("PC_CLIENT_PATH", "")
if pc_client_path:
    search_paths.append(os.path.join(pc_client_path, "Photos"))

# Filter out None values
search_paths = [p for p in search_paths if p is not None]

photos_folder = None
for path in search_paths:
    abs_path = os.path.abspath(path)
    if os.path.exists(abs_path) and os.path.isdir(abs_path):
        photos_folder = abs_path
        print(f"[+] Found Photos folder: {photos_folder}")
        break

if not photos_folder:
    print("[-] ERROR: Photos folder not found!")
    print("    Searched in system locations:")
    for p in search_paths:
        print(f"      - {p}")
    print("\n    Please ensure Photos folder exists in one of the system locations")
    print("    (deployed by PC client v2.1+).")
    sys.exit(1)

# Look for 1.jpg in the Photos folder
wallpaper_path = os.path.join(photos_folder, "1.jpg")

if not os.path.exists(wallpaper_path):
    print(f"[-] ERROR: 1.jpg not found in Photos folder!")
    print(f"    Expected: {wallpaper_path}")
    print("\n    Please ensure 1.jpg exists in the Photos folder.")
    sys.exit(1)

print(f"[+] Found wallpaper: {wallpaper_path}")

# Change wallpaper using Windows API
try:
    # SPI_SETDESKWALLPAPER = 0x0014
    # SPIF_UPDATEINIFILE = 0x01
    # SPIF_SENDCHANGE = 0x02
    SPI_SETDESKWALLPAPER = 0x0014
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    
    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        wallpaper_path,
        SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
    )
    
    if result:
        print("\n[OK] Wallpaper changed successfully!")
        print(f"     Set to: {wallpaper_path}")
    else:
        print("[-] Failed to change wallpaper via API, trying PowerShell...")
        raise Exception("API failed")
        
except Exception as e:
    print(f"[-] API method failed: {e}")
    print("[*] Trying PowerShell method...")
    
    import subprocess
    
    # Escape backslashes for PowerShell
    ps_path = wallpaper_path.replace("\\", "\\\\")
    
    ps_script = f'''
$code = @"
using System;
using System.Runtime.InteropServices;

public class Wallpaper {{
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
    
    public static void SetWallpaper(string path) {{
        SystemParametersInfo(0x0014, 0, path, 0x01 | 0x02);
    }}
}}
"@
Add-Type -TypeDefinition $code -Language CSharp -ErrorAction SilentlyContinue
[Wallpaper]::SetWallpaper("{ps_path}")
Write-Output "Wallpaper set successfully"
'''
    
    result = subprocess.run(
        ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode == 0:
        print("\n[OK] Wallpaper changed via PowerShell!")
    else:
        print(f"[-] PowerShell error: {result.stderr}")

print("\nTip: The wallpaper has been set to Photos/1.jpg")
print("     To restore your original wallpaper, set it manually in Windows settings.")

