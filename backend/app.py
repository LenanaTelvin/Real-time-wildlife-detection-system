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


# ── FIX 1: Dead /health route removed ────────────────────────────────────────
# The original code defined a @app.route('/health') decorator AFTER app.run(),
# which is a blocking call — the decorator never executed and the route was
# never registered.  The health endpoint already exists at /api/health
# (defined in api/routes.py), so this duplicate was unnecessary.


if __name__ == "__main__":
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

    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)