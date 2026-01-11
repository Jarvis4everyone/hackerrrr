"""
Script Service - Business logic for script management
Reads scripts directly from filesystem (no MongoDB storage)
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import re
from app.config import settings
from app.models.script import Script
import logging

logger = logging.getLogger(__name__)


class ScriptService:
    """Service for managing scripts - reads from filesystem only"""
    
    @staticmethod
    def detect_script_parameters(script_content: str) -> Dict[str, Dict[str, Any]]:
        """
        Detect required parameters from script content by parsing os.environ.get calls
        Returns dict of {param_name: {type, default, description}}
        """
        parameters = {}
        
        # Pattern to match os.environ.get("VAR_NAME", "default") or os.environ.get("VAR_NAME", "") or os.environ.get("VAR_NAME")
        # This pattern handles empty strings as defaults too
        pattern = r'os\.environ\.get\(["\']([^"\']+)["\'](?:\s*,\s*["\']([^"\']*)["\'])?\)'
        
        matches = re.finditer(pattern, script_content)
        for match in matches:
            var_name = match.group(1)
            # Get default value - group(2) can be empty string or None
            default_value = match.group(2) if match.group(2) is not None else None
            
            # Skip common system variables
            if var_name in ['CC_PC_ID', 'PC_CLIENT_PATH', 'TEMP', 'USERNAME', 'USER', 
                           'COMPUTERNAME', 'USERDOMAIN', 'APPDATA', 'PROGRAMDATA', 
                           'USERPROFILE', 'LOCALAPPDATA']:
                continue
            
            # Determine parameter type and description
            param_type = "text"
            description = ""
            
            if var_name == "APP_NAME":
                param_type = "text"
                description = "Application name to open/close (e.g., 'chrome', 'notepad')"
                # APP_NAME is required even if it has a default empty string
                # The scripts check "if not APP_NAME" so it's effectively required
            elif var_name == "APP_ARGS":
                param_type = "text"
                description = "Optional arguments for the application"
            elif var_name == "DISABLE_DURATION":
                param_type = "number"
                description = "Duration in seconds (max 300)"
            elif var_name == "BSOD_DURATION":
                param_type = "number"
                description = "Duration in seconds (max 300)"
            elif var_name == "SPEAK_MESSAGE":
                param_type = "textarea"
                description = "Text message to speak"
            elif var_name == "TTS_VOICE":
                param_type = "select"
                description = "Voice ID"
            elif var_name == "POPUP_MESSAGE":
                param_type = "textarea"
                description = "Message to display in popup"
            elif var_name == "POPUP_TITLE":
                param_type = "text"
                description = "Popup window title"
            elif var_name == "POPUP_ICON":
                param_type = "select"
                description = "Icon type (error, warning, info, question)"
            # MATRIX TERMINAL PARAMETERS REMOVED - FIXED VALUES ONLY
            elif var_name == "FILE_PATH":
                param_type = "text"
                description = "Path to file to read"
            elif var_name == "MAX_FILE_SIZE":
                param_type = "number"
                description = "Maximum file size in MB (1-100)"
            elif var_name == "MAX_LINES":
                param_type = "number"
                description = "Maximum lines to read (100-10000)"
            elif var_name == "DAYS_BACK":
                param_type = "number"
                description = "Number of days to look back (1-30)"
            elif var_name == "MAX_FILES":
                param_type = "number"
                description = "Maximum files to return (10-5000)"
            elif var_name == "EXPLORER_PATH":
                param_type = "text"
                description = "Directory path to explore"
            elif var_name == "EXPLORER_DEPTH":
                param_type = "number"
                description = "Maximum directory depth"
            elif var_name == "SEARCH_PATTERN":
                param_type = "text"
                description = "File search pattern (e.g., '*.txt', '*')"
            elif var_name == "SEARCH_PATH":
                param_type = "text"
                description = "Directory path to search"
            elif var_name == "MAX_RESULTS":
                param_type = "number"
                description = "Maximum number of results"
            elif var_name == "WEBSITES":
                param_type = "textarea"
                description = "Comma-separated list of URLs"
            # MATRIX TERMINAL PARAMETERS REMOVED - FIXED VALUES ONLY
            elif var_name == "AUDIO_COUNT":
                param_type = "number"
                description = "Number of audio files to play"
            elif var_name == "SOUNDS_DURATION":
                param_type = "number"
                description = "Duration in seconds"
            elif var_name == "RESTART_DELAY" or var_name == "SHUTDOWN_DELAY":
                param_type = "number"
                description = "Delay in seconds before action"
            elif "DURATION" in var_name:
                param_type = "number"
                description = "Duration in seconds"
            elif "DELAY" in var_name:
                param_type = "number"
                description = "Delay in seconds"
            elif "PATH" in var_name:
                param_type = "text"
                description = "File or directory path"
            elif "MESSAGE" in var_name or "TEXT" in var_name:
                param_type = "textarea"
                description = "Text content"
            elif "COUNT" in var_name or "MAX" in var_name or "NUM" in var_name:
                param_type = "number"
                description = "Numeric value"
            elif "ACTION" in var_name:
                param_type = "select"
                description = "Action to perform"
                # Try to detect possible values from script
                if "SCREEN_ACTION" in var_name:
                    default_value = "toggle"
                elif "MOUSE_ACTION" in var_name:
                    default_value = "toggle"
                elif "TASKBAR_ACTION" in var_name:
                    default_value = "toggle"
            
            # For APP_NAME, even if default is empty string, it's required by the script
            # The scripts check "if not APP_NAME" so empty string means it's required
            if var_name == "APP_NAME" and (default_value == "" or default_value is None):
                # Mark as required by not providing a default, or provide empty string
                parameters[var_name] = {
                    "type": param_type,
                    "default": "",  # Empty string default, but script requires it
                    "description": description,
                    "required": True  # Mark as required
                }
            else:
                parameters[var_name] = {
                    "type": param_type,
                    "default": default_value,
                    "description": description
                }
        
        return parameters
    
    @staticmethod
    async def get_script_content(script_name: str) -> Optional[str]:
        """Get script content from file system"""
        script_path = os.path.join(settings.SCRIPTS_DIR, script_name)
        if os.path.exists(script_path) and script_name.endswith('.py'):
            try:
                with open(script_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Error reading script {script_name}: {e}")
        return None
    
    @staticmethod
    async def list_scripts() -> List[Script]:
        """List all available scripts from filesystem"""
        scripts = []
        scripts_dir = settings.SCRIPTS_DIR
        
        logger.info(f"Looking for scripts in: {scripts_dir}")
        logger.info(f"Scripts directory exists: {os.path.exists(scripts_dir)}")
        
        if not os.path.exists(scripts_dir):
            logger.warning(f"Scripts directory does not exist: {scripts_dir}")
            return scripts
        
        try:
            files = os.listdir(scripts_dir)
            logger.info(f"Found {len(files)} files in scripts directory")
            
            for filename in files:
                if filename.endswith('.py'):
                    script_path = os.path.join(scripts_dir, filename)
                    try:
                        file_size = os.path.getsize(script_path)
                        
                        # Read script to detect parameters
                        script_content = await ScriptService.get_script_content(filename)
                        parameters = {}
                        if script_content:
                            parameters = ScriptService.detect_script_parameters(script_content)
                        
                        # Get file modification time
                        mtime = os.path.getmtime(script_path)
                        updated_at = datetime.fromtimestamp(mtime)
                        
                        scripts.append(Script(
                            name=filename,
                            size=file_size,
                            path=script_path,
                            description=None,
                            updated_at=updated_at,
                            parameters=parameters  # Add parameters to script model
                        ))
                        logger.debug(f"Added script: {filename} ({file_size} bytes, {len(parameters)} parameters)")
                    except Exception as e:
                        logger.error(f"Error processing script {filename}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
        except Exception as e:
            logger.error(f"Error listing scripts directory: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info(f"Returning {len(scripts)} scripts")
        return scripts

