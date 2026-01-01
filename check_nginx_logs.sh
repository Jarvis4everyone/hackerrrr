#!/bin/bash

echo "=== Nginx Logs ==="
echo ""
echo "Error Log (last 30 lines):"
echo "----------------------------------------"
sudo tail -30 /var/log/nginx/error.log
echo ""
echo "Access Log (last 20 lines):"
echo "----------------------------------------"
sudo tail -20 /var/log/nginx/access.log
echo ""

