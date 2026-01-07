# Server-Side Paths Guide

This document explains the paths that the server should use when requesting files from the PC client.

## Important: Use Executable Paths Only

**CRITICAL**: The server MUST use paths relative to the PC client's executable directory. The PC client includes specific folders (`build` and `Audios`) in the executable, and the server should ONLY request files from these folders.

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

## Important Notes

1. **DO NOT use absolute paths**: The server should NEVER send absolute paths like `C:\Users\...` or `/home/user/...`
2. **DO NOT use paths outside executable directory**: The server should ONLY request files from:
   - `build/` folder
   - `Audios/` folder
   - `logs/` folder (for log files)
3. **Path separator**: Use forward slashes `/` in paths (the PC client will handle Windows backslashes automatically)
4. **Case sensitivity**: On Windows, paths are case-insensitive, but it's best to match the exact case used in the folder names

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
- Are within allowed folders (`build/`, `Audios/`, `logs/`)
- Do not contain path traversal attempts (`../`, `..\\`, etc.)

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
    # Validate path is relative
    if os.path.isabs(file_path):
        raise ValueError("File path must be relative, not absolute")
    
    # Validate path is in allowed folders
    allowed_folders = ['build', 'Audios', 'logs']
    first_part = file_path.split('/')[0].split('\\')[0]
    if first_part not in allowed_folders:
        raise ValueError(f"File path must be in one of: {allowed_folders}")
    
    # Send download_file request to PC client
    message = {
        "type": "download_file",
        "file_path": file_path,  # Relative path
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

