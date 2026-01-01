#!/bin/bash

echo "=== Checking Hacking Panel Status ==="
echo ""

echo "1. Checking if processes are running:"
ps aux | grep -E "(python.*run.py|vite|node.*vite)" | grep -v grep
echo ""

echo "2. Checking if ports are listening:"
netstat -tulpn | grep -E "(5000|3000)" || ss -tulpn | grep -E "(5000|3000)"
echo ""

echo "3. Checking systemd services:"
systemctl status hackingpanel-backend --no-pager -l 2>/dev/null || echo "Backend service not installed"
echo ""
systemctl status hackingpanel-frontend --no-pager -l 2>/dev/null || echo "Frontend service not installed"
echo ""

echo "4. Checking firewall:"
ufw status 2>/dev/null || iptables -L -n | grep -E "(5000|3000)" || echo "Firewall check..."
echo ""

echo "5. Recent backend logs:"
tail -20 /root/h1x1/hackingpanel/backend.log 2>/dev/null || echo "No backend.log found"
echo ""

echo "6. Recent frontend logs:"
tail -20 /root/h1x1/hackingpanel/frontend.log 2>/dev/null || echo "No frontend.log found"
echo ""

