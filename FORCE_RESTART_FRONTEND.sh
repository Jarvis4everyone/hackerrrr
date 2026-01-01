#!/bin/bash

echo "=== Force Restarting Frontend with Cache Clear ==="

# Stop frontend completely
echo "1. Stopping frontend..."
sudo systemctl stop hackingpanel-frontend
pkill -9 -f "vite.*--host.*0.0.0.0" 2>/dev/null
pkill -9 -f "node.*vite" 2>/dev/null
pkill -9 -f "npm run dev" 2>/dev/null
sleep 3

# Clear Vite cache
echo "2. Clearing Vite cache..."
cd ~/h1x1/hackingpanel/frontend
rm -rf node_modules/.vite
rm -rf dist
echo "✓ Cache cleared"

# Verify .env
echo "3. Verifying .env file..."
cat .env
if ! grep -q "VITE_API_URL=http://93.127.195.74$" .env; then
    echo "Fixing .env..."
    cat > .env <<'EOF'
VITE_API_URL=http://93.127.195.74
EOF
    echo "✓ .env fixed"
fi

# Start frontend
echo "4. Starting frontend..."
cd ~/h1x1/hackingpanel
sudo systemctl start hackingpanel-frontend
sleep 5

# Check status
echo ""
echo "5. Frontend status:"
sudo systemctl status hackingpanel-frontend --no-pager -l | head -15

echo ""
echo "=== Testing ==="
echo "Frontend should be running. Now:"
echo "1. Open browser at http://93.127.195.74"
echo "2. Press Ctrl+Shift+R (or Cmd+Shift+R on Mac) for hard refresh"
echo "3. Open Developer Tools (F12)"
echo "4. Go to Network tab"
echo "5. Try to login"
echo "6. Check what URL the login request is going to"
echo ""
echo "It should be: POST http://93.127.195.74/api/auth/login"

