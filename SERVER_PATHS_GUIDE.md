# Server-Side Paths Guide

This document explains the paths that the server should use when requesting files from the PC client.

## Important: Use Executable Paths Only - NO USER FOLDERS

**CRITICAL**: The server MUST use paths relative to the PC client's executable directory (the malware exe directory). 

**DO NOT use paths from user folders** like:
- ❌ `C:\Users\...`
- ❌ `C:\Users\Username\Documents\...`
- ❌ `C:\Users\Username\Pictures\...`
- ❌ `C:\Users\Username\Music\...`
- ❌ Any absolute paths from user directories

**ONLY use paths from the malware executable directory**:
- ✅ `Audios/audio (1).mp3` (relative to exe directory)
- ✅ `build/WindowsMalwareProtection/...` (relative to exe directory)
- ✅ `logs/...` (relative to exe directory)

The PC client includes specific folders (`build` and `Audios`) in the executable, and the server should ONLY request files from these folders relative to the malware exe directory.

## Folder Structure in Executable

When the PC client is built as an executable, the following folders are included:

```
Windows Malware Protection.exe (executable)
├── build/              # Build files folder (included in executable)
│   └── WindowsMalwareProtection/
│       └── (build artifacts)
├── Audios/             # Audio files folder (included in executable)
│   ├── audio (1).mp3
│   ├── audio (2).mp3
│   ├── audio (3).mp3
│   └── ... (all audio files)
├── logs/               # Logs folder (created at runtime)
└── config.json         # Configuration file (optional)
```

## Path Resolution

The PC client uses `get_base_path()` to determine the base directory:
- **When running as executable**: Base path = directory containing the `.exe` file
- **When running as script**: Base path = directory containing `pc_client.py`

All folder paths are resolved relative to this base path.

## Server File Request Paths

### Build Folder

**Path**: `build/` (relative to executable directory)

**Example paths**:
- `build/WindowsMalwareProtection/Windows Malware Protection.pkg`
- `build/WindowsMalwareProtection/Analysis-00.toc`
- `build/WindowsMalwareProtection/...`

**Server should request**: `build/...` (relative path from executable directory)

### Audios Folder

**Path**: `Audios/` (relative to executable directory)

**Example paths**:
- `Audios/audio (1).mp3`
- `Audios/audio (2).mp3`
- `Audios/audio (10).mp3`
- `Audios/...` (all audio files)

**Server should request**: `Audios/audio (1).mp3` (relative path from executable directory)

**Note**: Do NOT request audio files from user folders like `C:\Users\...\Music\...` or `C:\Users\...\Downloads\...`. Only use paths from the `Audios/` folder in the executable directory.

### Photos Folder (if included in executable)

**Path**: `Photos/` (relative to executable directory, if included)

**Example paths**:
- `Photos/1.jpg`
- `Photos/2.jpg`
- `Photos/attack.mp3`
- `Photos/...` (all photo/image files)

**Server should request**: `Photos/1.jpg` (relative path from executable directory)

**Note**: Do NOT request photos from user folders like `C:\Users\...\Pictures\...` or `C:\Users\...\Downloads\...`. Only use paths from the `Photos/` folder in the executable directory (if it exists in the exe).

## File Download Request Format

When the server requests a file download, it should use relative paths from the executable directory:

```json
{
  "type": "download_file",
  "file_path": "Audios/audio (1).mp3",
  "request_id": "unique-request-id"
}
```

Or for build files:

```json
{
  "type": "download_file",
  "file_path": "build/WindowsMalwareProtection/Windows Malware Protection.pkg",
  "request_id": "unique-request-id"
}
```

Or for photos/images (if Photos folder exists in executable):

```json
{
  "type": "download_file",
  "file_path": "Photos/1.jpg",
  "request_id": "unique-request-id"
}
```

## Important Notes

1. **DO NOT use absolute paths**: The server should NEVER send absolute paths like `C:\Users\...` or `/home/user/...`
2. **DO NOT use user folder paths**: The server should NEVER request files from user directories like:
   - `C:\Users\...`
   - `C:\Users\Username\Documents\...`
   - `C:\Users\Username\Pictures\...`
   - `C:\Users\Username\Music\...`
   - Any other user folder paths
3. **ONLY use executable directory paths**: The server should ONLY request files from the malware executable directory:
   - `build/` folder (relative to exe directory)
   - `Audios/` folder (relative to exe directory)
   - `Photos/` folder (relative to exe directory, if included in executable)
   - `logs/` folder (relative to exe directory, for log files)
4. **Path separator**: Use forward slashes `/` in paths (the PC client will handle Windows backslashes automatically)
5. **Case sensitivity**: On Windows, paths are case-insensitive, but it's best to match the exact case used in the folder names
6. **All paths must be relative**: All file paths must be relative to the malware executable directory, never absolute paths

## PC Client Implementation

The PC client provides helper functions to get the correct paths:

```python
# Get base path (executable directory)
base_path = get_base_path()

# Get build folder path
build_path = get_build_path()  # Returns: base_path/build

# Get Audios folder path
audios_path = get_audios_path()  # Returns: base_path/Audios
```

When handling file download requests, the PC client:
1. Receives the relative path from the server (e.g., `Audios/audio (1).mp3`)
2. Resolves it relative to `get_base_path()`
3. Validates that the file is within allowed folders
4. Sends the file to the server

## Security Considerations

The PC client should validate that requested file paths:
- Are relative paths (not absolute)
- Are within allowed folders (`build/`, `Audios/`, `Photos/`, `logs/`)
- Do not contain path traversal attempts (`../`, `..\\`, etc.)
- Do not reference user folders (`Users/`, `Documents/`, `Pictures/`, `Music/`, etc.)

## Example Server Implementation

```python
# Server-side code example
def request_file_from_pc(pc_id, file_path):
    """
    Request a file from a PC client.
    
    Args:
        pc_id: The PC identifier
        file_path: Relative path from executable directory (e.g., "Audios/audio (1).mp3")
    
    Returns:
        File content or error
    """
    # Validate path is relative (not absolute)
    if os.path.isabs(file_path):
        raise ValueError("File path must be relative to executable directory, not absolute")
    
    # Reject user folder paths
    user_folder_indicators = ['Users', 'Documents', 'Pictures', 'Music', 'Downloads', 'Desktop']
    if any(indicator in file_path for indicator in user_folder_indicators):
        raise ValueError("File path must be from executable directory, not user folders")
    
    # Validate path is in allowed folders (relative to exe directory)
    allowed_folders = ['build', 'Audios', 'Photos', 'logs']
    first_part = file_path.split('/')[0].split('\\')[0]
    if first_part not in allowed_folders:
        raise ValueError(f"File path must be in one of: {allowed_folders} (relative to executable directory)")
    
    # Send download_file request to PC client
    message = {
        "type": "download_file",
        "file_path": file_path,  # Relative path from exe directory
        "request_id": generate_unique_id()
    }
    send_to_pc(pc_id, message)
```

## Testing

To test file access:
1. Ensure the executable includes the `build` and `Audios` folders
2. Request files using relative paths: `Audios/audio (1).mp3`
3. Verify the PC client can locate and send the files
4. Verify the server receives the correct file content

## Troubleshooting

### File not found errors
- Check that the file path is relative (not absolute)
- Verify the folder name matches exactly (`Audios` not `audios` or `audio`)
- Ensure the file exists in the executable directory structure

### Path traversal attempts
- The PC client should reject paths containing `../` or `..\\`
- Only allow paths within `build/`, `Audios/`, and `logs/` folders

### Case sensitivity issues
- On Windows, paths are case-insensitive, but use exact case for compatibility
- Use `Audios` (capital A) not `audios`

