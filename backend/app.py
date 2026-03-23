"""
================================================================
  backend/app.py  — ENTRY POINT
  Run this file to start the backend server:
    python app.py

  This file just wires everything together.
  The actual logic lives in:
    api/routes.py       → All URL endpoints
    database/db.py      → Database connection & queries
    detection/model.py  → YOLOv11 model + video processing
================================================================
"""

from flask import Flask
from flask_cors import CORS
from utils.storage import upload_manager

# Import the routes blueprint (all /api/... endpoints)
from api.routes import api_blueprint

app = Flask(__name__)
CORS(app)  # Allow frontend (different port) to call this backend

# Register all API routes under /api prefix
app.register_blueprint(api_blueprint, url_prefix="/api")

if __name__ == "__main__":
    #from database.db import init_database
    from database.db_manager import init_database
    import os

    init_database()
    os.makedirs("uploads", exist_ok=True)

    print("🚀 Backend running at http://localhost:5000")
    print("   Frontend should point BACKEND_URL to this address.")
    print(f"   Database: {'PostgreSQL' if os.environ.get('DATABASE_URL') else 'SQLite'}")
    print(f"   Storage: {upload_manager.upload_folder}")

    #app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

    @app.route('/health', methods=['GET'])
    def health_check():
        return {
                "status": "healthy",
                "database": "postgres" if os.environ.get('DATABASE_URL') else "sqlite",
                "model_loaded": True  # You can check if model loaded successfully
             }, 200



