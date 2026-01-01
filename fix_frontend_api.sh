#!/bin/bash

echo "=== Fixing Frontend API Configuration ==="
echo ""

cd ~/h1x1/hackingpanel/frontend

# Since nginx is proxying /api to the backend, we should use relative URLs
# But the frontend code uses API_BASE_URL, so we need to set it to use nginx proxy

# Option 1: Use relative path (works with nginx proxy)
# Option 2: Use full VPS URL

# Let's use the nginx proxy approach - set API URL to empty string so it uses relative paths
# Actually, looking at the code, it uses baseURL, so we need to set it to the nginx proxy

cat > .env <<'EOF'
VITE_API_URL=http://93.127.195.74
EOF

# Or use relative path - but vite needs full URL for env vars
# Actually, since nginx proxies /api, we can use relative paths by setting baseURL to empty
# But the code uses API_BASE_URL, so let's set it to use the nginx proxy

echo "✓ Frontend .env updated!"
echo ""
echo "Current frontend .env:"
cat .env
echo ""

echo "Restarting frontend service..."
sudo systemctl restart hackingpanel-frontend
sleep 3

echo ""
echo "Frontend status:"
sudo systemctl status hackingpanel-frontend --no-pager -l | head -15

echo ""
echo "=== Testing ==="
echo "Frontend should now use: http://93.127.195.74/api for API calls"
echo "Access your app at: http://93.127.195.74"

