"""
================================================================
  backend/detection/model.py  — YOLOV11 + VIDEO PROCESSING
================================================================
"""

import cv2
import os
import time
import threading
from datetime import datetime
from ultralytics import YOLO

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
#MODEL_PATH           = "best.pt"
# Get the absolute path to the model file (works both locally and on Render)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_model_path = os.path.join(_current_dir, '..', 'best.pt')
MODEL_PATH = os.path.abspath(_model_path)

CONFIDENCE_THRESHOLD = 0.65

SPECIES_COLORS = {
    "lions":   (0, 255, 0),
    "hyenas":  (128, 0, 128),
    "Buffalo": (0, 0, 255),
}

# ── LOGGING THROTTLE ──────────────────────────────────────────────────────────
LOG_COOLDOWN_SECONDS = 5
_last_logged_times   = {}

# ── LOAD MODEL ────────────────────────────────────────────────────────────────
model = YOLO(MODEL_PATH)
print(f"✅ YOLOv11 model loaded: {MODEL_PATH}")

# ── GLOBAL STATE ──────────────────────────────────────────────────────────────
_camera_active  = False
_camera_thread  = None
_latest_frame   = None
_latest_dets    = []
_frame_count    = 0
_fps_timestamps = []


# ── PUBLIC CONTROL FUNCTIONS ──────────────────────────────────────────────────
def start_video_processing(source: str):
    global _camera_active, _camera_thread, _last_logged_times
    _camera_active     = True
    _last_logged_times = {}
    _camera_thread = threading.Thread(
        target=_processing_loop, args=(source,), daemon=True
    )
    _camera_thread.start()


latest_processed_frame = None

def process_remote_frame(frame):
    global latest_processed_frame
    
    # 1. Run YOLO detection
    results = model(frame)
    
    # 2. Draw boxes
    annotated = results[0].plot()
    
    # 3. Save to global for the MJPEG stream
    _, buffer = cv2.imencode('.jpg', annotated)
    latest_processed_frame = buffer.tobytes()

def get_latest_frame():
    return latest_processed_frame


def stop_video_processing():
    global _camera_active
    _camera_active = False


def is_camera_active() -> bool:
    return _camera_active

def get_live_detections() -> list:
    return _latest_dets

def get_latest_frame():
    return _latest_frame

def get_frame_count() -> int:
    return _frame_count

def get_fps() -> float:
    if len(_fps_timestamps) < 2:
        return 0.0
    duration = _fps_timestamps[-1] - _fps_timestamps[0]
    return (len(_fps_timestamps) - 1) / duration if duration > 0 else 0.0


# ── BACKGROUND PROCESSING LOOP ────────────────────────────────────────────────

def _processing_loop(source: str):
    global _camera_active, _latest_frame, _latest_dets, _frame_count, _fps_timestamps

    cap = cv2.VideoCapture(0 if source == "webcam" else source)
    if not cap.isOpened():
        print(f"❌ Could not open: {source}")
        _camera_active = False
        return

    print(f"📹 Processing started: {source}")

    from database.db import save_detection
    from detection.alerts import check_and_send_alert

    while _camera_active:
        ret, frame = cap.read()

        if not ret:
            if source != "webcam":
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            break

        _frame_count += 1
        _fps_timestamps.append(datetime.now().timestamp())
        _fps_timestamps = _fps_timestamps[-30:]

        # Run detection every 3 frames to keep video smooth
        if _frame_count % 3 == 0:
            detections   = _run_detection(frame)
            _latest_dets = detections
        else:
            detections = _latest_dets

        # Draw bounding boxes
        annotated = _draw_boxes(frame, detections)

        # Encode to JPEG
        _, jpeg       = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        _latest_frame = jpeg.tobytes()

        # ── SAVE TO DATABASE + SEND ALERT (throttled) ──────────────────────
        now = datetime.now().timestamp()

        for det in detections:
            species    = det["species"]
            confidence = det["confidence"]

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            last_logged = _last_logged_times.get(species, 0)
            if now - last_logged >= LOG_COOLDOWN_SECONDS:
                # ⭐ Pass the annotated JPEG frame to both save and alert
                # This means the screenshot already has the bounding box drawn
                save_detection(det, jpeg.tobytes())
                check_and_send_alert(det, jpeg.tobytes())  # ⭐ frame passed here
                _last_logged_times[species] = now
                print(f"✅ Logged & alert triggered — {species} at {confidence:.0%}")

        # Frame rate cap
        time.sleep(0.03)

    cap.release()
    _camera_active = False
    print("📹 Processing stopped.")


# ── DETECTION FUNCTION ────────────────────────────────────────────────────────
def _run_detection(frame) -> list:
    results    = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
    detections = []
    for box in results.boxes:
        class_id   = int(box.cls[0])
        species    = model.names[class_id]
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        detections.append({
            "species":    species,
            "confidence": round(confidence, 3),
            "bbox":       [x1, y1, x2, y2],
        })
    return detections


# ── DRAW BOUNDING BOXES ───────────────────────────────────────────────────────
def _draw_boxes(frame, detections: list):
    out = frame.copy()
    for det in detections:
        species = det["species"]
        color   = SPECIES_COLORS.get(species, (255, 255, 255))
        x1, y1, x2, y2 = det.get("bbox", [0, 0, 100, 100])
        label = f"{species.capitalize()} {det['confidence']:.0%}"

        # Filled label background
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(out, (x1, y1 - h - 14), (x1 + w + 6, y1), color, -1)
        cv2.putText(out, label, (x1 + 3, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # Bounding box outline
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

    return out