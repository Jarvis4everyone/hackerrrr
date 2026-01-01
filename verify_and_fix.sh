#!/bin/bash

echo "=== Verifying and Fixing Access Issues ==="
echo ""

# Check if nginx config exists and is correct
echo "1. Verifying nginx configuration..."
if [ -f /etc/nginx/sites-available/hackingpanel ]; then
    echo "✓ Nginx config file exists"
    nginx -t
else
    echo "✗ Nginx config missing, recreating..."
    sudo ./setup_nginx.sh
fi
echo ""

# Ensure nginx is enabled and running
echo "2. Ensuring nginx is running..."
sudo systemctl enable nginx
sudo systemctl restart nginx
sleep 2
systemctl is-active nginx && echo "✓ Nginx is active" || echo "✗ Nginx failed to start"
echo ""

# Check if UFW needs to allow port 80
echo "3. Configuring local firewall (UFW)..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    echo "✓ UFW rules added for ports 80/443"
else
    echo "UFW not installed, skipping..."
fi
echo ""

# Test local access
echo "4. Testing local access..."
curl -s http://localhost/api/health > /dev/null && echo "✓ Backend accessible via nginx" || echo "✗ Backend not accessible"
curl -s http://localhost > /dev/null && echo "✓ Frontend accessible via nginx" || echo "✗ Frontend not accessible"
echo ""

# Show current status
echo "5. Current Status:"
echo "Nginx:" $(systemctl is-active nginx)
echo "Backend:" $(systemctl is-active hackingpanel-backend)
echo "Frontend:" $(systemctl is-active hackingpanel-frontend)
echo ""

echo "6. Port Status:"
netstat -tulpn | grep -E ":(80|443|5000|3000)" || ss -tulpn | grep -E ":(80|443|5000|3000)"
echo ""

echo "=== Next Steps ==="
echo ""
echo "If you still can't access from browser:"
echo ""
echo "1. CHECK YOUR VPS PROVIDER'S FIREWALL:"
echo "   - Log into your VPS provider's control panel"
echo "   - Find Firewall/Security Group settings"
echo "   - Add rule: Port 80 (HTTP) - Allow Inbound"
echo ""
echo "2. Test from your browser:"
echo "   http://93.127.195.74"
echo ""
echo "3. Check nginx logs for errors:"
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
echo "4. Try from a different network (mobile hotspot) to rule out your local firewall"

