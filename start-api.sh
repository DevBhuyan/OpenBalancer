#!/bin/bash

# 1. Dynamically find the primary local IP address
# This handles Linux machines (Ubuntu/Debian) efficiently
LOCAL_IP=$(hostname -I | awk '{print $1}')

# 2. Fallback to localhost if no LAN IP is found
if [ -z "$LOCAL_IP" ]; then
    echo "⚠️ No LAN IP detected. Falling back to localhost."
    LOCAL_IP="127.0.0.1"
else
    echo "🚀 Detected LAN IP: $LOCAL_IP"
fi

# 3. Define SSL paths relative to the project directory
KEY_FILE="openbalancer.key"
CERT_FILE="openbalancer.crt"

# 4. Execute Uvicorn with dynamic parameters
uvicorn openbalancer.app:app \
    --reload \
    --host "$LOCAL_IP" \
    --ssl-keyfile "$KEY_FILE" \
    --ssl-certfile "$CERT_FILE"
