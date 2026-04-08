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
    NEW: src/routes/ai.py → Structured AI detection endpoints
================================================================
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))  # Adds backend/ to path
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Import blueprints
from src.routes.auth import auth_bp
from src.routes.sightings import sightings_bp
from src.routes.ai import ai_bp
from api.routes import api_blueprint
from utils.storage import upload_manager


app = Flask(__name__)
CORS(app)


@app.after_request
def add_ngrok_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

@app.route('/api/test', methods=['GET'])
def test():
    return {"message": "Server is working!"}, 200
    
# ============================================
# DIRECT AUTH ROUTES (TEMPORARY - FOR TESTING)
# ============================================
from src.controllers.auth_controller import AuthController

@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    print("🔵 Direct register route hit!")
    return AuthController.register()

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    print("🔵 Direct login route hit!")
    return AuthController.login()

@app.route('/api/auth/profile', methods=['GET'])
def api_auth_profile():
    print("🔵 Direct profile route hit!")
    return AuthController.get_profile()

@app.route('/api/auth/logout', methods=['POST'])
def api_auth_logout():
    print("🔵 Direct logout route hit!")
    return AuthController.logout()

# ============================================
# ADD THESE OTP DIRECT ROUTES
# ============================================
@app.route('/api/auth/verify-otp', methods=['POST'])
def api_auth_verify_otp():
    print("🔵 Direct verify-otp route hit!")
    return AuthController.verify_otp()

@app.route('/api/auth/resend-otp', methods=['POST'])
def api_auth_resend_otp():
    print("🔵 Direct resend-otp route hit!")
    return AuthController.resend_otp()

# Register blueprints
app.register_blueprint(api_blueprint, url_prefix="/api")
app.register_blueprint(ai_bp)
# Note: auth_bp and sightings_bp are commented out because we're using direct routes
# app.register_blueprint(auth_bp, url_prefix='/api')
# app.register_blueprint(sightings_bp, url_prefix='/api')

# ── ML TUNNEL CONFIGURATION (for Render deployment) ────────────────────────────

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
        "version": "1.0.0",
        "routes_available": {
            "existing_api": "/api/*",
            "new_ai_api": "/api/ai/*"  # ➕ NEW: Show available routes
        }
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

    #  NEW: Create src uploads directories if they don't exist
    os.makedirs("src/uploads/raw", exist_ok=True)
    os.makedirs("src/uploads/processed", exist_ok=True)
    os.makedirs("src/uploads/ai_processed", exist_ok=True)
    
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

    # ➕ NEW: Show available routes
    print("\n📡 API Endpoints:")
    print("   Existing API:")
    print("     POST   /api/detect")
    print("     GET    /api/history")
    print("     GET    /api/stats")
    print("     DELETE /api/delete/<id>")
    print("   New Structured API:")
    print("     GET    /api/ai/info      - Model information")
    print("     POST   /api/ai/detect    - Run AI detection")
    print("     GET    /api/ai/stats     - Detection statistics")
    print("     GET    /api/ai/history   - Detection history")
    
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