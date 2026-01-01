#!/bin/bash

echo "=== Updating Frontend .env File ==="
echo ""

cd ~/h1x1/hackingpanel/frontend

# Remove /api from the URL to avoid double /api/api path
cat > .env <<'EOF'
VITE_API_URL=http://93.127.195.74
EOF

echo "✓ Frontend .env updated!"
echo ""
echo "Current .env:"
cat .env
echo ""

echo "Restarting frontend service to apply changes..."
sudo systemctl restart hackingpanel-frontend
sleep 3

echo ""
echo "Frontend status:"
sudo systemctl status hackingpanel-frontend --no-pager -l | head -10

echo ""
echo "✓ Done! The frontend will now use http://93.127.195.74/api/auth/login (correct path)"
echo "Refresh your browser and try logging in again."

