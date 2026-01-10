# -*- coding: utf-8 -*-
"""
Matrix GUI Terminal - Python GUI-based matrix rain terminal
Works as standalone or controlled by flag file
"""
import tkinter as tk
import random
import time
import os
import sys
import threading

# Configuration
WIDTH = 1000
HEIGHT = 600
FONT_SIZE = 12
FPS = 30  # Frames per second
CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%^&*アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"

# Get settings from environment or defaults
FLAG_FILE = os.environ.get("MATRIX_FLAG_FILE", None)
DURATION = int(os.environ.get("MATRIX_DURATION", 300))  # Default 5 minutes
MESSAGE = os.environ.get("MATRIX_MESSAGE", "WELCOME MR. KAUSHIK!")
AUTO_CLOSE = os.environ.get("MATRIX_AUTO_CLOSE", "false").lower() == "true"

class MatrixTerminal:
    def __init__(self, root):
        self.root = root
        self.running = True
        self.show_message = False
        self.message_displayed = False
        
        # Window setup
        self.root.title("HACKER TERMINAL")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg='black')
        self.root.attributes('-topmost', True)
        
        # Remove window decorations for full control
        self.root.overrideredirect(False)
        
        # Canvas for matrix effect
        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Matrix columns
        self.columns = []
        self.column_count = WIDTH // (FONT_SIZE // 2)
        for i in range(self.column_count):
            self.columns.append({
                'y': random.randint(-HEIGHT, 0),
                'speed': random.uniform(2, 8),
                'length': random.randint(10, 30),
                'chars': []
            })
        
        # Text items for each column
        self.text_items = []
        for col in self.columns:
            col['items'] = []
        
        # Start animation
        self.animate()
        
        # Check flag file if provided
        if FLAG_FILE:
            self.flag_check_thread = threading.Thread(target=self.check_flag_file, daemon=True)
            self.flag_check_thread.start()
        
        # Auto-close timer if duration is set
        if DURATION > 0:
            self.start_time = time.time()
            self.duration_thread = threading.Thread(target=self.check_duration, daemon=True)
            self.duration_thread.start()
    
    def check_flag_file(self):
        """Check flag file to see if terminal should close"""
        while self.running:
            try:
                if os.path.exists(FLAG_FILE):
                    with open(FLAG_FILE, 'r') as f:
                        content = f.read().strip()
                        if content == "0":
                            self.running = False
                            self.root.after(0, self.close_terminal)
                            break
                time.sleep(0.5)
            except:
                pass
    
    def check_duration(self):
        """Check if duration has elapsed"""
        while self.running:
            if time.time() - self.start_time >= DURATION:
                self.running = False
                self.show_message = True
                self.root.after(0, self.show_final_message)
                break
            time.sleep(1)
    
    def show_final_message(self):
        """Show final hacker message"""
        if self.message_displayed:
            return
        
        self.message_displayed = True
        self.canvas.delete("all")
        self.canvas.configure(bg='black')
        
        # Red background flash
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill='#1a0000', outline='')
        
        # Message text
        self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 - 50,
            text=MESSAGE,
            font=('Consolas', 32, 'bold'),
            fill='#00ff00',
            justify='center'
        )
        
        # Subtitle
        self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 + 50,
            text="SYSTEM COMPROMISED",
            font=('Consolas', 18, 'bold'),
            fill='#ff0000',
            justify='center'
        )
        
        # Status bar
        status_text = "[ STATUS: ACTIVE ]  [ ENCRYPTION: AES-256 ]  [ BYPASS: SUCCESSFUL ]  [ ACCESS: GRANTED ]"
        self.canvas.create_text(
            WIDTH // 2,
            HEIGHT - 30,
            text=status_text,
            font=('Consolas', 10, 'bold'),
            fill='#00ff00',
            justify='center'
        )
        
        # Blinking effect
        self.blink_count = 0
        self.blink_message()
    
    def blink_message(self):
        """Blink the message for dramatic effect"""
        if not self.running:
            return
        
        self.blink_count += 1
        if self.blink_count % 10 < 5:
            self.canvas.itemconfig(1, fill='#00ff00')  # Green
        else:
            self.canvas.itemconfig(1, fill='#ff0000')  # Red
        
        if self.blink_count < 30:  # Blink for 3 seconds
            self.root.after(100, self.blink_message)
        elif AUTO_CLOSE:
            self.root.after(2000, self.close_terminal)
    
    def animate(self):
        """Main animation loop"""
        if not self.running:
            return
        
        # Clear canvas
        self.canvas.delete("matrix")
        
        # Update and draw columns
        for i, col in enumerate(self.columns):
            # Move column down
            col['y'] += col['speed']
            
            # Reset if off screen
            if col['y'] > HEIGHT:
                col['y'] = random.randint(-200, -50)
                col['speed'] = random.uniform(2, 8)
                col['length'] = random.randint(10, 30)
            
            # Draw characters in this column
            x = i * (FONT_SIZE // 2)
            for j in range(col['length']):
                y_pos = col['y'] + (j * FONT_SIZE)
                if 0 <= y_pos < HEIGHT:
                    char = random.choice(CHARS)
                    # Fade effect - brighter at top
                    alpha = 1.0 - (j / col['length'])
                    if alpha > 0.5:
                        color = '#00ff00'  # Bright green
                    elif alpha > 0.2:
                        color = '#00aa00'  # Medium green
                    else:
                        color = '#004400'  # Dark green
                    
                    self.canvas.create_text(
                        x,
                        y_pos,
                        text=char,
                        font=('Consolas', FONT_SIZE),
                        fill=color,
                        tags="matrix"
                    )
        
        # Schedule next frame
        delay = int(1000 / FPS)
        self.root.after(delay, self.animate)
    
    def close_terminal(self):
        """Close the terminal window"""
        self.running = False
        self.root.destroy()

def main():
    """Main entry point"""
    root = tk.Tk()
    app = MatrixTerminal(root)
    
    # Handle window close
    def on_closing():
        app.running = False
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window on screen
    root.update_idletasks()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - WIDTH) // 2
    y = (screen_height - HEIGHT) // 2
    root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
    
    try:
        root.mainloop()
    except:
        pass

if __name__ == '__main__':
    main()

