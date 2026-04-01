"""
================================================================
  backend/app.py  — ENTRY POINT
  Run this file to start the backend server:
    python app.py

  Wires everything together.  Logic lives in:
    api/routes.py          → All /api/... endpoints
    database/db_manager.py → Unified DB layer (SQLite + PostgreSQL)
    detection/model.py     → YOLOv11 model + video processing
    detection/alerts.py    → Email alert service
    utils/storage.py       → File upload management
================================================================
"""

import os
from dotenv import load_dotenv
from flask import jsonify

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

from flask import Flask
from flask_cors import CORS
from utils.storage import upload_manager
from api.routes import api_blueprint

app = Flask(__name__)
CORS(app)

@app.after_request
def add_ngrok_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

app.register_blueprint(api_blueprint, url_prefix="/api")

# ── ML TUNNEL CONFIGURATION (for Render deployment) ────────────────────────────
# Get tunnel settings from environment
ML_API_URL = os.environ.get('ML_API_URL', '')
ML_API_KEY = os.environ.get('ML_API_KEY', '')
USE_ML_TUNNEL = bool(ML_API_URL)  # If URL is set, use tunnel mode

# Store in app config for access in routes
app.config['ML_API_URL'] = ML_API_URL
app.config['ML_API_KEY'] = ML_API_KEY
app.config['USE_ML_TUNNEL'] = USE_ML_TUNNEL

# ── FIX 1: Dead /health route removed ────────────────────────────────────────
# The original code defined a @app.route('/health') decorator AFTER app.run(),
# which is a blocking call — the decorator never executed and the route was
# never registered.  The health endpoint already exists at /api/health
# (defined in api/routes.py), so this duplicate was unnecessary.

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Backend is running",
        "mode": "tunnel" if USE_ML_TUNNEL else "local",
        "ml_api_configured": bool(ML_API_URL),
        "database": "postgresql" if os.environ.get('DATABASE_URL') else "sqlite",
        "version": "1.0.0"
    })

if __name__ == "__main__":
    # Initialize database
    try:
        from database.db_manager import init_database
        init_database()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    
    # Get configuration
    db_type = "PostgreSQL" if os.environ.get("DATABASE_URL") else "SQLite"
    ml_mode = "🌐 TUNNEL MODE (Remote ML)" if USE_ML_TUNNEL else "💻 LOCAL MODE (YOLO)"
    port = int(os.environ.get("PORT", 5000))
    
    # Print startup information
    print("\n" + "="*60)
    print("🚀 Wildlife Detection System Backend")
    print("="*60)
    print(f"📍 Running at: http://localhost:{port}")
    print(f"🗄️  Database: {db_type}")
    print(f"🤖 ML Mode: {ml_mode}")
    
    if USE_ML_TUNNEL:
        print(f"🔗 Tunnel URL: {ML_API_URL}")
        print(f"🔐 Auth: {'Enabled' if ML_API_KEY else 'Disabled'}")
        print("📡 Frames will be forwarded to your local ML service")
    else:
        print("📡 Using local YOLO model for detection")
    
    print(f"📁 Upload storage: uploads/")
    print("="*60 + "\n")
    
    # Run the app
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False, 
        threaded=True
    )

""" if __name__ == "__main__":
    # ── FIX 2: Import init_database from db_manager only ─────────────────────
    # Original code had the db.py import commented out but left as a comment,
    # which would confuse anyone maintaining this file. Only db_manager is used.
    from database.db_manager import init_database

    init_database()
    os.makedirs("uploads", exist_ok=True)

    db_type = "PostgreSQL" if os.environ.get("DATABASE_URL") else "SQLite"
    port    = int(os.environ.get("PORT", 5000))

    print(f"Backend running at http://localhost:{port}")
    print(f"  Database : {db_type}")
    print(f"  Storage  : {upload_manager.upload_folder}")

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True) """