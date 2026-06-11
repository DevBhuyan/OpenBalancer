# OpenBalancer Dashboard - External IP Setup Guide

## What Changed

Your OpenBalancer Dashboard has been updated to support **external IP addresses** for network environments where localhost doesn't work.

## Quick Start

### 1. Check Your IP
```bash
./check-ip.sh
```

**Output:**
```
✓ Detected Machine IP: 192.168.1.100

Access URLs:
  Dashboard Frontend:
    http://192.168.1.100:3000
  API Backend:
    http://192.168.1.100:8000
  API Documentation:
    http://192.168.1.100:8000/docs
  Health Check:
    http://192.168.1.100:8000/health

Next steps:
  1. Run: ./start-dashboard.sh
  2. Open browser to: http://192.168.1.100:3000
  3. Sign up and add provider API keys
```

### 2. Start Dashboard
```bash
./start-dashboard.sh
```

**Output:**
```
🌐 Detected LAN IP: 192.168.1.100

✓ Backend API will start on: http://192.168.1.100:8000
✓ Frontend Dashboard will start on: http://192.168.1.100:3000

✓ Both services started!

🌐 Open your browser to:
  http://192.168.1.100:3000
```

### 3. Open Dashboard
Visit the URL shown in your terminal (e.g., `http://192.168.1.100:3000`)

## What Was Updated

### Scripts

1. **`start-dashboard.sh`** (Updated)
   - Auto-detects external IP using `hostname -I`
   - Starts backend on external IP
   - Passes API URL to frontend via environment variable
   - Suppresses Pydantic/SQLModel warnings
   - Better formatted output with detected IPs and URLs

2. **`check-ip.sh`** (New)
   - Quick way to see your machine's IP
   - Shows all access URLs
   - Tests connectivity
   - Helps diagnose network issues

### Code

1. **`dashboard/state.py`** (Updated)
   - Added `API_BASE_URL` constant that reads from `OPENBALANCER_API_URL` environment variable
   - All API calls now use `API_BASE_URL` instead of hardcoded `http://localhost:8000`
   - Falls back to localhost if no environment variable is set

2. **`NETWORK_SETUP.md`** (New)
   - Comprehensive network troubleshooting guide
   - Instructions for manual setup
   - Common issues and solutions
   - IP detection commands for different OS

3. **`SETUP_SUMMARY.md`** (This file)
   - Quick reference for all changes

## How It Works

```
User runs: ./start-dashboard.sh
                    ↓
Script detects IP: hostname -I → 192.168.1.100
                    ↓
Backend API starts: uvicorn app:app --host 192.168.1.100 --port 8000
                    ↓
Export env var: OPENBALANCER_API_URL="http://192.168.1.100:8000"
                    ↓
Reflex frontend starts: reflex run (reads env var)
                    ↓
Dashboard loads and connects to API using the correct external IP
```

## File Changes Summary

### Modified Files
- `dashboard/state.py` - Uses dynamic API URL
- `start-dashboard.sh` - External IP detection and setup

### New Files
- `check-ip.sh` - IP detection utility
- `NETWORK_SETUP.md` - Detailed network troubleshooting
- `SETUP_SUMMARY.md` - This file

## Environment Variables

| Variable | Value | Set By | Usage |
|----------|-------|--------|-------|
| `OPENBALANCER_API_URL` | `http://<IP>:8000` | `start-dashboard.sh` | Tells dashboard where to find API |
| `PYTHONWARNINGS` | `ignore::DeprecationWarning,...` | `start-dashboard.sh` | Suppresses import warnings |

## Usage Examples

### Example 1: Automatic Setup
```bash
cd "LLM Load Balancer"
./start-dashboard.sh
# Opens http://192.168.1.100:3000 automatically
```

### Example 2: Manual Setup with Specific IP
```bash
# Terminal 1
export LOCAL_IP="192.168.1.100"
python -m uvicorn openbalancer.app:app --host "$LOCAL_IP" --port 8000 --reload

# Terminal 2
export OPENBALANCER_API_URL="http://192.168.1.100:8000"
cd dashboard
reflex run
```

### Example 3: Check IP First
```bash
./check-ip.sh  # See your IP and URLs
./start-dashboard.sh  # Start dashboard with that IP
```

## Troubleshooting

### "Connection Refused"
```bash
# 1. Check if backend is running
curl http://192.168.1.100:8000/health

# 2. Check backend logs in Terminal 1 for errors
# 3. Verify IP is correct
./check-ip.sh

# 4. Check if ports are available
netstat -an | grep 8000  # Should be empty or show your service
```

### "Not authorized" or "Port in use"
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Try again
./start-dashboard.sh
```

### Pydantic/SQLModel Warnings
```
Traceback (most recent call last):
  ...
ImportError: cannot import name 'PydanticDeprecatedSince211' from 'pydantic.v1'
```
These warnings are suppressed by default in the script. If you still see them:
```bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
./start-dashboard.sh
```

## Network Architecture

```
┌─────────────────────────────────────────┐
│         Your Machine (192.168.1.100)    │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐  │
│  │  FastAPI Backend (Port 8000)    │  │
│  │  - Authentication endpoints     │  │
│  │  - Dashboard API endpoints      │  │
│  │  - CORS enabled                 │  │
│  └─────────────────────────────────┘  │
│                ↑                        │
│         HTTP (Port 8000)                │
│                ↓                        │
│  ┌─────────────────────────────────┐  │
│  │  Reflex Frontend (Port 3000)    │  │
│  │  - Login page                   │  │
│  │  - Dashboard UI                 │  │
│  │  - Provider management          │  │
│  └─────────────────────────────────┘  │
│                ↕                        │
│         HTTP (Port 3000)                │
└─────────────────────────────────────────┘
        ↕
    Browser
    (Your Computer)
```

## Testing the Setup

### 1. Test Backend Health
```bash
curl http://192.168.1.100:8000/health
```

Expected response:
```json
{"status":"ok","providers":[...]}
```

### 2. Test API Documentation
```bash
# Open in browser: http://192.168.1.100:8000/docs
```

### 3. Test Frontend Access
```bash
# Open in browser: http://192.168.1.100:3000
```

### 4. Test Full Workflow
1. Visit http://192.168.1.100:3000
2. Click "Sign up"
3. Enter test credentials
4. Add provider API keys
5. Verify OpenBalancer key is generated

## Production Deployment

For production use, consider:

1. **Use HTTPS**
   ```bash
   # Use reverse proxy (nginx/Apache)
   # Or enable SSL in Uvicorn
   ```

2. **Restrict CORS**
   ```python
   # In openbalancer/app.py
   allow_origins=["https://yourdomain.com"]
   ```

3. **Use Process Manager**
   ```bash
   # systemd, supervisor, or PM2
   ```

4. **Use Environment Secrets**
   ```bash
   # Store API URLs in .env
   # Use Docker secrets or Kubernetes
   ```

## Quick Reference

| Task | Command |
|------|---------|
| Check IP | `./check-ip.sh` |
| Start Dashboard | `./start-dashboard.sh` |
| Test Backend | `curl http://192.168.1.100:8000/health` |
| View API Docs | Open `http://192.168.1.100:8000/docs` |
| Access Dashboard | Open `http://192.168.1.100:3000` |
| Stop All Services | Press `Ctrl+C` in start-dashboard.sh terminal |

## Next Steps

1. ✅ Run `./check-ip.sh` to verify IP detection works
2. ✅ Run `./start-dashboard.sh` to start services
3. ✅ Open the displayed URL in your browser
4. ✅ Sign up for a new account
5. ✅ Add your provider API keys
6. ✅ Get your OpenBalancer API key
7. ✅ Copy a quickstart code snippet
8. ✅ Test the API using the provided examples

## Support

For detailed troubleshooting, see:
- `NETWORK_SETUP.md` - Network troubleshooting guide
- `DASHBOARD_SETUP.md` - Complete dashboard documentation
- `dashboard/README.md` - Dashboard development guide

Enjoy using OpenBalancer Dashboard! 🚀
