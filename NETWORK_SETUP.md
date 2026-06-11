# OpenBalancer Dashboard - Network Setup Guide

## Problem: "localhost refused to connect"

When running the dashboard on a network that requires using external IPs instead of loopback addresses, you may see "connection refused" errors.

## Solution

The updated `start-dashboard.sh` script now **automatically detects and uses your machine's external IP address** instead of localhost.

### How It Works

1. **Automatic IP Detection**
   ```bash
   LOCAL_IP=$(hostname -I | awk '{print $1}')
   ```
   - Detects the primary network interface IP
   - Falls back to 127.0.0.1 if no network IP is found
   - Works on Linux/Ubuntu systems

2. **Dynamic Port Configuration**
   - Backend API: `http://<YOUR_IP>:8000`
   - Frontend Dashboard: `http://<YOUR_IP>:3000`

3. **Environment Variable Passing**
   - Dashboard receives `OPENBALANCER_API_URL` environment variable
   - All API calls use the correct external IP

## Running the Dashboard

### Method 1: Automated Script (Recommended)

```bash
cd "LLM Load Balancer"
./start-dashboard.sh
```

**Output:**
```
🌐 Detected LAN IP: 192.168.1.100

✓ Backend API will start on: http://192.168.1.100:8000
✓ Frontend Dashboard will start on: http://192.168.1.100:3000

✓ Both services started!

Open your browser to:
  http://192.168.1.100:3000
```

### Method 2: Manual Setup

**Terminal 1 (Backend):**
```bash
# Detect your IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
# Or manually: LOCAL_IP="192.168.1.100"

python -m uvicorn openbalancer.app:app --host "$LOCAL_IP" --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
# Set the API URL for the dashboard
export OPENBALANCER_API_URL="http://$LOCAL_IP:8000"

cd dashboard
reflex run
```

Then visit: `http://$LOCAL_IP:3000` (replace with your actual IP)

## Finding Your Machine's IP

### Linux/Ubuntu
```bash
# Method 1: hostname
hostname -I

# Method 2: ip command
ip addr show | grep "inet " | grep -v "127.0.0.1"

# Method 3: ifconfig
ifconfig | grep "inet "
```

### macOS
```bash
ifconfig | grep "inet " | grep -v "127.0.0.1"
```

### Windows
```bash
ipconfig | findstr /I "IPv4"
```

## Network Troubleshooting

### 1. Check if Backend is Running
```bash
curl http://<YOUR_IP>:8000/health
```

Expected response:
```json
{"status":"ok","providers":[...]}
```

### 2. Verify Ports Are Not In Use
```bash
# Check port 8000
netstat -an | grep 8000

# Check port 3000
netstat -an | grep 3000
```

### 3. Check CORS Configuration
The API has CORS enabled to allow cross-origin requests from the dashboard:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. View Backend Logs
The backend runs in the foreground, so you can see all logs in Terminal 1:
```
INFO:     Uvicorn running on http://192.168.1.100:8000
INFO:     Application startup complete.
```

### 5. View Frontend Logs
The frontend runs in the foreground in Terminal 2:
```
Compiled successfully!
Ready to serve on http://192.168.1.100:3000
```

## Environment Variables

### OPENBALANCER_API_URL
- **Purpose**: Tells the dashboard where to find the API
- **Default**: `http://localhost:8000`
- **Set by**: `start-dashboard.sh` automatically
- **Can override**: `export OPENBALANCER_API_URL="http://192.168.1.100:8000"`

### PYTHONWARNINGS
- **Purpose**: Suppress Pydantic/SQLModel import warnings
- **Default**: Set to `ignore::DeprecationWarning,ignore::RuntimeWarning`
- **Note**: These warnings don't affect functionality

## Common Issues & Solutions

### Issue: "Connection Refused"
**Cause**: Dashboard trying to connect to localhost instead of external IP

**Solution**:
```bash
# Verify the script detected your IP
./start-dashboard.sh | grep "LAN IP"

# Or manually check
hostname -I
```

### Issue: "CORS Error"
**Cause**: Cross-origin request blocked

**Solution**: Already handled in the script - CORS is enabled on the backend

### Issue: "Pydantic/SQLModel Errors"
**Cause**: Version incompatibility warnings (non-critical)

**Solution**: Automatically suppressed by PYTHONWARNINGS environment variable

### Issue: "Port Already in Use"
**Cause**: Another process using port 8000 or 3000

**Solution**:
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Issue: "Node.js not found"
**Cause**: Reflex requires Node.js

**Solution**: Install Node.js
```bash
# Ubuntu/Debian
sudo apt-get install nodejs npm

# macOS
brew install node

# Windows
Download from https://nodejs.org/
```

## Performance Tips

1. **Use Wired Connection**: More stable than WiFi for development
2. **Disable Firewall Temporarily**: For local network testing only
   ```bash
   sudo ufw disable  # Ubuntu
   ```
3. **Monitor Resource Usage**: Backend and Reflex can use significant RAM
   ```bash
   top
   # or
   htop
   ```

## Production Deployment

For production use:

1. **Use a Reverse Proxy** (nginx/Apache)
   - Handles SSL/TLS
   - Load balancing
   - Static file serving

2. **Use a Process Manager** (systemd/supervisor)
   - Keeps services running
   - Auto-restart on failure

3. **Restrict CORS Origins**
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

4. **Use Environment Secrets**
   - Don't hardcode API URLs
   - Use `.env` files with proper permissions
   - Consider using a secrets manager

## Next Steps

1. Run `./start-dashboard.sh`
2. Note the displayed IP address
3. Open the URL in your browser
4. Sign up/login
5. Add provider credentials
6. Get your OpenBalancer API key!

## Support

For issues:
1. Check the logs in the terminal windows
2. Verify backend is accessible: `curl http://<IP>:8000/health`
3. Check browser console: F12 → Console tab
4. Verify network connectivity: `ping <YOUR_IP>`
