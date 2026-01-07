# -*- coding: utf-8 -*-
"""
Path Utilities - Standardized path resolution for all scripts
All scripts should use these functions to get paths relative to the executable directory
"""
import os
import sys


def get_base_path():
    """
    Get the base path (executable directory).
    
    When running as executable: Returns directory containing the .exe file
    When running as script: Returns directory containing the script or pc_client.py
    
    Returns:
        str: Base path (executable directory)
    """
    # Check if running as executable (frozen with PyInstaller)
    if getattr(sys, 'frozen', False):
        # Running as executable - base path is directory containing .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Running as script - try to find pc_client.py directory first
        # Check PC_CLIENT_PATH environment variable (set by PC client)
        pc_client_path = os.environ.get("PC_CLIENT_PATH", "")
        if pc_client_path and os.path.exists(pc_client_path):
            base_path = pc_client_path
        else:
            # Running as script - try to find pc_client.py directory first
            # Check PC_CLIENT_PATH environment variable (set by PC client)
            pc_client_path = os.environ.get("PC_CLIENT_PATH", "")
            if pc_client_path and os.path.exists(pc_client_path):
                base_path = pc_client_path
            else:
                # Get directory containing this path_utils.py script
                try:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    # If this is in Scripts folder, go up one level to get PC client directory
                    if os.path.basename(script_dir) == 'Scripts':
                        base_path = os.path.dirname(script_dir)
                    else:
                        base_path = script_dir
                except NameError:
                    # Fallback to current working directory
                    base_path = os.getcwd()
    
    return os.path.abspath(base_path)


def get_audios_path():
    """
    Get the path to the Audios folder (relative to executable directory).
    
    Returns:
        str: Path to Audios folder
    """
    return os.path.join(get_base_path(), "Audios")


def get_photos_path():
    """
    Get the path to the Photos folder (relative to executable directory).
    
    Returns:
        str: Path to Photos folder
    """
    return os.path.join(get_base_path(), "Photos")


def get_build_path():
    """
    Get the path to the build folder (relative to executable directory).
    
    Returns:
        str: Path to build folder
    """
    return os.path.join(get_base_path(), "build")


def get_logs_path():
    """
    Get the path to the logs folder (relative to executable directory).
    
    Returns:
        str: Path to logs folder
    """
    return os.path.join(get_base_path(), "logs")


def find_folder(folder_name):
    """
    Find a folder relative to executable directory.
    First checks executable directory, then falls back to common locations.
    
    Args:
        folder_name: Name of folder to find (e.g., "Audios", "Photos")
    
    Returns:
        str or None: Path to folder if found, None otherwise
    """
    # Primary location: executable directory
    primary_path = os.path.join(get_base_path(), folder_name)
    if os.path.exists(primary_path) and os.path.isdir(primary_path):
        return primary_path
    
    # Fallback: check if running as script and folder exists in script directory
    if not getattr(sys, 'frozen', False):
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        fallback_path = os.path.join(script_dir, folder_name)
        if os.path.exists(fallback_path) and os.path.isdir(fallback_path):
            return fallback_path
        
        # Check parent directory
        parent_path = os.path.join(os.path.dirname(script_dir), folder_name)
        if os.path.exists(parent_path) and os.path.isdir(parent_path):
            return parent_path
    
    return None


def get_file_path(relative_path):
    """
    Get absolute path for a file relative to executable directory.
    
    Args:
        relative_path: Relative path from executable directory (e.g., "Audios/audio (1).mp3")
    
    Returns:
        str: Absolute path to the file
    """
    return os.path.join(get_base_path(), relative_path.replace('/', os.sep).replace('\\', os.sep))


def ensure_folder_exists(folder_path):
    """
    Ensure a folder exists, create it if it doesn't.
    
    Args:
        folder_path: Path to folder
    
    Returns:
        str: Path to folder (created if needed)
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
    return folder_path

