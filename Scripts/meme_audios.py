# -*- coding: utf-8 -*-
"""
Meme Audio Player
Plays random meme audio files from the Audios folder
Audios folder should be in the PC client main directory
"""
import os
import sys
import random
import subprocess
import time

# Number of audio files to play (from server)
COUNT = int(os.environ.get("AUDIO_COUNT", "5"))

print("=" * 50)
print("   MEME AUDIO PLAYER")
print("=" * 50)
print("   Audio count: %d" % COUNT)
print("=" * 50)

# Find the Audios folder - same logic as wallpaper finding Hacked.jpg
script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()

search_paths = [
    os.path.join(os.getcwd(), "Audios"),                    # Current working directory
    os.path.join(script_dir, "Audios"),                     # Script directory
    os.path.join(script_dir, "..", "Audios"),               # Parent directory
    os.path.join(os.path.expanduser("~"), "Audios"),        # User home
]

# Check PC_CLIENT_PATH environment variable (set by PC client)
pc_client_path = os.environ.get("PC_CLIENT_PATH", "")
if pc_client_path:
    search_paths.insert(0, os.path.join(pc_client_path, "Audios"))

# Find the Audios folder
audio_folder = None
for path in search_paths:
    if os.path.exists(path) and os.path.isdir(path):
        audio_folder = path
        print("[+] Found Audios folder: %s" % path)
        break

if not audio_folder:
    print("[-] ERROR: Audios folder not found!")
    print("    Searched in:")
    for p in search_paths:
        print("      - %s" % p)
    print("")
    print("    Please ensure 'Audios' folder is in the PC client main directory")
    print("    with audio files named like: audio (1).mp3, audio (2).mp3, etc.")
    sys.exit(1)

# Find all audio files (mp3, wav)
audio_files = []
for f in os.listdir(audio_folder):
    if f.lower().endswith(('.mp3', '.wav', '.wma', '.m4a')):
        audio_files.append(os.path.join(audio_folder, f))

audio_files.sort()
print("[*] Found %d audio files" % len(audio_files))

if not audio_files:
    print("[-] ERROR: No audio files found in %s" % audio_folder)
    sys.exit(1)

# Select random files
actual_count = min(COUNT, len(audio_files))
if COUNT > len(audio_files):
    print("[!] Requested %d but only %d files available" % (COUNT, len(audio_files)))

selected_files = random.sample(audio_files, actual_count)
print("[*] Selected %d random audio files" % len(selected_files))
print("")

# Play each file
print("[*] Playing audio files...")
print("-" * 50)

for i, filepath in enumerate(selected_files, 1):
    filename = os.path.basename(filepath)
    print("[%d/%d] %s" % (i, len(selected_files), filename))
    
    # Play using PowerShell MediaPlayer
    ps_script = '''
Add-Type -AssemblyName presentationCore
$player = New-Object System.Windows.Media.MediaPlayer
$player.Open('%s')
$player.Play()
Start-Sleep -Milliseconds 500
$timeout = 0
while ($player.NaturalDuration.HasTimeSpan -eq $false -and $timeout -lt 30) {
    Start-Sleep -Milliseconds 100
    $timeout++
}
if ($player.NaturalDuration.HasTimeSpan) {
    $duration = [math]::Ceiling($player.NaturalDuration.TimeSpan.TotalSeconds)
    Start-Sleep -Seconds $duration
}
$player.Stop()
$player.Close()
''' % filepath.replace("'", "''").replace("\\", "\\\\")
    
    try:
        subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True,
            timeout=120
        )
        print("       [OK]")
    except subprocess.TimeoutExpired:
        print("       [Timeout]")
    except Exception as e:
        print("       [Error: %s]" % str(e))

print("-" * 50)
print("")
print("[OK] Played %d audio files!" % len(selected_files))
print("=" * 50)
