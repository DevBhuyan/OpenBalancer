#!/bin/bash
# Quick IP detection and URL preview for OpenBalancer Dashboard

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   OpenBalancer IP & URL Preview      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Detect IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="127.0.0.1"
    echo -e "${YELLOW}⚠️  No LAN IP detected. Using localhost.${NC}"
else
    echo -e "${GREEN}✓ Detected Machine IP: $LOCAL_IP${NC}"
fi

echo ""
echo -e "${YELLOW}Access URLs:${NC}"
echo ""
echo -e "  ${GREEN}Dashboard Frontend:${NC}"
echo -e "    http://$LOCAL_IP:3000"
echo ""
echo -e "  ${GREEN}API Backend:${NC}"
echo -e "    http://$LOCAL_IP:8000"
echo ""
echo -e "  ${GREEN}API Documentation:${NC}"
echo -e "    http://$LOCAL_IP:8000/docs"
echo ""
echo -e "  ${GREEN}Health Check:${NC}"
echo -e "    http://$LOCAL_IP:8000/health"
echo ""

# Quick connectivity test
echo -e "${YELLOW}Testing connectivity...${NC}"
echo ""

if ping -c 1 -W 1 "$LOCAL_IP" &> /dev/null; then
    echo -e "${GREEN}✓ Machine is reachable via IP${NC}"
else
    echo -e "${YELLOW}⚠️  Could not ping machine (may be blocked by firewall)${NC}"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Run: ${GREEN}./start-dashboard.sh${NC}"
echo "  2. Open browser to: ${GREEN}http://$LOCAL_IP:3000${NC}"
echo "  3. Sign up and add provider API keys"
echo ""
