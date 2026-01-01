#!/bin/bash

# Production deployment script
# Builds frontend and serves both backend and frontend

echo "Building frontend for production..."
cd /root/h1x1/hackingpanel/frontend

# Create .env file for frontend with VPS IP
cat > .env <<'EOF'
VITE_API_URL=http://93.127.195.74:5000
EOF

# Build frontend
npm run build

echo "Frontend built successfully!"

# Start backend
cd /root/h1x1/hackingpanel
source .venv/bin/activate
echo "Starting backend server..."
nohup python run.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend server started with PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Serve frontend using Python's http.server (or install serve globally)
cd /root/h1x1/hackingpanel/frontend/dist
nohup python3 -m http.server 3000 > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend server started with PID: $FRONTEND_PID"

echo ""
echo "========================================="
echo "Production servers are running!"
echo "Backend API:  http://93.127.195.74:5000"
echo "Frontend:     http://93.127.195.74:3000"
echo "========================================="
echo ""
echo "Logs:"
echo "  Backend:  /root/h1x1/hackingpanel/backend.log"
echo "  Frontend: /root/h1x1/hackingpanel/frontend.log"
echo ""
echo "To stop: ./stop_all.sh"

