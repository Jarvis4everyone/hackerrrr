#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Backend and Frontend Servers${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Start Backend Server
echo -e "${GREEN}Starting Backend Server...${NC}"
python run.py &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start Frontend Server
echo -e "${GREEN}Starting Frontend Server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Both servers are running!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Backend:  http://localhost:8000"
echo -e "Frontend: http://localhost:3000"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID

