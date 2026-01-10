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
    def __init__(self, title="HACKER TERMINAL", width=850, height=450, x=None, y=None, 
                 flag_file=None, duration=None, message="WELCOME MR. KAUSHIK!"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        
        # Position window
        if x is not None and y is not None:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        else:
            # Center on screen
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make window topmost and remove decorations for hacker look
        self.root.attributes('-topmost', True)
        self.root.configure(bg='black')
        # Remove window decorations for true hacker terminal look
        self.root.overrideredirect(True)  # Remove title bar completely
        # Make it look like a terminal window
        self.root.attributes('-alpha', 0.98)  # Slight transparency for effect
        
        # Matrix settings
        self.width = width
        self.height = height
        self.flag_file = flag_file
        self.duration = duration
        self.message = message
        self.running = True
        self.matrix_phase = "rain"  # "rain" or "message"
        self.message_display_time = 0
        
        # Create canvas for matrix effect
        self.canvas = tk.Canvas(
            self.root,
            bg='black',
            highlightthickness=0,
            width=width,
            height=height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Matrix characters
        self.chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        
        # Matrix columns
        self.num_columns = width // 10  # Adjust based on font size
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
        
        # Add close handler (Escape key or window close)
        self.root.bind('<Escape>', lambda e: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        
        # Start animation
        self.animate()
        
        # Check flag file in background thread
        if self.flag_file:
            self.flag_thread = threading.Thread(target=self.check_flag_file, daemon=True)
            self.flag_thread.start()
        
        # Auto-close after duration
        if self.duration:
            self.root.after(int(self.duration * 1000), self.close)
    
    def check_flag_file(self):
        """Check flag file to see if terminal should close"""
        while self.running:
            try:
                if os.path.exists(self.flag_file):
                    with open(self.flag_file, 'r') as f:
                        content = f.read().strip()
                        if content == "0":
                            self.running = False
                            self.root.after(0, self.close)
                            break
                time.sleep(0.5)
            except:
                pass
            time.sleep(0.1)
    
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
    
    def close(self):
        """Close the terminal"""
        self.running = False
        self.root.destroy()
    
    def run(self):
        """Start the terminal"""
        try:
            self.root.mainloop()
        except:
            pass


def main():
    """Main function - can be called as standalone or imported"""
    import sys
    
    # Get parameters from command line or environment
    title = os.environ.get("TERMINAL_TITLE", "HACKER TERMINAL")
    flag_file = os.environ.get("TERMINAL_FLAG_FILE", None)
    duration = os.environ.get("TERMINAL_DURATION", None)
    message = os.environ.get("TERMINAL_MESSAGE", "WELCOME MR. KAUSHIK!")
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--title="):
                title = arg.split("=", 1)[1]
            elif arg.startswith("--flag="):
                flag_file = arg.split("=", 1)[1]
            elif arg.startswith("--duration="):
                try:
                    duration = float(arg.split("=", 1)[1])
                except:
                    pass
            elif arg.startswith("--message="):
                message = arg.split("=", 1)[1]
    
    if duration:
        try:
            duration = float(duration)
        except:
            duration = None
    
    # Create and run terminal
    terminal = MatrixTerminal(
        title=title,
        flag_file=flag_file,
        duration=duration,
        message=message
    )
    terminal.run()


if __name__ == '__main__':
    main()
