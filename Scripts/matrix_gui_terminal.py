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
        self.message_display_time = 0
        self.start_time = time.time()  # Track when terminal started
        self.max_duration = 30.0  # HARD LIMIT - terminal MUST close after 30 seconds
        
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
    
    def force_close_immediately(self):
        """Force close immediately - CTRL+P handler"""
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
        """Draw hacker message - classic hacker terminal style"""
        self.canvas.delete("all")
        
        # Black background with subtle grid
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill='#000000', outline='')
        
        # Subtle grid lines
        for i in range(0, self.width, 30):
            self.canvas.create_line(i, 0, i, self.height, fill='#001100', width=1)
        
        # Main message - large, centered, green
        self.canvas.create_text(
            self.width // 2,
            self.height // 2 - 60,
            text=self.message,
            fill='#00ff41',  # Matrix green
            font=('Consolas', 28, 'bold'),
            anchor='center'
        )
        
        # Decorative separator line
        line_y = self.height // 2 - 20
        self.canvas.create_line(50, line_y, self.width - 50, line_y, fill='#00ff41', width=2)
        
        # Status indicators
        status_items = [
            "[ STATUS: ACTIVE ]",
            "[ ENCRYPTION: AES-256 ]",
            "[ BYPASS: SUCCESSFUL ]",
            "[ ACCESS: GRANTED ]"
        ]
        
        y_offset = self.height // 2 + 20
        for i, item in enumerate(status_items):
            self.canvas.create_text(
                self.width // 2,
                y_offset + (i * 25),
                text=item,
                fill='#00cc33',
                font=('Consolas', 12, 'bold'),
                anchor='center'
            )
        
        # Bottom decorative line
        self.canvas.create_line(50, self.height - 40, self.width - 50, self.height - 40, fill='#00ff41', width=2)
        
        # Corner brackets for hacker look
        bracket_size = 20
        # Top-left
        self.canvas.create_line(20, 20, 20, 20 + bracket_size, fill='#00ff41', width=2)
        self.canvas.create_line(20, 20, 20 + bracket_size, 20, fill='#00ff41', width=2)
        # Top-right
        self.canvas.create_line(self.width - 20, 20, self.width - 20, 20 + bracket_size, fill='#00ff41', width=2)
        self.canvas.create_line(self.width - 20, 20, self.width - 20 - bracket_size, 20, fill='#00ff41', width=2)
        # Bottom-left
        self.canvas.create_line(20, self.height - 20, 20, self.height - 20 - bracket_size, fill='#00ff41', width=2)
        self.canvas.create_line(20, self.height - 20, 20 + bracket_size, self.height - 20, fill='#00ff41', width=2)
        # Bottom-right
        self.canvas.create_line(self.width - 20, self.height - 20, self.width - 20, self.height - 20 - bracket_size, fill='#00ff41', width=2)
        self.canvas.create_line(self.width - 20, self.height - 20, self.width - 20 - bracket_size, self.height - 20, fill='#00ff41', width=2)
    
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
        
        # Alternate between rain and message
        if self.matrix_phase == "rain":
            self.draw_matrix_rain()
            # Switch to message occasionally (less frequent for more rain effect)
            if random.random() < 0.005:  # 0.5% chance per frame
                self.matrix_phase = "message"
                self.message_display_time = time.time()
        else:
            self.draw_message()
            # Switch back to rain after 2-3 seconds of message
            if hasattr(self, 'message_display_time') and time.time() - self.message_display_time > random.uniform(2.0, 3.0):
                self.matrix_phase = "rain"
            elif not hasattr(self, 'message_display_time'):
                self.message_display_time = time.time()
        
        # Schedule next frame
        self.root.after(30, self.animate)  # ~33 FPS
    
    def force_close_after_max(self):
        """Force close after maximum duration (30 seconds) - cannot be overridden"""
        if self.running:
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
