# -*- coding: utf-8 -*-
"""
Fake Blue Screen of Death (BSOD)
Shows a fullscreen fake BSOD for a specified duration
Only Ctrl+Alt+Del can exit before duration ends
"""
import sys
import os
import time
import threading

# Duration in seconds (default 30, max 300)
DURATION = min(int(os.environ.get("BSOD_DURATION", "30")), 300)

print("=" * 50)
print("   FAKE BSOD")
print("=" * 50)
print("   Duration: %d seconds" % DURATION)
print("   Exit: Wait for timer or Ctrl+Alt+Del")
print("=" * 50)

# Try to import tkinter and PIL
try:
    import tkinter as tk
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    try:
        import tkinter as tk
    except ImportError:
        print("[!] tkinter not available")
        sys.exit(1)

# Try to import qrcode for QR code generation
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("[!] qrcode library not available - QR code will show as white square")

def create_bsod():
    """Create a fake BSOD window."""
    root = tk.Tk()
    
    # Remove window decorations and make fullscreen
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.configure(bg='#0078D7')  # Windows 10 BSOD blue
    root.config(cursor="none")  # Hide cursor
    root.overrideredirect(True)  # Remove window decorations
    
    # Disable Alt+F4
    root.protocol("WM_DELETE_WINDOW", lambda: None)
    
    # Get screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Main frame
    frame = tk.Frame(root, bg='#0078D7')
    frame.place(relx=0.5, rely=0.45, anchor='center')
    
    # Sad face emoticon
    sad_face = tk.Label(
        frame,
        text=":(",
        font=('Segoe UI Light', 120),
        fg='white',
        bg='#0078D7'
    )
    sad_face.pack(pady=(0, 20))
    
    # Main error message
    error_msg = tk.Label(
        frame,
        text="Your PC ran into a problem and needs to restart.\nWe're just collecting some error info, and then we'll\nrestart for you.",
        font=('Segoe UI', 20),
        fg='white',
        bg='#0078D7',
        justify='left'
    )
    error_msg.pack(pady=(0, 30))
    
    # Progress percentage
    progress_var = tk.StringVar(value="0% complete")
    progress_label = tk.Label(
        frame,
        textvariable=progress_var,
        font=('Segoe UI', 18),
        fg='white',
        bg='#0078D7'
    )
    progress_label.pack(pady=(0, 40))
    
    # Timer display (small, at bottom)
    timer_var = tk.StringVar(value="")
    timer_label = tk.Label(
        root,
        textvariable=timer_var,
        font=('Segoe UI', 10),
        fg='#0078D7',  # Same as background - hidden
        bg='#0078D7'
    )
    timer_label.place(relx=0.99, rely=0.99, anchor='se')
    
    # QR code (generate actual QR code if libraries available)
    if QRCODE_AVAILABLE and PIL_AVAILABLE:
        try:
            # Generate QR code pointing to Windows stop code page
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,  # Increased from 2 to 4 for better visibility
                border=3,     # Increased border for better visibility
            )
            qr.add_data('https://www.windows.com/stopcode')
            qr.make(fit=True)
            
            # Create QR code image (black on white for high contrast)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            # Resize to make it more visible (200x200 pixels - larger than before)
            qr_img = qr_img.resize((200, 200), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage for tkinter
            qr_photo = ImageTk.PhotoImage(qr_img)
            
            # Create label with QR code image
            qr_label = tk.Label(
                root,
                image=qr_photo,
                bg='#0078D7'  # BSOD blue background
            )
            qr_label.image = qr_photo  # Keep a reference to prevent garbage collection
            # Place QR code on the left side of screen, below the main content
            qr_label.place(relx=0.05, rely=0.75, anchor='nw')
            print("[*] QR code displayed successfully")
        except Exception as e:
            print(f"[!] Error creating QR code: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to white square if QR code generation fails
            qr_frame = tk.Frame(root, bg='white', width=200, height=200)
            qr_frame.place(relx=0.05, rely=0.75, anchor='nw')
            qr_frame.pack_propagate(False)
    else:
        # Fallback: white square placeholder if libraries not available
        if not QRCODE_AVAILABLE:
            print("[!] qrcode library not installed - install with: pip install qrcode[pil]")
        if not PIL_AVAILABLE:
            print("[!] PIL/Pillow not installed - install with: pip install Pillow")
        qr_frame = tk.Frame(root, bg='white', width=200, height=200)
        qr_frame.place(relx=0.05, rely=0.75, anchor='nw')
        qr_frame.pack_propagate(False)
    
    # Stop code info - place to the right of QR code, aligned with QR code top
    # QR code is at 5% from left, 200px wide, so text starts around 25% from left
    stop_code = tk.Label(
        root,
        text="For more information about this issue and possible fixes, visit\nhttps://www.windows.com/stopcode\n\nIf you call a support person, give them this info:\nStop code: CRITICAL_PROCESS_DIED",
        font=('Segoe UI', 11),
        fg='white',
        bg='#0078D7',
        justify='left'
    )
    # Position text to the right of QR code (QR is at 5% from left, 200px wide)
    # Text starts at ~25% from left to be right of QR code but still on left side of screen
    stop_code.place(relx=0.25, rely=0.75, anchor='nw')
    
    # Animation and timer variables
    start_time = time.time()
    
    def update_display():
        elapsed = time.time() - start_time
        remaining = max(0, DURATION - elapsed)
        
        # Update progress (fake, goes from 0 to 100 over duration)
        progress = min(100, int((elapsed / DURATION) * 100))
        progress_var.set("%d%% complete" % progress)
        
        # Hidden timer (for debugging)
        timer_var.set("%.0fs" % remaining)
        
        if remaining <= 0:
            # Duration ended, close
            root.destroy()
            return
        
        # Continue updating
        root.after(100, update_display)
    
    # Block all keyboard input except Ctrl+Alt+Del (which Windows handles)
    def block_keys(event):
        # Block everything
        return "break"
    
    def block_mouse(event):
        return "break"
    
    # Bind to block all input
    root.bind('<Key>', block_keys)
    root.bind('<Button-1>', block_mouse)
    root.bind('<Button-2>', block_mouse)
    root.bind('<Button-3>', block_mouse)
    root.bind('<Motion>', block_mouse)
    root.bind('<Escape>', block_keys)
    root.bind('<Alt-F4>', block_keys)
    root.bind('<Alt_L>', block_keys)
    root.bind('<Alt_R>', block_keys)
    root.bind('<Control_L>', block_keys)
    root.bind('<Control_R>', block_keys)
    
    # Focus and grab all input
    root.focus_force()
    root.grab_set_global()
    
    # Start the display update
    root.after(100, update_display)
    
    print("[*] BSOD displayed for %d seconds" % DURATION)
    print("[*] Only Ctrl+Alt+Del can exit early")
    
    root.mainloop()
    
    print("[OK] BSOD closed")

try:
    create_bsod()
except Exception as e:
    print("[ERROR] %s" % str(e))

print("\n" + "=" * 50)
