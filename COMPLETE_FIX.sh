#!/bin/bash

echo "=== Complete Frontend Fix ==="

# Stop frontend completely
echo "1. Stopping frontend completely..."
sudo systemctl stop hackingpanel-frontend
pkill -9 -f "vite" 2>/dev/null
pkill -9 -f "node.*vite" 2>/dev/null
pkill -9 -f "npm" 2>/dev/null
sleep 3

# Clear ALL caches
echo "2. Clearing all caches..."
cd ~/h1x1/hackingpanel/frontend
rm -rf node_modules/.vite
rm -rf .vite
rm -rf dist
rm -rf .cache
echo "✓ All caches cleared"

# Set correct .env
echo "3. Setting correct .env..."
cat > .env <<'EOF'
VITE_API_URL=http://93.127.195.74
EOF
echo "✓ .env set to:"
cat .env

# Verify the file was written
if [ ! -f .env ]; then
    echo "ERROR: .env file not created!"
    exit 1
fi

# Start frontend
echo ""
echo "4. Starting frontend..."
cd ~/h1x1/hackingpanel
sudo systemctl start hackingpanel-frontend
sleep 5

# Check if it's running
if systemctl is-active --quiet hackingpanel-frontend; then
    echo "✓ Frontend is running"
else
    echo "✗ Frontend failed to start"
    sudo journalctl -u hackingpanel-frontend -n 20 --no-pager
    exit 1
fi

echo ""
echo "=== IMPORTANT ==="
echo "1. Access your app at: http://93.127.195.74 (NOT port 3000)"
echo "2. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)"
echo "3. Open DevTools (F12) → Console tab"
echo "4. Type: console.log(import.meta.env.VITE_API_URL)"
echo "5. It should show: http://93.127.195.74"
echo ""
echo "If it shows something else, the .env isn't being loaded."

