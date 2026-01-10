# PC Client Requirements & Dependencies Documentation

## Overview

This document lists **ALL** requirements and dependencies needed for the PC client to function properly with all scripts and features.

---

## Table of Contents

1. [Python Requirements](#python-requirements)
2. [System Requirements](#system-requirements)
3. [Python Package Dependencies](#python-package-dependencies)
4. [File Structure Requirements](#file-structure-requirements)
5. [Script-Specific Requirements](#script-specific-requirements)
6. [Installation Guide](#installation-guide)
7. [Verification Checklist](#verification-checklist)

---

## Python Requirements

### Python Version
- **Minimum**: Python 3.8
- **Recommended**: Python 3.10 or higher
- **Tested**: Python 3.10.10

### Python Standard Library Modules
These are included with Python and don't need installation:
- `asyncio` - Async operations
- `ctypes` - Windows API access
- `json` - JSON handling
- `logging` - Logging system
- `os` - Operating system interface
- `socket` - Network operations
- `subprocess` - Process management
- `sys` - System-specific parameters
- `tempfile` - Temporary file handling
- `threading` - Threading support
- `time` - Time operations
- `tkinter` - GUI (usually included, but may need separate install on Linux)

---

## System Requirements

### Operating System
- **Windows 10** (recommended)
- **Windows 11** (compatible)
- **Windows 8.1** (may work, not tested)

### Permissions
- **Administrator rights** (recommended for some features):
  - Input blocking (BlockInput API)
  - System-level operations
  - Some Windows API hooks

### Hardware
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: 500MB free space for logs and temporary files
- **Network**: Internet connection for WebSocket communication

---

## Python Package Dependencies

### Core Dependencies (Required for Basic Functionality)

```bash
pip install websockets
pip install aiohttp
```

### Script Execution Dependencies

#### 1. Hacker Attack Script (`hacker_attack.py`)

**Required:**
```bash
pip install pynput
```

**Optional (for better compatibility):**
```bash
pip install pyautogui
```

**What it does:**
- `pynput`: Input blocking (keyboard and mouse suppression)
- `pyautogui`: Fallback input blocking method

**Installation Notes:**
- `pynput` may require additional system dependencies on some systems
- If installation fails, try: `pip install pynput --upgrade`

#### 2. Fake BSOD Script (`fake_bsod.py`)

**Required:**
```bash
pip install qrcode[pil]
pip install Pillow
```

**What it does:**
- `qrcode`: Generates QR codes for BSOD screen
- `Pillow` (PIL): Image processing for QR code display

**Installation Notes:**
- `qrcode[pil]` installs both qrcode and Pillow
- Alternative: `pip install qrcode pillow` (separate)

#### 3. Audio Playback Scripts

**Required:**
- **Windows**: Built-in PowerShell MediaPlayer (no Python package needed)
- **Cross-platform**: `pygame` or `playsound` (optional)

**What it does:**
- Plays audio files (`.mp3`, `.wav`) during attacks

**Installation (if needed):**
```bash
pip install pygame
# OR
pip install playsound
```

#### 4. Screen Recording Scripts

**Required:**
```bash
pip install mss
pip install opencv-python
```

**What it does:**
- `mss`: Fast screen capture
- `opencv-python`: Video encoding and processing

**Installation Notes:**
- `opencv-python` is large (~100MB), may take time to install
- Alternative: `pip install opencv-python-headless` (smaller, no GUI)

#### 5. Camera/Microphone Scripts

**Required:**
```bash
pip install opencv-python
pip install pyaudio
```

**What it does:**
- `opencv-python`: Camera access
- `pyaudio`: Microphone access

**Installation Notes:**
- `pyaudio` may require system audio libraries
- On Windows, may need: `pip install pipwin && pipwin install pyaudio`

#### 6. File Operations Scripts

**Required:**
- No additional packages (uses standard library)

#### 7. Network Scripts

**Required:**
```bash
pip install requests
```

**What it does:**
- HTTP requests to server
- File uploads/downloads

---

## Complete Installation Command

### All-in-One Installation

```bash
# Core dependencies
pip install websockets aiohttp

# Script execution dependencies
pip install pynput pyautogui

# GUI and QR code
pip install qrcode[pil] Pillow

# Screen and camera
pip install mss opencv-python

# Audio (optional, Windows has built-in)
pip install pygame

# Network
pip install requests

# Microphone (if needed)
pip install pyaudio
```

### Alternative: Requirements File

Create `requirements.txt`:
```txt
websockets>=10.0
aiohttp>=3.8.0
pynput>=1.7.6
pyautogui>=0.9.54
qrcode[pil]>=7.4.2
Pillow>=10.0.0
mss>=9.0.1
opencv-python>=4.8.0
pygame>=2.5.0
requests>=2.31.0
pyaudio>=0.2.14
```

Install with:
```bash
pip install -r requirements.txt
```

---

## File Structure Requirements

### Required Folders

The PC client must create/copy these folders to the user's home directory:

1. **`C:\Users\{USERNAME}\Photos`**
   - Contains: `1.jpg`, `2.jpg`, ..., `9.jpg` (wallpaper images)
   - Contains: `attack.mp3` (audio file for hacker attack)
   - **Source**: Copied from PC client's `Photos` folder on startup

2. **`C:\Users\{USERNAME}\Audios`**
   - Contains: Audio files for various scripts
   - **Source**: Copied from PC client's `Audios` folder on startup

3. **`C:\Users\{USERNAME}\logs`** (or `C:\Users\{USERNAME}\Desktop\Hacking\PC\logs`)
   - Contains: Execution logs
   - **Created**: Automatically by PC client

### Required Files

1. **`attack.mp3`**
   - Location: `C:\Users\{USERNAME}\Photos\attack.mp3` OR `C:\Users\{USERNAME}\Audios\attack.mp3`
   - Purpose: Audio played during hacker attack
   - Duration: ~38 seconds

2. **Wallpaper Images**
   - Files: `1.jpg`, `2.jpg`, ..., `9.jpg`
   - Location: `C:\Users\{USERNAME}\Photos\`
   - Purpose: Wallpaper cycling during hacker attack

---

## Script-Specific Requirements

### Hacker Attack Script

**Dependencies:**
- `pynput` (required for input blocking)
- `pyautogui` (optional, fallback)

**Files Required:**
- `C:\Users\{USERNAME}\Photos\attack.mp3` (audio file)
- `C:\Users\{USERNAME}\Photos\1.jpg` through `9.jpg` (wallpaper images)

**System Requirements:**
- Windows 10/11
- Administrator rights (recommended for input blocking)
- Multiple monitors supported

**Features:**
- Matrix terminals (15 terminals)
- Input blocking (keyboard + mouse)
- Audio playback
- Wallpaper cycling
- Popup messages
- Desktop manipulation

### Fake BSOD Script

**Dependencies:**
- `qrcode[pil]` (required for QR code)
- `Pillow` (required for image processing)
- `tkinter` (usually included with Python)

**System Requirements:**
- Windows 10/11
- GUI support (display)

**Features:**
- Fullscreen BSOD display
- QR code generation
- Progress animation
- Timer display

### Screen Recording Scripts

**Dependencies:**
- `mss` (required for screen capture)
- `opencv-python` (required for video encoding)

**System Requirements:**
- Windows 10/11
- Sufficient RAM for video encoding
- Disk space for video files

### Camera/Microphone Scripts

**Dependencies:**
- `opencv-python` (camera)
- `pyaudio` (microphone)

**System Requirements:**
- Webcam (for camera scripts)
- Microphone (for audio scripts)
- Drivers installed

---

## Installation Guide

### Step 1: Install Python

1. Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```bash
   python --version
   pip --version
   ```

### Step 2: Install Core Dependencies

```bash
pip install websockets aiohttp
```

### Step 3: Install Script Dependencies

```bash
# For hacker attack
pip install pynput pyautogui

# For fake BSOD
pip install qrcode[pil]

# For screen recording
pip install mss opencv-python

# For camera/microphone
pip install opencv-python pyaudio

# For network operations
pip install requests
```

### Step 4: Verify Installation

```bash
python -c "import websockets; import pynput; import qrcode; import cv2; print('All dependencies installed!')"
```

### Step 5: Setup File Structure

Ensure these folders exist and contain required files:
- `C:\Users\{USERNAME}\Photos\` (with `1.jpg`-`9.jpg` and `attack.mp3`)
- `C:\Users\{USERNAME}\Audios\` (with audio files)

---

## Verification Checklist

### Core Functionality
- [ ] Python 3.8+ installed
- [ ] `websockets` installed and importable
- [ ] `aiohttp` installed and importable
- [ ] PC client can connect to server
- [ ] Heartbeats are being sent

### Hacker Attack Script
- [ ] `pynput` installed: `python -c "import pynput"`
- [ ] `pyautogui` installed: `python -c "import pyautogui"`
- [ ] `attack.mp3` exists in `C:\Users\{USERNAME}\Photos\` or `C:\Users\{USERNAME}\Audios\`
- [ ] Wallpaper images (`1.jpg`-`9.jpg`) exist in `C:\Users\{USERNAME}\Photos\`
- [ ] Script executes without errors
- [ ] Input blocking works
- [ ] Audio plays
- [ ] Matrix terminals open and stay open
- [ ] Wallpaper cycles

### Fake BSOD Script
- [ ] `qrcode` installed: `python -c "import qrcode"`
- [ ] `Pillow` installed: `python -c "from PIL import Image"`
- [ ] `tkinter` available: `python -c "import tkinter"`
- [ ] Script displays BSOD correctly
- [ ] QR code is visible
- [ ] Text is positioned correctly (right of QR code)

### Screen Recording
- [ ] `mss` installed: `python -c "import mss"`
- [ ] `opencv-python` installed: `python -c "import cv2"`
- [ ] Script can capture screen
- [ ] Video files are created

### Camera/Microphone
- [ ] `opencv-python` installed
- [ ] `pyaudio` installed: `python -c "import pyaudio"`
- [ ] Camera accessible (if webcam present)
- [ ] Microphone accessible (if microphone present)

---

## Troubleshooting

### Issue: `pynput` Installation Fails

**Solution:**
```bash
pip install --upgrade pip
pip install pynput --no-cache-dir
```

**Alternative:** Use `pyautogui` as fallback (less reliable)

### Issue: `pyaudio` Installation Fails

**Solution (Windows):**
```bash
pip install pipwin
pipwin install pyaudio
```

**Alternative:** Use `sounddevice`:
```bash
pip install sounddevice
```

### Issue: `opencv-python` Too Large

**Solution:** Use headless version:
```bash
pip install opencv-python-headless
```

### Issue: `tkinter` Not Available

**Solution (Windows):**
- Usually included with Python
- If missing, reinstall Python with "tcl/tk" option

**Solution (Linux):**
```bash
sudo apt-get install python3-tk
```

### Issue: Matrix Terminals Close Immediately

**Solution:**
- Ensure script uses `/K` instead of `/C` in cmd command
- Script should have `pause` at the end
- Check that flag file is being read correctly

### Issue: Input Blocking Doesn't Work

**Solution:**
1. Install `pynput`: `pip install pynput`
2. Run PC client as Administrator (recommended)
3. Check that `pynput` listeners are running:
   ```python
   from pynput import keyboard, mouse
   # Test if it works
   ```

### Issue: Audio Doesn't Play

**Solution:**
1. Check `attack.mp3` exists in correct location
2. Verify file path in script logs
3. Test PowerShell MediaPlayer manually:
   ```powershell
   Add-Type -AssemblyName presentationCore
   $player = New-Object System.Windows.Media.MediaPlayer
   $player.Open('C:\Users\{USERNAME}\Photos\attack.mp3')
   $player.Play()
   ```

### Issue: QR Code Not Displayed

**Solution:**
1. Install `qrcode[pil]`: `pip install qrcode[pil]`
2. Verify installation: `python -c "import qrcode; from PIL import Image"`
3. Check script logs for errors

---

## Quick Reference: Installation Commands

### Minimal Installation (Core Only)
```bash
pip install websockets aiohttp
```

### Standard Installation (Most Scripts)
```bash
pip install websockets aiohttp pynput qrcode[pil] mss opencv-python requests
```

### Full Installation (All Features)
```bash
pip install websockets aiohttp pynput pyautogui qrcode[pil] Pillow mss opencv-python pygame requests pyaudio
```

### Development Installation
```bash
pip install -r requirements.txt
```

---

## Version Compatibility

### Tested Versions

| Package | Minimum | Recommended | Tested |
|---------|---------|-------------|--------|
| Python | 3.8 | 3.10+ | 3.10.10 |
| websockets | 10.0 | 11.0+ | 12.0 |
| aiohttp | 3.8.0 | 3.9.0+ | 3.9.1 |
| pynput | 1.7.6 | 1.7.6+ | 1.7.6 |
| qrcode | 7.4.0 | 7.4.2+ | 7.4.2 |
| Pillow | 10.0.0 | 10.1.0+ | 10.1.0 |
| mss | 9.0.0 | 9.0.1+ | 9.0.1 |
| opencv-python | 4.8.0 | 4.8.1+ | 4.8.1 |

---

## Notes

- **Always use virtual environments** for Python projects
- **Update packages regularly**: `pip install --upgrade package_name`
- **Check for conflicts** if multiple scripts use same packages
- **Test after installation** to verify everything works
- **Keep requirements.txt updated** with all dependencies

---

## Support

If you encounter issues:
1. Check this documentation first
2. Verify all dependencies are installed
3. Check script execution logs
4. Test individual components
5. Refer to script-specific documentation

---

**Last Updated:** 2026-01-10  
**Version:** 1.0  
**Status:** Complete

