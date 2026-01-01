# Deployment Guide for VPS

## Quick Start

### Option 1: Development Mode (Both servers running)

```bash
cd /root/h1x1/hackingpanel
chmod +x start_all.sh stop_all.sh
./start_all.sh
```

This will start:
- Backend on port 5000: http://93.127.195.74:5000
- Frontend on port 3000: http://93.127.195.74:3000

### Option 2: Production Mode (Built frontend)

```bash
cd /root/h1x1/hackingpanel
chmod +x start_production.sh stop_all.sh
./start_production.sh
```

This will:
- Build the frontend
- Start backend on port 5000
- Serve built frontend on port 3000

## Stopping Servers

```bash
./stop_all.sh
```

## Manual Start

### Backend Only
```bash
cd /root/h1x1/hackingpanel
source .venv/bin/activate
python run.py
```

### Frontend Only (Development)
```bash
cd /root/h1x1/hackingpanel/frontend
npm run dev -- --host 0.0.0.0 --port 3000
```

### Frontend Only (Production Build)
```bash
cd /root/h1x1/hackingpanel/frontend
npm run build
cd dist
python3 -m http.server 3000
```

## Environment Variables

### Backend (.env in root)
```
MONGODB_URL=mongodb+srv://KaushikShresth:Shresth123&@cluster0.awof7.mongodb.net/
MONGODB_DB_NAME=HackingPanel
SERVER_URL=http://93.127.195.74:5000/
USERNAME=Shresth
PASSWORD=hackur
```

### Frontend (.env in frontend/)
```
VITE_API_URL=http://93.127.195.74:5000
```

## Using systemd (Recommended for Production)

Create `/etc/systemd/system/hackingpanel-backend.service`:
```ini
[Unit]
Description=Hacking Panel Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/h1x1/hackingpanel
Environment="PATH=/root/h1x1/hackingpanel/.venv/bin"
ExecStart=/root/h1x1/hackingpanel/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/hackingpanel-frontend.service`:
```ini
[Unit]
Description=Hacking Panel Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/h1x1/hackingpanel/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0 --port 3000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable hackingpanel-backend
sudo systemctl enable hackingpanel-frontend
sudo systemctl start hackingpanel-backend
sudo systemctl start hackingpanel-frontend
```

Check status:
```bash
sudo systemctl status hackingpanel-backend
sudo systemctl status hackingpanel-frontend
```

## Firewall

Make sure ports 5000 and 3000 are open:
```bash
sudo ufw allow 5000/tcp
sudo ufw allow 3000/tcp
```

## Using Nginx (Optional - for better production setup)

Install nginx and configure reverse proxy:

```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/hackingpanel`:
```nginx
server {
    listen 80;
    server_name 93.127.195.74;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/hackingpanel /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

