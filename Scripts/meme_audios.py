# -*- coding: utf-8 -*-
"""
Meme Audio Player
Plays random meme audio files from the Audios folder
Audios folder should be in the executable directory (malware exe directory)
"""
import os
import sys
import random
import subprocess
import time

# Import standardized path utilities
try:
    from path_utils import get_audios_path, find_folder
except ImportError:
    # Fallback if path_utils not available (shouldn't happen in normal execution)
    import os
    def get_audios_path():
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        if os.path.basename(script_dir) == 'Scripts':
            return os.path.join(os.path.dirname(script_dir), "Audios")
        return os.path.join(script_dir, "Audios")
    def find_folder(folder_name):
        audios_path = get_audios_path()
        if os.path.exists(audios_path) and os.path.isdir(audios_path):
            return audios_path
        return None

# Number of audio files to play (from server)
COUNT = int(os.environ.get("AUDIO_COUNT", "5"))

print("=" * 50)
print("   MEME AUDIO PLAYER")
print("=" * 50)
print("   Audio count: %d" % COUNT)
print("=" * 50)

# Find the Audios folder using standardized path resolution (executable directory)
audio_folder = find_folder("Audios")

if not audio_folder:
    audio_folder = get_audios_path()
    if not os.path.exists(audio_folder):
        print("[-] ERROR: Audios folder not found!")
        print(f"    Expected location: {audio_folder}")
        print("")
        print("    Please ensure 'Audios' folder is in the executable directory")
        print("    (relative to malware exe directory)")
        print("    with audio files named like: audio (1).mp3, audio (2).mp3, etc.")
        sys.exit(1)

print("[+] Found Audios folder: %s" % audio_folder)

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
