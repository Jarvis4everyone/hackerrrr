# -*- coding: utf-8 -*-
"""
Matrix GUI Terminal - Python GUI-based matrix rain terminal
Displays matrix effect with hacker messages in a tkinter window
"""
import tkinter as tk
import random
import time
import os
import threading
import sys
import ctypes
import subprocess

# Windows API constants for input blocking
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
HC_ACTION = 0

# Windows API structures for input blocking
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_ulong),
        ("scanCode", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT),
        ("mouseData", ctypes.c_ulong),
        ("flags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_ulong),
        ("pt", POINT)
    ]

# Global flag to control input blocking
input_blocking_active = True

# ============================================
# INPUT BLOCKER (Same as hacker_attack.py)
# ============================================
class HackerInputBlocker:
    """Multi-method input blocker - same as hacker_attack.py"""
    def __init__(self):
        self.mouse_listener = None
        self.keyboard_listener = None
        self.keyboard_hook = None
        self.mouse_hook = None
        self.hook_proc_keyboard = None
        self.hook_proc_mouse = None
        self.blocking_thread = None
        self.pyautogui_thread = None
        self.blockinput_active = False
        self.method_used = None
    
    def method_pynput(self):
        """Try blocking with pynput (no admin needed)."""
        try:
            try:
                from pynput import keyboard, mouse
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "-q"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                from pynput import keyboard, mouse
            
            # Create listeners with suppress=True to block input
            self.mouse_listener = mouse.Listener(suppress=True)
            self.keyboard_listener = keyboard.Listener(suppress=True)
            
            # Start listeners
            self.mouse_listener.start()
            self.keyboard_listener.start()
            
            # Wait a bit to ensure they're running
            time.sleep(0.5)
            
            # Verify they're actually running
            if self.mouse_listener.running and self.keyboard_listener.running:
                self.method_used = "pynput"
                # Keep listeners alive by joining them in a separate thread
                def keep_listeners_alive():
                    try:
                        if self.mouse_listener:
                            self.mouse_listener.join()
                        if self.keyboard_listener:
                            self.keyboard_listener.join()
                    except:
                        pass
                
                listener_thread = threading.Thread(target=keep_listeners_alive, daemon=True)
                listener_thread.start()
                return True
        except Exception as e:
            pass
        return False
    
    def stop_pynput(self):
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
            if self.keyboard_listener:
                self.keyboard_listener.stop()
        except:
            pass
    
    def method_blockinput(self):
        """Try blocking with Windows BlockInput API."""
        try:
            result = ctypes.windll.user32.BlockInput(True)
            if result:
                self.method_used = "blockinput"
                self.blockinput_active = True
                return True
        except:
            pass
        return False
    
    def stop_blockinput(self):
        try:
            if self.blockinput_active:
                ctypes.windll.user32.BlockInput(False)
                self.blockinput_active = False
        except:
            pass
    
    def method_windows_hooks(self):
        """Try blocking with direct Windows API hooks."""
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            def low_level_keyboard_proc(nCode, wParam, lParam):
                if nCode >= HC_ACTION:
                    return 1  # Block the key
                return user32.CallNextHookExW(self.keyboard_hook, nCode, wParam, lParam)
            
            def low_level_mouse_proc(nCode, wParam, lParam):
                if nCode >= HC_ACTION:
                    return 1  # Block the event
                return user32.CallNextHookExW(self.mouse_hook, nCode, wParam, lParam)
            
            # Define hook procedure types
            if ctypes.sizeof(ctypes.c_void_p) == 8:  # 64-bit
                WPARAM = ctypes.c_ulonglong
                LPARAM = ctypes.c_longlong
            else:  # 32-bit
                WPARAM = ctypes.c_ulong
                LPARAM = ctypes.c_long
            
            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, WPARAM, LPARAM)
            
            self.hook_proc_keyboard = HOOKPROC(low_level_keyboard_proc)
            self.hook_proc_mouse = HOOKPROC(low_level_mouse_proc)
            
            self.keyboard_hook = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL, self.hook_proc_keyboard,
                kernel32.GetModuleHandleW(None), 0
            )
            
            self.mouse_hook = user32.SetWindowsHookExW(
                WH_MOUSE_LL, self.hook_proc_mouse,
                kernel32.GetModuleHandleW(None), 0
            )
            
            if self.keyboard_hook and self.mouse_hook:
                self.method_used = "windows_hooks"
                
                def message_loop():
                    try:
                        while input_blocking_active:
                            msg = MSG()
                            bRet = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0x0001)
                            if bRet:
                                msg = MSG()
                                bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                                if bRet == 0 or bRet == -1:
                                    break
                                user32.TranslateMessage(ctypes.byref(msg))
                                user32.DispatchMessageW(ctypes.byref(msg))
                            else:
                                time.sleep(0.01)
                    except:
                        pass
                
                self.blocking_thread = threading.Thread(target=message_loop, daemon=True)
                self.blocking_thread.start()
                time.sleep(0.5)
                return True
        except:
            pass
        return False
    
    def stop_windows_hooks(self):
        try:
            if self.keyboard_hook:
                ctypes.windll.user32.UnhookWindowsHookExW(self.keyboard_hook)
                self.keyboard_hook = None
            if self.mouse_hook:
                ctypes.windll.user32.UnhookWindowsHookExW(self.mouse_hook)
                self.mouse_hook = None
        except:
            pass
    
    def method_pyautogui(self):
        """Try blocking with pyautogui (last resort)."""
        try:
            try:
                import pyautogui
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui", "-q"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                import pyautogui
            
            pyautogui.FAILSAFE = False
            screen_width, screen_height = pyautogui.size()
            center_x, center_y = screen_width // 2, screen_height // 2
            
            def continuous_block():
                while input_blocking_active:
                    try:
                        pyautogui.moveTo(center_x, center_y, duration=0)
                        time.sleep(0.01)
                    except:
                        pass
            
            self.pyautogui_thread = threading.Thread(target=continuous_block, daemon=True)
            self.pyautogui_thread.start()
            time.sleep(0.5)
            
            self.method_used = "pyautogui"
            return True
        except:
            pass
        return False
    
    def stop_pyautogui(self):
        pass  # Thread stops when input_blocking_active = False
    
    def block(self):
        """Start blocking using best available method."""
        global input_blocking_active
        
        methods = [
            ("pynput", self.method_pynput, self.stop_pynput),
            ("blockinput", self.method_blockinput, self.stop_blockinput),
            ("windows_hooks", self.method_windows_hooks, self.stop_windows_hooks),
            ("pyautogui", self.method_pyautogui, self.stop_pyautogui),
        ]
        
        active_methods = []
        
        for method_name, try_method, stop_method in methods:
            if try_method():
                active_methods.append((method_name, stop_method))
                if method_name in ["pynput", "blockinput", "windows_hooks"]:
                    break  # Strong method found
        
        if not active_methods:
            return False
        
        # Wait while blocking is active - keep checking and verifying blocking is still active
        while input_blocking_active:
            time.sleep(0.1)
            # Verify blocking is still active (especially for pynput)
            if self.method_used == "pynput":
                if self.mouse_listener and not self.mouse_listener.running:
                    # Restart if it stopped
                    try:
                        from pynput import mouse
                        self.mouse_listener = mouse.Listener(suppress=True)
                        self.mouse_listener.start()
                    except:
                        pass
                if self.keyboard_listener and not self.keyboard_listener.running:
                    # Restart if it stopped
                    try:
                        from pynput import keyboard
                        self.keyboard_listener = keyboard.Listener(suppress=True)
                        self.keyboard_listener.start()
                    except:
                        pass
        
        # Stop all active methods
        for method_name, stop_method in active_methods:
            try:
                stop_method()
            except:
                pass
        
        return True

def disable_input_loop():
    """Main function to disable input using multi-method approach."""
    blocker = HackerInputBlocker()
    blocker.block()

class MatrixTerminal:
    def __init__(self):
        # FIXED VALUES - NO PARAMETERS ALLOWED
        self.TITLE = "HACKER TERMINAL"
        self.MESSAGE = "Welcome back sir, Jarvis Here!"
        self.DURATION = 30.0  # FIXED 30 SECONDS - NO EXCEPTIONS
        
        self.root = tk.Tk()
        self.root.title(self.TITLE)
        
        # FULL SCREEN - NO EXCEPTIONS
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.state('zoomed')  # Maximize on Windows
        
        # Make window topmost and remove decorations for hacker look
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        # Remove window decorations for true hacker terminal look
        self.root.overrideredirect(True)  # Remove title bar completely
        # Make it look like a terminal window
        self.root.attributes('-alpha', 0.98)  # Slight transparency for effect
        
        # FIXED SETTINGS - NO PARAMETERS
        self.width = screen_width
        self.height = screen_height
        self.duration = self.DURATION  # FIXED 30 SECONDS
        self.message = self.MESSAGE  # FIXED MESSAGE
        self.running = True
        self.matrix_phase = "rain"  # "rain" or "message"
        self.phase_start_time = time.time()  # Track when current phase started
        self.start_time = time.time()  # Track when terminal started
        self.max_duration = 30.0  # HARD LIMIT - terminal MUST close after 30 seconds
        self.phase_duration = 5.0  # 5 seconds per phase (rain or message)
        
        # Message animation variables
        self.message_char_index = 0  # For typing animation
        self.message_animation_time = 0
        self.status_blink_state = 0  # For blinking status indicators
        self.pulse_intensity = 0  # For pulsing effects
        
        # Input blocking (will use HackerInputBlocker)
        self.input_blocker_thread = None
        
        # Create canvas for matrix effect
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            width=self.width,
            height=self.height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Matrix characters
        self.chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        
        # Matrix columns
        self.num_columns = self.width // 10  # Adjust based on font size
        self.columns = []
        self.column_speeds = []
        self.column_positions = []
        
        # Initialize columns
        for i in range(self.num_columns):
            self.columns.append([])
            self.column_speeds.append(random.uniform(0.5, 2.0))
            self.column_positions.append(random.randint(-500, 0))
        
        # Font settings - larger for better visibility
        self.font_size = 14
        self.font = ('Consolas', self.font_size, 'bold')
        
        # CTRL+P to close immediately - FORCEFULLY
        self.root.bind('<Control-p>', lambda e: self.force_close_immediately())
        self.root.bind('<Control-P>', lambda e: self.force_close_immediately())
        self.root.protocol("WM_DELETE_WINDOW", self.force_close_immediately)
        
        # Start animation
        self.animate()
        
        # Start input blocking in background thread (same method as hacker_attack.py)
        self.input_blocker_thread = threading.Thread(target=disable_input_loop, daemon=False, name="InputBlocker")
        self.input_blocker_thread.start()
        time.sleep(0.5)  # Give it time to initialize
        
        # ALWAYS set up auto-close - FIXED 30 SECONDS
        self.root.after(30000, self.force_close_after_max)  # 30 seconds = 30000ms
    
    
    def force_close_immediately(self):
        """Force close immediately - CTRL+P handler"""
        global input_blocking_active
        input_blocking_active = False
        self.running = False
        try:
            self.root.after(0, self.root.destroy)
        except:
            try:
                self.root.destroy()
            except:
                import os
                os._exit(0)
    
    def draw_matrix_rain(self):
        """Draw matrix rain effect - classic green on black hacker look"""
        self.canvas.delete("all")
        
        # Draw background grid effect (subtle)
        for i in range(0, self.width, 20):
            self.canvas.create_line(i, 0, i, self.height, fill='#001100', width=1)
        for i in range(0, self.height, 20):
            self.canvas.create_line(0, i, self.width, i, fill='#001100', width=1)
        
        for i in range(self.num_columns):
            col_x = i * (self.width / self.num_columns)
            
            # Update column position
            self.column_positions[i] += self.column_speeds[i] * 20
            
            # Reset column if it goes off screen
            if self.column_positions[i] > self.height + 100:
                self.column_positions[i] = random.randint(-500, -100)
                self.column_speeds[i] = random.uniform(0.5, 2.5)
            
            # Draw characters in this column
            y_pos = self.column_positions[i]
            char_count = random.randint(10, 25)
            
            for j in range(char_count):
                char_y = y_pos - (j * self.font_size)
                
                if char_y > 0 and char_y < self.height:
                    # Brightness decreases from top to bottom (trail effect)
                    # Top character is brightest white-green, fading to dark green
                    if j == 0:
                        # Leading character - bright white-green
                        color = '#00ff41'  # Matrix green
                    elif j == 1:
                        color = '#00cc33'  # Bright green
                    elif j == 2:
                        color = '#009922'  # Medium green
                    else:
                        # Fading trail
                        brightness = max(30, 200 - (j * 8))
                        color = f"#00{format(int(brightness), '02x')}00"
                    
                    # Get random character
                    char = random.choice(self.chars)
                    
                    # Draw character with slight glow effect on leading char
                    if j == 0:
                        # Draw glow for leading character
                        self.canvas.create_text(
                            col_x,
                            char_y,
                            text=char,
                            fill='#00ff88',
                            font=self.font,
                            anchor='n'
                        )
                    self.canvas.create_text(
                        col_x,
                        char_y,
                        text=char,
                        fill=color,
                        font=self.font,
                        anchor='n'
                    )
    
    def draw_message(self):
        """Draw enhanced hacker message with animations and professional UI"""
        self.canvas.delete("all")
        
        # Update animation variables
        current_time = time.time()
        if not hasattr(self, 'message_animation_start'):
            self.message_animation_start = current_time
        elapsed = current_time - self.message_animation_start
        
        # Update pulse intensity (0-255)
        self.pulse_intensity = int(128 + 127 * (1 + (elapsed * 2) % 2 - 1))
        
        # Update status blink
        self.status_blink_state = (self.status_blink_state + 1) % 60
        
        # Black background with animated grid
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill='#000000', outline='')
        
        # Animated grid lines with subtle pulse
        grid_alpha = 20 + int(10 * (self.pulse_intensity / 255))
        for i in range(0, self.width, 30):
            self.canvas.create_line(i, 0, i, self.height, fill=f'#00{format(grid_alpha, "02x")}00', width=1)
        for i in range(0, self.height, 30):
            self.canvas.create_line(0, i, self.width, i, fill=f'#00{format(grid_alpha, "02x")}00', width=1)
        
        # HEADQUARTERS header - animated typing effect
        header_text = ">>> HEADQUARTERS <<<"
        header_y = 80
        # Pulsing glow effect for header
        glow_intensity = 30 + int(25 * (self.pulse_intensity / 255))
        self.canvas.create_text(
            self.width // 2,
            header_y,
            text=header_text,
            fill=f'#00{format(glow_intensity, "02x")}00',
            font=('Consolas', 16, 'bold'),
            anchor='center'
        )
        self.canvas.create_text(
            self.width // 2,
            header_y,
            text=header_text,
            fill='#00ff41',
            font=('Consolas', 16, 'bold'),
            anchor='center'
        )
        
        # Top border with animated corners
        border_y = 120
        self.canvas.create_line(50, border_y, self.width - 50, border_y, fill='#00ff41', width=2)
        # Animated corner brackets
        corner_pulse = int(200 + 55 * (self.pulse_intensity / 255))
        corner_color = f'#00{format(min(255, corner_pulse), "02x")}41'
        # Top-left corner
        self.canvas.create_line(50, border_y, 50, border_y - 15, fill=corner_color, width=3)
        self.canvas.create_line(50, border_y, 65, border_y, fill=corner_color, width=3)
        # Top-right corner
        self.canvas.create_line(self.width - 50, border_y, self.width - 50, border_y - 15, fill=corner_color, width=3)
        self.canvas.create_line(self.width - 50, border_y, self.width - 65, border_y, fill=corner_color, width=3)
        
        # Main message - typing animation
        message_y = self.height // 2 - 40
        # Calculate how many characters to show (typing effect)
        chars_to_show = min(len(self.message), int(elapsed * 8))  # 8 chars per second
        displayed_message = self.message[:chars_to_show]
        if chars_to_show < len(self.message):
            displayed_message += "_"  # Blinking cursor
        
        # Glow effect for main message
        glow_size = 2 + int(1 * (self.pulse_intensity / 255))
        for offset in range(glow_size, 0, -1):
            glow_alpha = 100 // (offset + 1)
            self.canvas.create_text(
                self.width // 2 + offset,
                message_y + offset,
                text=displayed_message,
                fill=f'#00{format(glow_alpha, "02x")}00',
                font=('Consolas', 32, 'bold'),
                anchor='center'
            )
        # Main message text
        self.canvas.create_text(
            self.width // 2,
            message_y,
            text=displayed_message,
            fill='#00ff41',
            font=('Consolas', 32, 'bold'),
            anchor='center'
        )
        
        # Decorative separator with animation
        line_y = self.height // 2 + 20
        line_alpha = 150 + int(105 * (self.pulse_intensity / 255))
        self.canvas.create_line(100, line_y, self.width - 100, line_y, 
                               fill=f'#00{format(min(255, line_alpha), "02x")}41', width=3)
        
        # Enhanced status indicators with blinking animation
        status_items = [
            ("[ STATUS:", "ACTIVE", True),
            ("[ ENCRYPTION:", "AES-256", True),
            ("[ BYPASS:", "SUCCESSFUL", True),
            ("[ ACCESS:", "GRANTED", True),
            ("[ HEADQUARTERS:", "ONLINE", True),
            ("[ SYSTEM:", "COMPROMISED", False)
        ]
        
        y_offset = self.height // 2 + 60
        for i, (prefix, value, blink) in enumerate(status_items):
            # Blinking effect for certain items
            if blink and self.status_blink_state % 40 < 20:
                value_color = '#00ff41'
            else:
                value_color = '#00cc33'
            
            # Draw prefix
            self.canvas.create_text(
                self.width // 2 - 80,
                y_offset + (i * 28),
                text=prefix,
                fill='#00aa22',
                font=('Consolas', 13, 'bold'),
                anchor='e'
            )
            # Draw value with animation
            self.canvas.create_text(
                self.width // 2 + 20,
                y_offset + (i * 28),
                text=value + " ]",
                fill=value_color,
                font=('Consolas', 13, 'bold'),
                anchor='w'
            )
        
        # Animated progress bar
        progress_y = self.height - 150
        progress_width = self.width - 200
        progress_x = 100
        # Progress bar background
        self.canvas.create_rectangle(progress_x, progress_y, progress_x + progress_width, progress_y + 8, 
                                    outline='#00aa22', fill='#001100', width=2)
        # Animated progress fill
        progress_percent = (elapsed * 10) % 100
        progress_fill_width = int((progress_width * progress_percent) / 100)
        if progress_fill_width > 0:
            self.canvas.create_rectangle(progress_x, progress_y, progress_x + progress_fill_width, progress_y + 8, 
                                        fill='#00ff41', outline='')
        
        # System info section (bottom)
        info_y = self.height - 100
        info_texts = [
            ">>> SYSTEM ACCESS ESTABLISHED <<<",
            ">>> ALL SECURITY PROTOCOLS BYPASSED <<<",
            ">>> DATA STREAM ACTIVE <<<"
        ]
        for i, info_text in enumerate(info_texts):
            # Scrolling text effect
            scroll_offset = int((elapsed * 20 + i * 30) % 100)
            alpha = 100 + int(155 * (1 - abs(scroll_offset - 50) / 50))
            self.canvas.create_text(
                self.width // 2,
                info_y + (i * 20),
                text=info_text,
                fill=f'#00{format(max(50, alpha), "02x")}00',
                font=('Consolas', 11, 'bold'),
                anchor='center'
            )
        
        # Bottom border with animated corners
        bottom_border_y = self.height - 50
        self.canvas.create_line(50, bottom_border_y, self.width - 50, bottom_border_y, fill='#00ff41', width=2)
        # Bottom-left corner
        self.canvas.create_line(50, bottom_border_y, 50, bottom_border_y + 15, fill=corner_color, width=3)
        self.canvas.create_line(50, bottom_border_y, 65, bottom_border_y, fill=corner_color, width=3)
        # Bottom-right corner
        self.canvas.create_line(self.width - 50, bottom_border_y, self.width - 50, bottom_border_y + 15, fill=corner_color, width=3)
        self.canvas.create_line(self.width - 50, bottom_border_y, self.width - 65, bottom_border_y, fill=corner_color, width=3)
        
        # Side borders with pulse
        side_alpha = 100 + int(100 * (self.pulse_intensity / 255))
        self.canvas.create_line(30, 0, 30, self.height, fill=f'#00{format(min(255, side_alpha), "02x")}00', width=2)
        self.canvas.create_line(self.width - 30, 0, self.width - 30, self.height, fill=f'#00{format(min(255, side_alpha), "02x")}00', width=2)
        
        # Corner brackets for hacker look (enhanced)
        bracket_size = 25
        bracket_glow = int(200 + 55 * (self.pulse_intensity / 255))
        bracket_color = f'#00{format(min(255, bracket_glow), "02x")}41'
        # Top-left
        self.canvas.create_line(20, 20, 20, 20 + bracket_size, fill=bracket_color, width=3)
        self.canvas.create_line(20, 20, 20 + bracket_size, 20, fill=bracket_color, width=3)
        # Top-right
        self.canvas.create_line(self.width - 20, 20, self.width - 20, 20 + bracket_size, fill=bracket_color, width=3)
        self.canvas.create_line(self.width - 20, 20, self.width - 20 - bracket_size, 20, fill=bracket_color, width=3)
        # Bottom-left
        self.canvas.create_line(20, self.height - 20, 20, self.height - 20 - bracket_size, fill=bracket_color, width=3)
        self.canvas.create_line(20, self.height - 20, 20 + bracket_size, self.height - 20, fill=bracket_color, width=3)
        # Bottom-right
        self.canvas.create_line(self.width - 20, self.height - 20, self.width - 20, self.height - 20 - bracket_size, fill=bracket_color, width=3)
        self.canvas.create_line(self.width - 20, self.height - 20, self.width - 20 - bracket_size, self.height - 20, fill=bracket_color, width=3)
    
    def animate(self):
        """Main animation loop"""
        if not self.running:
            return
        
        # HARD CHECK: Always enforce 30 second maximum - check every frame
        elapsed = time.time() - self.start_time
        if elapsed >= self.max_duration:
            # 30 seconds have passed - FORCE CLOSE
            self.force_close_after_max()
            return
        
        # Check if 30 seconds elapsed - FIXED DURATION
        if elapsed >= self.duration:
            self.force_close_after_max()
            return
        
        # Alternate between rain and message every 5 seconds
        current_time = time.time()
        phase_elapsed = current_time - self.phase_start_time
        
        if phase_elapsed >= self.phase_duration:
            # Switch phase after 5 seconds
            if self.matrix_phase == "rain":
                self.matrix_phase = "message"
                self.message_animation_start = current_time
            else:
                self.matrix_phase = "rain"
                if hasattr(self, 'message_animation_start'):
                    delattr(self, 'message_animation_start')
            self.phase_start_time = current_time
        
        # Draw current phase
        if self.matrix_phase == "rain":
            self.draw_matrix_rain()
        else:
            self.draw_message()
        
        # Schedule next frame
        self.root.after(30, self.animate)  # ~33 FPS
    
    def force_close_after_max(self):
        """Force close after maximum duration (30 seconds) - cannot be overridden"""
        if self.running:
            global input_blocking_active
            input_blocking_active = False
            self.running = False
            try:
                self.root.after(0, self.root.destroy)
            except:
                try:
                    self.root.destroy()
                except:
                    pass
    
    def close(self):
        """Close the terminal"""
        global input_blocking_active
        input_blocking_active = False
        self.running = False
        try:
            self.root.destroy()
        except:
            pass
    
    def run(self):
        """Start the terminal"""
        try:
            self.root.mainloop()
        except:
            pass


def launch_single_terminal():
    """Launch single fullscreen matrix terminal - FIXED VALUES ONLY"""
    import subprocess
    import tempfile
    import importlib.util
    
    print("[*] LAUNCHING MATRIX TERMINAL")
    print("[*] Message: WELCOME BACK SIR")
    print("[*] Duration: 30 seconds (FIXED)")
    print("[*] Fullscreen: YES")
    print("[*] Close: CTRL+P or wait 30 seconds")
    
    # Find the matrix_gui_terminal.py script
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
    matrix_gui_script = os.path.join(script_dir, "matrix_gui_terminal.py")
    
    # If not found, try other locations
    if not os.path.exists(matrix_gui_script):
        possible_paths = [
            os.path.join(os.path.dirname(script_dir), "matrix_gui_terminal.py"),
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), "Scripts", "matrix_gui_terminal.py"),
            os.path.join(tempfile.gettempdir(), "matrix_gui_terminal.py"),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                matrix_gui_script = path
                break
    
    if not matrix_gui_script or not os.path.exists(matrix_gui_script):
        print("[!] ERROR: matrix_gui_terminal.py not found!")
        return
    
    # Get Python executable
    python_exe = sys.executable
    if not python_exe or not os.path.exists(python_exe):
        python_exe = 'python'
    
    # Create launcher script - NO PARAMETERS
    launcher_script = os.path.join(tempfile.gettempdir(), "matrix_launcher.py")
    with open(launcher_script, 'w', encoding='utf-8') as f:
        f.write('''import sys
import os
import importlib.util

# Load and run the GUI terminal module
gui_script_path = r"{}"
try:
    spec = importlib.util.spec_from_file_location("matrix_gui_terminal", gui_script_path)
    matrix_gui_terminal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(matrix_gui_terminal)
    
    # Create terminal - NO PARAMETERS - FIXED VALUES ONLY
    terminal = matrix_gui_terminal.MatrixTerminal()
    terminal.run()
except Exception as e:
    import traceback
    print(f"Error: {{e}}")
    traceback.print_exc()
    input("Press Enter to exit...")
'''.format(matrix_gui_script.replace("\\", "\\\\")))
    
    # Launch Python script
    try:
        subprocess.Popen(
            [python_exe, launcher_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        print("[+] Matrix terminal launched (fullscreen, 30 seconds)")
    except Exception as e:
        print(f"[!] Error launching terminal: {e}")


def main():
    """Main function - FIXED VALUES ONLY - NO PARAMETERS"""
    # NO PARAMETERS - FIXED VALUES ONLY
    # Message: "WELCOME BACK SIR"
    # Duration: 30 seconds
    # Fullscreen: YES
    # Close: CTRL+P or 30 seconds
    
    terminal = MatrixTerminal()
    terminal.run()


if __name__ == '__main__':
    main()
