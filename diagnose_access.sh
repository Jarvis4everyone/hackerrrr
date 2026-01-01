#!/bin/bash

echo "=== Comprehensive Access Diagnosis ==="
echo ""

echo "1. Nginx Status:"
systemctl is-active nginx && echo "✓ Nginx is running" || echo "✗ Nginx is not running"
echo ""

echo "2. Backend Service Status:"
systemctl is-active hackingpanel-backend && echo "✓ Backend is running" || echo "✗ Backend is not running"
echo ""

echo "3. Frontend Service Status:"
systemctl is-active hackingpanel-frontend && echo "✓ Frontend is running" || echo "✗ Frontend is not running"
echo ""

echo "4. Ports Listening:"
echo "Port 80 (nginx):"
netstat -tulpn | grep :80 || ss -tulpn | grep :80
echo "Port 5000 (backend):"
netstat -tulpn | grep :5000 || ss -tulpn | grep :5000
echo "Port 3000 (frontend):"
netstat -tulpn | grep :3000 || ss -tulpn | grep :3000
echo ""

echo "5. Testing Local Connections:"
echo "Backend direct:"
curl -s http://localhost:5000/api/health && echo " ✓" || echo " ✗"
echo "Frontend direct:"
curl -s http://localhost:3000 > /dev/null && echo "✓ Frontend responding" || echo "✗ Frontend not responding"
echo "Backend via nginx:"
curl -s http://localhost/api/health && echo " ✓" || echo " ✗"
echo "Frontend via nginx:"
curl -s http://localhost > /dev/null && echo "✓ Frontend via nginx responding" || echo "✗ Frontend via nginx not responding"
echo ""

echo "6. Nginx Configuration:"
nginx -t 2>&1
echo ""

echo "7. Checking Firewall Rules:"
echo "UFW Status:"
ufw status | head -5
echo ""
echo "iptables rules for port 80:"
iptables -L -n | grep -E "(80|ACCEPT)" | head -10
echo ""

echo "8. Network Interfaces:"
ip addr show | grep -E "(inet |eth0)" | head -5
echo ""

echo "9. Testing External IP from VPS (this is NOT a real external test):"
curl -s --connect-timeout 3 http://93.127.195.74/api/health && echo " ✓ (but this is from VPS itself)" || echo " ✗"
echo ""

echo "=== IMPORTANT ==="
echo "If everything above shows ✓ but you still can't access from browser:"
echo ""
echo "1. Check your VPS provider's firewall/security group:"
echo "   - Hostinger: hPanel → VPS → Firewall → Open port 80 (HTTP)"
echo "   - Make sure port 80 is ALLOWED for INBOUND traffic"
echo ""
echo "2. Test from a different network (mobile hotspot, different WiFi)"
echo ""
echo "3. Check if your local firewall/antivirus is blocking"
echo ""
echo "4. Try accessing from a different device"
echo ""
echo "5. Check nginx error logs:"
echo "   sudo tail -50 /var/log/nginx/error.log"
echo ""

