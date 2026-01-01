#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Backend and Frontend Servers${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Pull latest code from GitHub
echo -e "${GREEN}Pulling latest code from GitHub...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✓ Code updated successfully${NC}"
else
    echo -e "${YELLOW}⚠ Git pull failed or no updates available${NC}"
fi
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

# Check if backend is already running
BACKEND_RUNNING=$(ps aux | grep "[p]ython run.py" | wc -l)
if [ "$BACKEND_RUNNING" -gt 0 ]; then
    echo -e "${YELLOW}Backend server is already running. Skipping backend start.${NC}"
    echo -e "${YELLOW}To restart backend, stop it first with: pkill -f 'python run.py'${NC}"
    BACKEND_PID=""
else
    # Activate virtual environment if it exists
    if [ -d ".venv" ]; then
        echo -e "${GREEN}Activating virtual environment...${NC}"
        source .venv/bin/activate
    fi

    # Start Backend Server
    echo -e "${GREEN}Starting Backend Server...${NC}"
    python run.py &
    BACKEND_PID=$!
    echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"
    
    # Wait a moment for backend to start
    sleep 2
fi

# Check if frontend is already running
FRONTEND_RUNNING=$(ps aux | grep "[v]ite" | wc -l)
if [ "$FRONTEND_RUNNING" -gt 0 ]; then
    echo -e "${YELLOW}Frontend server is already running. Skipping frontend start.${NC}"
    echo -e "${YELLOW}To restart frontend, stop it first with: pkill -f vite${NC}"
    FRONTEND_PID=""
else
    # Start Frontend Server
    echo -e "${GREEN}Starting Frontend Server...${NC}"
    cd frontend
    npm run dev &
    FRONTEND_PID=$!
    echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"
    cd ..
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Server Status${NC}"
echo -e "${BLUE}========================================${NC}"
if [ ! -z "$BACKEND_PID" ]; then
    echo -e "${GREEN}✓ Backend running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Backend already running${NC}"
fi
if [ ! -z "$FRONTEND_PID" ]; then
    echo -e "${GREEN}✓ Frontend running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Frontend already running${NC}"
fi
echo ""
echo -e "Backend:  http://localhost:8000"
echo -e "Frontend: http://localhost:3000"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop servers${NC}"
echo ""

# Wait for processes that we started
if [ ! -z "$BACKEND_PID" ] && [ ! -z "$FRONTEND_PID" ]; then
    wait $BACKEND_PID $FRONTEND_PID
elif [ ! -z "$BACKEND_PID" ]; then
    wait $BACKEND_PID
elif [ ! -z "$FRONTEND_PID" ]; then
    wait $FRONTEND_PID
else
    # Both already running, just wait for interrupt
    echo -e "${YELLOW}Both servers were already running. Waiting for Ctrl+C...${NC}"
    while true; do
        sleep 1
    done
fi

