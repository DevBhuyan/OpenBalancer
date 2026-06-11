#!/bin/bash
# Start both OpenBalancer API and Dashboard with external IP support

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect external IP address
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
    echo -e "${YELLOW}⚠️  No LAN IP detected. Using localhost.${NC}"
else
    echo -e "${GREEN}🌐 Detected LAN IP: $LOCAL_IP${NC}"
fi

DASHBOARD_PORT=3000
API_PORT=8000
# Use HTTPS for the API since we now serve it with a TLS certificate
API_URL="https://$LOCAL_IP:$API_PORT"
DASHBOARD_URL="http://$LOCAL_IP:$DASHBOARD_PORT"

echo -e "${GREEN}🚀 OpenBalancer Dashboard Startup${NC}"
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

# Check if Node.js is installed (required for Reflex)
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    echo "Reflex requires Node.js. Install it first:"
    echo "  Ubuntu/Debian: sudo apt-get install nodejs npm"
    echo "  macOS: brew install node"
    exit 1
fi

# Check if dependencies are installed
echo -e "${YELLOW}📦 Checking dependencies...${NC}"
if ! python -c "import reflex" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies (this may take a few minutes)...${NC}"
    pip install -e . --upgrade > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

echo ""
echo -e "${YELLOW}📝 Starting services...${NC}"
echo ""
echo -e "${GREEN}✓ Backend API will start on: $API_URL${NC}"
echo -e "${GREEN}✓ Frontend Dashboard will start on: $DASHBOARD_URL${NC}"
echo ""
echo -e "${YELLOW}💡 Commands:${NC}"
echo "   - API Docs: $API_URL/docs"
echo "   - Health Check: $API_URL/health"
echo "   - Dashboard: $DASHBOARD_URL"
echo ""
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
echo -e "${YELLOW}Ctrl+C to stop services${NC}"
echo ""

# Start backend in background
echo -e "${GREEN}Starting FastAPI backend...${NC}"
python -m uvicorn openbalancer.app:app --host "$LOCAL_IP" --port $API_PORT --reload &
BACKEND_PID=$!

# Wait for backend to start and be ready
sleep 3

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Failed to start backend${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo ""

# Export API URL for Reflex dashboard to use
export OPENBALANCER_API_URL="$API_URL"

# Start frontend
echo -e "${GREEN}Starting Reflex dashboard...${NC}"
cd dashboard

# Export API URL for Reflex to use
export OPENBALANCER_API_URL="$API_URL"

# Suppress Pydantic/SQLModel compatibility warnings
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::RuntimeWarning"

reflex run &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 8

echo ""
echo -e "${GREEN}✓ Both services started!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🌐 OpenBalancer Dashboard Ready     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Open your browser to:${NC}"
echo -e "${GREEN}  $DASHBOARD_URL${NC}"
echo ""
echo -e "${YELLOW}API Documentation:${NC}"
echo -e "${GREEN}  $API_URL/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep process running and handle shutdown
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo -e "\n${YELLOW}Services stopped${NC}"; exit 0' INT

wait $BACKEND_PID $FRONTEND_PID
