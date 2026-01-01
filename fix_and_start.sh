#!/bin/bash

# Comprehensive fix and start script

echo "=== Fixing and Starting Hacking Panel ==="
echo ""

PROJECT_DIR="/root/h1x1/hackingpanel"
FRONTEND_DIR="/root/h1x1/hackingpanel/frontend"

# Kill any existing processes
echo "1. Stopping any existing processes..."
pkill -f "python.*run.py" 2>/dev/null
pkill -f "vite.*--host.*0.0.0.0" 2>/dev/null
pkill -f "node.*vite" 2>/dev/null
sleep 2

# Check firewall
echo "2. Checking and configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp
    ufw allow 3000/tcp
    echo "Firewall rules added (if ufw is active)"
else
    echo "UFW not found, checking iptables..."
    # Add iptables rules if needed
    iptables -I INPUT -p tcp --dport 5000 -j ACCEPT 2>/dev/null
    iptables -I INPUT -p tcp --dport 3000 -j ACCEPT 2>/dev/null
fi

# Ensure frontend .env exists
echo "3. Ensuring frontend .env exists..."
if [ ! -f "$FRONTEND_DIR/.env" ]; then
    cat > "$FRONTEND_DIR/.env" <<'EOF'
VITE_API_URL=http://93.127.195.74:5000
EOF
    echo "Created frontend .env"
fi

# Check if virtual environment exists
echo "4. Checking Python virtual environment..."
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Virtual environment not found! Creating..."
    cd "$PROJECT_DIR"
    python3.10 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
fi

# Setup systemd services
echo "5. Setting up systemd services..."
cd "$PROJECT_DIR"

if [ -f "setup_systemd.sh" ]; then
    chmod +x setup_systemd.sh
    sudo ./setup_systemd.sh
else
    echo "setup_systemd.sh not found, creating services manually..."
    
    # Create service files
    cat > /tmp/hackingpanel-backend.service <<'EOF'
[Unit]
Description=Hacking Panel Backend Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/h1x1/hackingpanel
Environment="PATH=/root/h1x1/hackingpanel/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/root/h1x1/hackingpanel/.venv/bin/python /root/h1x1/hackingpanel/run.py
Restart=always
RestartSec=10
StandardOutput=append:/root/h1x1/hackingpanel/backend.log
StandardError=append:/root/h1x1/hackingpanel/backend.log

[Install]
WantedBy=multi-user.target
EOF

    cat > /tmp/hackingpanel-frontend.service <<'EOF'
[Unit]
Description=Hacking Panel Frontend Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/h1x1/hackingpanel/frontend
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
StandardOutput=append:/root/h1x1/hackingpanel/frontend.log
StandardError=append:/root/h1x1/hackingpanel/frontend.log

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/hackingpanel-backend.service /etc/systemd/system/
    sudo cp /tmp/hackingpanel-frontend.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable hackingpanel-backend.service
    sudo systemctl enable hackingpanel-frontend.service
fi

# Start services
echo "6. Starting services..."
sudo systemctl restart hackingpanel-backend.service
sleep 3
sudo systemctl restart hackingpanel-frontend.service
sleep 3

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status hackingpanel-backend.service --no-pager -l | head -15
echo ""
sudo systemctl status hackingpanel-frontend.service --no-pager -l | head -15

echo ""
echo "=== Testing Connections ==="
sleep 2
curl -s http://localhost:5000/api/health && echo " - Backend is responding!" || echo " - Backend not responding"
curl -s http://localhost:3000 > /dev/null && echo "Frontend is responding!" || echo "Frontend not responding"

echo ""
echo "=== Done ==="
echo "Backend:  http://93.127.195.74:5000"
echo "Frontend: http://93.127.195.74:3000"
echo ""
echo "Check logs:"
echo "  sudo journalctl -u hackingpanel-backend -f"
echo "  sudo journalctl -u hackingpanel-frontend -f"

