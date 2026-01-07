# -*- coding: utf-8 -*-
"""Change desktop wallpaper to Photos/1.jpg"""
import os
import sys
import ctypes

# Import standardized path utilities
try:
    from path_utils import get_photos_path, find_folder
except ImportError:
    # Fallback if path_utils not available (shouldn't happen in normal execution)
    import os
    def get_photos_path():
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        if os.path.basename(script_dir) == 'Scripts':
            return os.path.join(os.path.dirname(script_dir), "Photos")
        return os.path.join(script_dir, "Photos")
    def find_folder(folder_name):
        photos_path = get_photos_path()
        if os.path.exists(photos_path) and os.path.isdir(photos_path):
            return photos_path
        return None

print("[*] WALLPAPER CHANGER")
print("Setting desktop wallpaper to Photos/1.jpg...")

# Find Photos folder using standardized path resolution (executable directory)
photos_folder = find_folder("Photos")

if not photos_folder:
    photos_folder = get_photos_path()
    if not os.path.exists(photos_folder):
        print("[-] ERROR: Photos folder not found!")
        print(f"    Expected location: {photos_folder}")
        print("\n    Please ensure Photos folder exists in the executable directory")
        print("    (relative to malware exe directory).")
        sys.exit(1)

print(f"[+] Found Photos folder: {photos_folder}")

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

