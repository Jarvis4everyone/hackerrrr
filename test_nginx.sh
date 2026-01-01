#!/bin/bash

echo "=== Testing Nginx Setup ==="
echo ""

echo "1. Checking if nginx is running:"
systemctl status nginx --no-pager -l | head -10
echo ""

echo "2. Testing nginx on port 80:"
curl -s http://localhost | head -20
echo ""

echo "3. Testing backend API through nginx:"
curl -s http://localhost/api/health
echo ""
echo ""

echo "4. Checking if port 80 is listening:"
netstat -tulpn | grep :80 || ss -tulpn | grep :80
echo ""

echo "5. Testing from external IP (if accessible):"
curl -s --connect-timeout 5 http://93.127.195.74/api/health && echo " ✓ External access working!" || echo " ✗ External access blocked (check provider firewall for port 80)"
echo ""

echo "=== Access URLs ==="
echo "Frontend: http://93.127.195.74"
echo "Backend API: http://93.127.195.74/api/health"
echo ""
echo "If external access doesn't work, you need to open port 80 in your VPS provider's firewall."

