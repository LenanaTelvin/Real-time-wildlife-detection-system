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
    Passes them through the full detection + logging + alert pipeline.
    """
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
        return jsonify({"status": "error", "message": str(e)}), 500


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