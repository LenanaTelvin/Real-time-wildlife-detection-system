#!/usr/bin/env python3
"""
Keep Alive Script - Pings the backend to prevent cold starts
"""

import requests
import os
import sys
from datetime import datetime

# Your backend URL
BACKEND_URL = os.environ.get("BACKEND_URL", "https://real-time-wildlife-detection-system.onrender.com")

def ping_backend():
    """Ping the health check endpoint"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=30)
        if response.status_code == 200:
            print(f"[{datetime.now()}] ✅ Backend is alive! Status: {response.status_code}")
            return True
        else:
            print(f"[{datetime.now()}] ⚠️ Backend returned: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] ❌ Error pinging backend: {e}")
        return False

if __name__ == "__main__":
    print(f"🔍 Pinging backend: {BACKEND_URL}")
    success = ping_backend()
    sys.exit(0 if success else 1)