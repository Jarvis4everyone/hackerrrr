#!/bin/bash

# Start both backend and frontend servers

echo "Starting Hacking Panel servers..."

# Start backend in background
cd /root/h1x1/hackingpanel
source .venv/bin/activate
nohup python run.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"
echo "Backend logs: /root/h1x1/hackingpanel/backend.log"

# Wait a bit for backend to start
sleep 3

# Start frontend in background
cd /root/h1x1/hackingpanel/frontend
nohup npm run dev -- --host 0.0.0.0 --port 3000 > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"
echo "Frontend logs: /root/h1x1/hackingpanel/frontend.log"

echo ""
echo "========================================="
echo "Servers are running!"
echo "Backend:  http://93.127.195.74:5000"
echo "Frontend: http://93.127.195.74:3000"
echo "========================================="
echo ""
echo "To stop servers, run:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "Or use: ./stop_all.sh"

