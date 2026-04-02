"""
================================================================
  backend/detection/model.py  — YOLOV11 + VIDEO PROCESSING
================================================================
"""

import cv2
import os
import time
import threading
import queue
from datetime import datetime
#from ultralytics import YOLO
# ── CONDITIONAL IMPORT FOR YOLO ───────────────────────────────────────────────
# This allows the app to run on Render without ultralytics (tunnel mode)
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("✅ Ultralytics available - local detection mode")
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ Ultralytics not available - running in tunnel mode only")

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
_current_dir = os.path.dirname(os.path.abspath(__file__))
_model_path  = os.path.join(_current_dir, '..', 'best.pt')
MODEL_PATH   = os.path.abspath(_model_path)

CONFIDENCE_THRESHOLD = 0.68

# ── FIX 1: Normalised all keys to lowercase so they match model.names output ──
SPECIES_COLORS = {
    "lions":   (0, 255, 0),
    "hyenas":  (128, 0, 128),
    "Buffalo": (0, 0, 255),   
}

_logged_this_session  = set()
_alerted_this_session = set()

# ── LOAD MODEL ────────────────────────────────────────────────────────────────
"""model = YOLO(MODEL_PATH)
print(f"YOLOv11 model loaded: {MODEL_PATH}")"""
# ── LOAD MODEL (only if available) ────────────────────────────────────────────
if YOLO_AVAILABLE:
    model = YOLO(MODEL_PATH)
    print(f"✅ YOLOv11 model loaded: {MODEL_PATH}")
else:
    model = None
    print("⚠️ No local model - will use tunnel for ML processing")

# ── GLOBAL STATE ──────────────────────────────────────────────────────────────
_camera_active  = False
_camera_thread  = None
_latest_frame   = None          # single shared frame store (see FIX 2)
_latest_dets    = []
_frame_count    = 0
_fps_timestamps = []

_remote_frame_queue = queue.Queue(maxsize=1) 


# ── PUBLIC CONTROL FUNCTIONS ──────────────────────────────────────────────────
def start_video_processing(source: str):
    global _camera_active, _camera_thread
    # ── FIX 2: Corrected 'global' declaration — was missing keyword on second var ──
    global _logged_this_session, _alerted_this_session   # was: global_logged_this_session, _alerted_this_session

    _logged_this_session  = set()
    _alerted_this_session = set()
    _camera_active = True

    _camera_thread = threading.Thread(
        target=_processing_loop, args=(source,), daemon=True
    )
    _camera_thread.start()


# ── FIX 3: Removed duplicate get_latest_frame() that used a different global ──
# process_remote_frame now writes to _latest_frame (same global as the loop)
# so the MJPEG stream endpoint always has the freshest frame regardless of source.
def process_remote_frame(frame):
    """
    Called by /api/video/upload_frame.
    Just queues the frame and returns immediately — no blocking.
    A single background worker thread handles detection and display.
    """
    try:
        _remote_frame_queue.put_nowait(frame)  # drop old frame if queue full
    except queue.Full:
        pass  # queue full means worker is busy — just skip this frame


def _start_remote_worker():
    """
    Starts a single background worker thread that processes
    one frame at a time — no race conditions, no glitching.
    """
    threading.Thread(target=_remote_worker_loop, daemon=True).start()


def _remote_worker_loop():
    """Single worker — processes frames one at a time from the queue."""
    global _latest_frame, _latest_dets
    global _logged_this_session, _alerted_this_session

    from database.db_manager import save_detection
    from detection.alerts import check_and_send_alert

    while True:
        try:
            # Wait for next frame — blocks until one arrives
            frame = _remote_frame_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        # Run detection
        detections   = _run_detection(frame)
        _latest_dets = detections

        # Draw boxes
        annotated = _draw_boxes(frame, detections)
        success, buffer = cv2.imencode(
            '.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80]
        )
        if success:
            _latest_frame = buffer.tobytes()

        # Log and alert
        for det in detections:
            species    = det["species"]
            confidence = det["confidence"]

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            if species not in _logged_this_session:
                save_detection(det, buffer.tobytes())
                _logged_this_session.add(species)
                print(f"Logged (remote) — {species} at {confidence:.0%}")

            if species not in _alerted_this_session:
                check_and_send_alert(det, buffer.tobytes())
                _alerted_this_session.add(species)
                print(f"Alert triggered (remote) — {species}")


def get_latest_frame():
    """Single definition — returns the shared _latest_frame global."""
    return _latest_frame                                 # removed the duplicate that returned latest_processed_frame


def stop_video_processing():
    global _camera_active
    _camera_active = False


def is_camera_active() -> bool:
    return _camera_active

def get_live_detections() -> list:
    return _latest_dets

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
    global _logged_this_session, _alerted_this_session

    cap = cv2.VideoCapture(0 if source == "webcam" else source)
    if not cap.isOpened():
        print(f"Could not open: {source}")
        _camera_active = False
        return

    print(f"Processing started: {source}")

    # ── FIX 5: Import from db_manager (Postgres-aware) not db.py (SQLite-only) ──
    from database.db_manager import save_detection       # was: from database.db
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

        if _frame_count % 3 == 0:
            detections   = _run_detection(frame)
            _latest_dets = detections
        else:
            detections = _latest_dets

        annotated = _draw_boxes(frame, detections)

        _, jpeg       = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        _latest_frame = jpeg.tobytes()

        now = datetime.now().timestamp()

        for det in detections:
            species    = det["species"]
            confidence = det["confidence"]

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            if species not in _logged_this_session:
                save_detection(det, jpeg.tobytes())
                _logged_this_session.add(species)
                print(f"Logged — {species} at {confidence:.0%} (first this session)")

            if species not in _alerted_this_session:
                check_and_send_alert(det, jpeg.tobytes())
                _alerted_this_session.add(species)
                print(f"Alert triggered — {species} (first this session)")

        time.sleep(0.03)

    cap.release()
    _camera_active = False
    print("Processing stopped.")


# ── DETECTION FUNCTION ────────────────────────────────────────────────────────
def _run_detection(frame) -> list:
    if model is None:
        return []  # Return empty detections in tunnel mode
    
    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
    #results    = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]
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

        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(out, (x1, y1 - h - 14), (x1 + w + 6, y1), color, -1)
        cv2.putText(out, label, (x1 + 3, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

    return out

_start_remote_worker()