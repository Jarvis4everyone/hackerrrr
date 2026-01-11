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

class MatrixTerminal:
    def __init__(self):
        # FIXED VALUES - NO PARAMETERS ALLOWED
        self.TITLE = "HACKER TERMINAL"
        self.MESSAGE = "WELCOME BACK SIR"
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
        self.scan_line_y = 0  # For scanning line effect
        self.pulse_intensity = 0  # For pulsing effects
        
        # Input blocking
        self.input_blocker = None
        self.input_blocking_active = True
        
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
        
        # ALWAYS set up auto-close - FIXED 30 SECONDS
        self.root.after(30000, self.force_close_after_max)  # 30 seconds = 30000ms
    
    def block_input(self):
        """Block keyboard and mouse input while terminal is running"""
        while self.running and self.input_blocking_active:
            try:
                # Try pynput first (most reliable)
                try:
                    from pynput import keyboard, mouse
                    if not hasattr(self, 'keyboard_listener') or not self.keyboard_listener.running:
                        self.keyboard_listener = keyboard.Listener(suppress=True)
                        self.keyboard_listener.start()
                    if not hasattr(self, 'mouse_listener') or not self.mouse_listener.running:
                        self.mouse_listener = mouse.Listener(suppress=True)
                        self.mouse_listener.start()
                    time.sleep(0.5)
                    continue
                except ImportError:
                    # Try to install pynput
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "-q"],
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                        continue
                    except:
                        pass
                
                # Fallback: BlockInput API
                try:
                    ctypes.windll.user32.BlockInput(True)
                    time.sleep(0.1)
                except:
                    pass
                
                # Fallback: Block keys in tkinter
                def block_all_keys(event):
                    if event.keysym not in ['Control_L', 'Control_R', 'p', 'P']:
                        return "break"
                
                def block_all_mouse(event):
                    return "break"
                
                self.root.bind('<Key>', block_all_keys)
                self.root.bind('<Button>', block_all_mouse)
                self.root.bind('<Motion>', block_all_mouse)
                
                time.sleep(0.1)
            except:
                time.sleep(0.1)
    
    def stop_input_blocking(self):
        """Stop blocking input"""
        self.input_blocking_active = False
        try:
            if hasattr(self, 'keyboard_listener'):
                self.keyboard_listener.stop()
            if hasattr(self, 'mouse_listener'):
                self.mouse_listener.stop()
        except:
            pass
        try:
            ctypes.windll.user32.BlockInput(False)
        except:
            pass
    
    def force_close_immediately(self):
        """Force close immediately - CTRL+P handler"""
        self.stop_input_blocking()
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
        
        # Update scan line
        self.scan_line_y = (self.scan_line_y + 3) % (self.height + 100)
        
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
        
        # Scanning line effect (subtle)
        if self.scan_line_y < self.height:
            self.canvas.create_line(0, self.scan_line_y, self.width, self.scan_line_y, 
                                   fill='#00ff41', width=1, stipple='gray25')
        
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
            self.stop_input_blocking()
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
        self.stop_input_blocking()
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
