"""
================================================================
  backend/api/routes.py  — ALL API ENDPOINTS

  Every function here maps to one URL:
    GET    /api/health               → health check
    POST   /api/camera/start         → start webcam or video
    POST   /api/camera/stop          → stop stream
    GET    /api/camera/status        → sync Start/Stop button state
    GET    /api/video/stream         → MJPEG stream (used as <img src>)
    POST   /api/video/upload         → upload a local video file
    POST   /api/video/upload_frame   → phone-pushed single frame
    GET    /api/detections/live      → current-frame detections (polled)
    GET    /api/detections/logs      → detection history table
    GET    /api/detections/stats     → totals per species
    DELETE /api/detections/<id>      → delete one log entry
================================================================
"""
import base64
import cv2
import numpy as np
import os
import threading
from flask import Blueprint, jsonify, request, Response

# ── ML TUNNEL SUPPORT (for Render deployment) ─────────────────────────────────
import requests

# ── ML TUNNEL CONFIGURATION ────────────────────────────────────────────────────
def is_tunnel_mode():
    """Check if we should use ML tunnel (forward to local service)"""
    return bool(os.environ.get('ML_API_URL'))

def get_tunnel_url():
    """Get the tunnel URL for ML service"""
    return os.environ.get('ML_API_URL', '')

def get_tunnel_key():
    """Get API key for tunnel authentication"""
    return os.environ.get('ML_API_KEY', '')


def forward_to_tunnel(image_data):
    """
    Forward frame to local ML service via tunnel
    Returns detection results or None if failed
    """
    tunnel_url = get_tunnel_url()
    tunnel_key = get_tunnel_key()
    
    try:
        headers = {"Content-Type": "application/json"}
        if tunnel_key:
            headers["Authorization"] = f"Bearer {tunnel_key}"
        
        response = requests.post(
            f"{tunnel_url}/detect",
            json={"image": image_data},
            headers=headers,
            timeout=25
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Tunnel error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print("Tunnel timeout - local ML service not responding")
        return None
    except requests.exceptions.ConnectionError:
        print("Tunnel connection error - make sure ngrok is running")
        return None
    except Exception as e:
        print(f"Tunnel error: {e}")
        return None

# ── FIX 1: All DB imports now come from db_manager (not db.py) ───────────────
# Previously routes.py imported from database.db (SQLite-only) while app.py
# initialised tables via database.db_manager (Postgres-aware).  In production
# on Render, tables existed in PostgreSQL but every read/write still hit the
# local SQLite file — which doesn't exist on Render — causing silent failures.
from database.db_manager import (          # was: from database.db import (...)
    save_detection,
    get_detection_logs,
    get_detection_stats,
    delete_detection_by_id,
)

from detection.model import (
    start_video_processing,
    stop_video_processing,
    get_live_detections,
    get_latest_frame,
    get_fps,
    get_frame_count,
    is_camera_active,
    model,
    process_remote_frame,                  # ── FIX 2: Explicitly imported so the
)                                          # upload_frame route can call it directly

api_blueprint = Blueprint("api", __name__)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

@api_blueprint.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status":       "ok",
        "model_loaded": model is not None,
    })


# ── START CAMERA / VIDEO ──────────────────────────────────────────────────────
@api_blueprint.route("/camera/start", methods=["POST"])
def start_camera():
    if is_camera_active():
        return jsonify({"status": "already_running"})

    data        = request.get_json(silent=True) or {}
    source_type = data.get("source", "webcam")
    facing_mode = data.get("facingMode", "user")

    if source_type == "webcam":
        source = 1 if facing_mode == "environment" else 0
    else:
        source = source_type

    start_video_processing(source)

    return jsonify({
        "status": "started",
        "source": source,
        "mode":   facing_mode,
    })


# ── UPLOAD FRAMES (phone-pushed) ──────────────────────────────────────────────
@api_blueprint.route("/video/upload_frame", methods=["POST"])
def upload_frame():
    """
    Receives individual frames pushed from a mobile browser.
    If tunnel mode is enabled, forwards to local ML service.
    Otherwise, uses local YOLO model.
    """
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    try:
        # Get image data (already has base64 header)
        image_data = data['image']
        
        # ── TUNNEL MODE: Forward to local ML service ─────────────────────────
        if is_tunnel_mode():
            result = forward_to_tunnel(image_data)
            
            if result:
                # Save detections to database
                for det in result.get('detections', []):
                    annotated_bytes = None
                    if result.get('annotated_frame'):
                        annotated_bytes = base64.b64decode(result['annotated_frame'])
                    save_detection(det, annotated_bytes)
                
                return jsonify(result)
            else:
                # Tunnel failed, return empty result
                return jsonify({
                    "detections": [],
                    "status": "ok",
                    "message": "Tunnel mode active but no response"
                })
        
        # ── LOCAL MODE: Use existing logic ────────────────────────────────────
        else:
            # Your existing code (unchanged)
            header, encoded = image_data.split(",", 1)
            nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Process with local model
            process_remote_frame(frame)
            
            return jsonify({"status": "ok"})
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
""" @api_blueprint.route("/video/upload_frame", methods=["POST"])
def upload_frame():
   
    Receives individual frames pushed from a mobile browser.
    Passes them through the full detection + logging + alert pipeline.
    
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"status": "error", "message": "No image provided"}), 400

    try:
        header, encoded = data['image'].split(",", 1)
        nparr  = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame  = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # ── FIX 3: process_remote_frame now handles DB logging and alerts ──
        # Previously it only drew bounding boxes and stored the JPEG in a
        # separate global (latest_processed_frame) that the MJPEG stream
        # never read from — phone detections were completely invisible.
        process_remote_frame(frame)

        return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500 """

# ── TUNNEL STATUS CHECK ────────────────────────────────────────────────────────
@api_blueprint.route("/tunnel/status", methods=["GET"])
def tunnel_status():
    """Check if ML tunnel is configured and reachable"""
    if not is_tunnel_mode():
        return jsonify({
            "enabled": False,
            "message": "ML tunnel not configured. Set ML_API_URL environment variable."
        })
    
    tunnel_url = get_tunnel_url()
    
    try:
        headers = {}
        if get_tunnel_key():
            headers["Authorization"] = f"Bearer {get_tunnel_key()}"
        
        response = requests.get(
            f"{tunnel_url}/health",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify({
                "enabled": True,
                "url": tunnel_url,
                "reachable": True,
                "response": response.json()
            })
        else:
            return jsonify({
                "enabled": True,
                "url": tunnel_url,
                "reachable": False,
                "error": f"HTTP {response.status_code}"
            })
            
    except Exception as e:
        return jsonify({
            "enabled": True,
            "url": tunnel_url,
            "reachable": False,
            "error": str(e)
        })


# ── STOP CAMERA ───────────────────────────────────────────────────────────────
@api_blueprint.route("/camera/stop", methods=["POST"])
def stop_camera():
    stop_video_processing()
    return jsonify({"status": "stopped"})


# ── CAMERA STATUS ─────────────────────────────────────────────────────────────
@api_blueprint.route("/camera/status", methods=["GET"])
def camera_status():
    return jsonify({"active": is_camera_active()})


# ── MJPEG VIDEO STREAM ────────────────────────────────────────────────────────
@api_blueprint.route("/video/stream", methods=["GET"])
def video_stream():
    """
    Frontend uses this as an <img> src:
      <img src="http://localhost:5000/api/video/stream" />

    Pushes annotated JPEG frames continuously.
    """
    def generate():
        while True:
            frame = get_latest_frame()
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ── UPLOAD VIDEO FILE ─────────────────────────────────────────────────────────
@api_blueprint.route("/video/upload", methods=["POST"])
def upload_video():
    """
    Frontend sends a video file (multipart/form-data, field name: "video").
    Backend saves it and starts processing it instead of the webcam.
    """
    if "video" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    video_file = request.files["video"]
    os.makedirs("uploads", exist_ok=True)
    save_path = f"uploads/{video_file.filename}"
    video_file.save(save_path)

    stop_video_processing()
    start_video_processing(save_path)

    return jsonify({"status": "processing", "filename": video_file.filename})


# ── LIVE DETECTIONS (current frame) ──────────────────────────────────────────
@api_blueprint.route("/detections/live", methods=["GET"])
def live_detections():
    """
    Frontend polls this every 1.5 s to update the 'Detecting Now' panel.

    Response:
    {
      "detections": [{ "species": "lions", "confidence": 0.87 }, ...],
      "fps": 27.3,
      "frame_count": 142
    }
    """
    return jsonify({
        "detections":  get_live_detections(),
        "fps":         round(get_fps(), 1),
        "frame_count": get_frame_count(),
    })


# ── DETECTION HISTORY LOGS ────────────────────────────────────────────────────
@api_blueprint.route("/detections/logs", methods=["GET"])
def detection_logs():
    """
    Populates the Detection History table.
    Query params: ?limit=50  ?species=lions
    """
    limit   = request.args.get("limit", 50, type=int)
    species = request.args.get("species", None)
    logs    = get_detection_logs(limit=limit, species_filter=species)
    return jsonify({"logs": logs, "total": len(logs)})


# ── DETECTION STATISTICS ──────────────────────────────────────────────────────
@api_blueprint.route("/detections/stats", methods=["GET"])
def detection_stats():
    """
    Updates the totals/species breakdown panel.

    Response:
    {
      "total": 245,
      "by_species": { "lions": 120, "hyenas": 85, "buffalo": 40 },
      "today": 30
    }
    """
    return jsonify(get_detection_stats())


# ── DELETE A LOG ENTRY ────────────────────────────────────────────────────────
@api_blueprint.route("/detections/<int:detection_id>", methods=["DELETE"])
def delete_detection(detection_id):
    """DELETE /api/detections/42  — removes that row from the history table."""
    delete_detection_by_id(detection_id)
    return jsonify({"status": "deleted", "id": detection_id})