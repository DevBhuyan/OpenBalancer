#!/bin/bash

# 1. Ensure working directory is the script's location
cd "$(dirname "$0")"

# 2. Detect Python Environment
PYTHON=$(command -v python3.11 || command -v python3 || command -v "$PYTHON")
if [ -z "$PYTHON" ]; then
    echo "❌ Error: Python is not installed."
    exit 1
fi

# 3. Base Configuration
PORT="${OPENBALANCER_PORT:-8000}"
UVICORN_ARGS=("--reload" "--port" "$PORT")
FALLBACK_TO_HTTP=false

# 4. Attempt HTTPS Setup (Default)
if command -v mkcert &> /dev/null; then
    # Ensure local CA is trusted
    mkcert -install > /dev/null 2>&1

    # Dynamically find primary local LAN IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    if [ -z "$LOCAL_IP" ]; then
        echo "⚠️ No LAN IP detected. Falling back to localhost for HTTPS."
        LOCAL_IP="127.0.0.1"
    else
        echo "🚀 Detected LAN IP: $LOCAL_IP"
    fi

    # Certificate provisioning
    KEY_FILE="openbalancer.key"
    CERT_FILE="openbalancer.crt"
    echo "🔒 Generating trusted local certificates via mkcert..."
    
    if mkcert -key-file "$KEY_FILE" -cert-file "$CERT_FILE" localhost 127.0.0.1 "$LOCAL_IP" > /dev/null 2>&1; then
        # Append SSL specific runtime arguments
        UVICORN_ARGS+=("--host" "$LOCAL_IP" "--ssl-keyfile" "$KEY_FILE" "--ssl-certfile" "$CERT_FILE")
        echo "🔥 Starting OpenBalancer at https://$LOCAL_IP:$PORT"
    else
        echo "⚠️ mkcert failed to generate certificates."
        FALLBACK_TO_HTTP=true
    fi
else
    echo "⚠️ mkcert is not installed. ('brew install mkcert' or 'sudo apt install mkcert')"
    FALLBACK_TO_HTTP=true
fi

# 5. Fallback to HTTP if HTTPS setup failed
if [ "$FALLBACK_TO_HTTP" = true ]; then
    echo "🔄 Falling back to insecure HTTP mode..."
    HOST="${OPENBALANCER_HOST:-127.0.0.1}"
    UVICORN_ARGS+=("--host" "$HOST")
    
    echo "Starting OpenBalancer on http://${HOST}:${PORT}"
    echo "Dashboard: http://${HOST}:${PORT}/dashboard"
    echo "API docs:  http://${HOST}:${PORT}/docs"
fi

echo ""

# 6. Hand off execution control to Python Uvicorn process
exec "$PYTHON" -m uvicorn openbalancer.app:app "${UVICORN_ARGS[@]}"
