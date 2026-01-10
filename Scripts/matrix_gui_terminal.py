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
        self.root.overrideredirect(False)  # Keep title bar for now
        
        # Matrix settings
        self.width = width
        self.height = height
        self.flag_file = flag_file
        self.duration = duration
        self.message = message
        self.running = True
        self.matrix_phase = "rain"  # "rain" or "message"
        
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
        
        # Font settings
        self.font_size = 12
        self.font = ('Consolas', self.font_size, 'bold')
        
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
        """Draw matrix rain effect"""
        self.canvas.delete("all")
        
        for i in range(self.num_columns):
            col_x = i * (self.width / self.num_columns)
            
            # Update column position
            self.column_positions[i] += self.column_speeds[i] * 15
            
            # Reset column if it goes off screen
            if self.column_positions[i] > self.height + 100:
                self.column_positions[i] = random.randint(-500, -100)
                self.column_speeds[i] = random.uniform(0.5, 2.0)
            
            # Draw characters in this column
            y_pos = self.column_positions[i]
            char_count = random.randint(8, 20)
            
            for j in range(char_count):
                char_y = y_pos - (j * self.font_size)
                
                if char_y > 0 and char_y < self.height:
                    # Brightness decreases from top to bottom
                    brightness = max(50, 255 - (j * 15))
                    color = f"#00{format(int(brightness), '02x')}00"
                    
                    # Get random character
                    char = random.choice(self.chars)
                    
                    # Draw character
                    self.canvas.create_text(
                        col_x,
                        char_y,
                        text=char,
                        fill=color,
                        font=self.font,
                        anchor='n'
                    )
    
    def draw_message(self):
        """Draw hacker message"""
        self.canvas.delete("all")
        
        # Red background flash effect
        flash_color = random.choice(['#ff0000', '#cc0000', '#990000'])
        self.canvas.create_rectangle(0, 0, self.width, self.height, fill=flash_color, outline='')
        
        # Green text
        self.canvas.create_text(
            self.width // 2,
            self.height // 2 - 50,
            text=self.message,
            fill='#00ff00',
            font=('Consolas', 24, 'bold'),
            anchor='center'
        )
        
        # Decorative lines
        self.canvas.create_text(
            self.width // 2,
            self.height // 2 + 20,
            text="=" * 80,
            fill='#00ff00',
            font=('Consolas', 14, 'bold'),
            anchor='center'
        )
        
        # Status text
        status_text = "[ STATUS: ACTIVE ]  [ ENCRYPTION: AES-256 ]  [ BYPASS: SUCCESSFUL ]"
        self.canvas.create_text(
            self.width // 2,
            self.height // 2 + 60,
            text=status_text,
            fill='#00ff00',
            font=('Consolas', 10, 'bold'),
            anchor='center'
        )
    
    def animate(self):
        """Main animation loop"""
        if not self.running:
            return
        
        # Alternate between rain and message
        if self.matrix_phase == "rain":
            self.draw_matrix_rain()
            # Switch to message occasionally
            if random.random() < 0.01:  # 1% chance per frame
                self.matrix_phase = "message"
        else:
            self.draw_message()
            # Switch back to rain after short message display
            if random.random() < 0.05:  # 5% chance per frame
                self.matrix_phase = "rain"
        
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
