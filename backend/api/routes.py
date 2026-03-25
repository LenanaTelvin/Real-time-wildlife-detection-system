"""
================================================================
  backend/api/routes.py  — ALL API ENDPOINTS
  These are the URLs the frontend calls.

  Every function here maps to one URL:
    GET  /api/health                → health check
    POST /api/camera/start          → start webcam or video
    POST /api/camera/stop           → stop stream
    GET  /api/video/stream          → MJPEG stream (used as <img src>)
    POST /api/video/upload          → upload a local video file
    GET  /api/detections/live       → current-frame detections (polled every 1.5s)
    GET  /api/detections/logs       → detection history table
    GET  /api/detections/stats      → totals per species
    DELETE /api/detections/<id>     → delete one log entry
================================================================
"""
import base64
import cv2
import numpy as np
import os
import threading
from flask import Blueprint, jsonify, request, Response

from database.db import (
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
)

api_blueprint = Blueprint("api", __name__)


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────
@api_blueprint.route("/health", methods=["GET"])
def health_check():
    """
    Frontend calls this to check if backend is up.
    Returns whether the YOLOv11 model is loaded or running in demo mode.
    """
    return jsonify({
        "status": "ok",
        "model_loaded": model is not None,
        "demo_mode": model is None,
    })


# ── START CAMERA / VIDEO ──────────────────────────────────────────────────────
@api_blueprint.route("/camera/start", methods=["POST"])
def start_camera():
    if is_camera_active():
        return jsonify({"status": "already_running"})

    data = request.get_json(silent=True) or {}
    source_type = data.get("source", "webcam")
    facing_mode = data.get("facingMode", "user") # Default to 'user'

    # Logic to determine camera index
    if source_type == "webcam":
        # Usually: 0 = Laptop/Front, 1 = Back camera
        # If 1 doesn't work on your specific mobile hardware, try 2
        source = 1 if facing_mode == "environment" else 0
    else:
        # If source is a file path (e.g., "video.mp4")
        source = source_type

    # Pass the index (int) or path (string) to your processing function
    start_video_processing(source)
    
    return jsonify({
        "status": "started", 
        "source": source,
        "mode": facing_mode
    })

# ── UPLOAD FRAMES ───────────────────────────────────────────────────────────────
@api_blueprint.route("/video/upload_frame", methods=["POST"])
def upload_frame():
    """
    Receives frames pushed from the mobile browser.
    """
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"status": "error"}), 400

    try:
        # Decode the image sent by the phone
        header, encoded = data['image'].split(",", 1)
        nparr = np.frombuffer(base64.b64decode(encoded), np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Send to YOLO model
        from detection.model import process_remote_frame
        process_remote_frame(frame)
        
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── STOP CAMERA ───────────────────────────────────────────────────────────────
@api_blueprint.route("/camera/stop", methods=["POST"])
def stop_camera():
    """Frontend calls this when user clicks the Stop button."""
    stop_video_processing()
    return jsonify({"status": "stopped"})


# ── CAMERA STATUS ─────────────────────────────────────────────────────────────
@api_blueprint.route("/camera/status", methods=["GET"])
def camera_status():
    """Frontend checks this to sync the Start/Stop button state."""
    return jsonify({"active": is_camera_active()})


# ── MJPEG VIDEO STREAM ────────────────────────────────────────────────────────
@api_blueprint.route("/video/stream", methods=["GET"])
def video_stream():
    """
    Frontend uses this as an <img> src:
      <img src="http://localhost:5000/api/video/stream" />

    Pushes annotated JPEG frames continuously.
    Bounding boxes are already drawn by the backend before sending.
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
    Frontend sends a video file here (multipart/form-data, field name: "video").
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
    Frontend polls this every 1.5s to update the 'Detecting Now' panel.
    Returns detections from the most recently processed frame.

    Response shape:
    {
      "detections": [{ "species": "lion", "confidence": 0.87 }, ...],
      "fps": 27.3,
      "frame_count": 142
    }
    """
    return jsonify({
        "detections": get_live_detections(),
        "fps": round(get_fps(), 1),
        "frame_count": get_frame_count(),
    })


# ── DETECTION HISTORY LOGS ────────────────────────────────────────────────────
@api_blueprint.route("/detections/logs", methods=["GET"])
def detection_logs():
    """
    Frontend calls this to populate the Detection History table.
    Query params:
      ?limit=50          (default 50)
      ?species=lion      (optional filter)

    Response shape:
    {
      "logs": [{ "id":1, "species":"lion", "confidence":0.87, ... }],
      "total": 123
    }
    """
    limit = request.args.get("limit", 50, type=int)
    species = request.args.get("species", None)
    logs = get_detection_logs(limit=limit, species_filter=species)
    return jsonify({"logs": logs, "total": len(logs)})


# ── DETECTION STATISTICS ──────────────────────────────────────────────────────
@api_blueprint.route("/detections/stats", methods=["GET"])
def detection_stats():
    """
    Frontend calls this to update the totals/species breakdown panel.

    Response shape:
    {
      "total": 245,
      "by_species": { "lion": 120, "hyena": 85, "buffalo": 40 },
      "today": 30
    }
    """
    return jsonify(get_detection_stats())


# ── DELETE A LOG ENTRY ────────────────────────────────────────────────────────
@api_blueprint.route("/detections/<int:detection_id>", methods=["DELETE"])
def delete_detection(detection_id):
    """
    Frontend calls this when user clicks Delete on a table row.
    URL example: DELETE /api/detections/42
    """
    delete_detection_by_id(detection_id)
    return jsonify({"status": "deleted", "id": detection_id})
