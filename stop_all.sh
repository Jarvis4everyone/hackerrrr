#!/bin/bash

# Stop all servers
echo "Stopping all servers..."

# Kill backend (Python process running run.py)
pkill -f "python.*run.py" && echo "Backend stopped" || echo "Backend not running"

# Kill frontend (Node/Vite process)
pkill -f "vite.*--host.*0.0.0.0" && echo "Frontend stopped" || echo "Frontend not running"

echo "All servers stopped."

