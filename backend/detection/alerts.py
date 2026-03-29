"""
================================================================
  backend/detection/alerts.py  — EMAIL ALERT SERVICE
  Sends ONE email with a screenshot of the detected animal.
================================================================
"""

import os                        # ── FIX 1: Added os import for env var reading ──
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# ── EMAIL CONFIGURATION ───────────────────────────────────────────────────────
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587

# ── FIX 2: Credentials moved to environment variables ────────────────────────
# Previously: SMTP_EMAIL = "example@gmail.com" and SMTP_PASSWORD = "pacacuqfbfjq"
# were hardcoded in source code — a security risk even with placeholder values.
# Set these in your Render dashboard under Environment Variables, or in a .env file locally.

COOLDOWN_SECONDS = 30

_last_alert_times: dict = {}


def check_and_send_alert(detection: dict, frame_jpeg: bytes):
    """
    Called after every logged detection in model.py.

    Parameters:
      detection  — { species, confidence, bbox }
      frame_jpeg — JPEG bytes of the annotated frame (with bounding box drawn)

    Sends ONE email with the screenshot attached if cooldown has passed.
    """
    # ── FIX 3: Guard against missing credentials before attempting SMTP ──
    # Previously the code would try to connect and fail at server.login() with
    # a confusing error. Now it exits early with a clear message.

    SMTP_EMAIL     = os.environ.get("SMTP_EMAIL", "")
    SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD", "")
    RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "")

    if not SMTP_EMAIL or not SMTP_PASSWORD or not RECEIVER_EMAIL:
        print("Alert skipped — SMTP credentials not configured (check env vars: "
              "SMTP_EMAIL, SMTP_PASSWORD, RECEIVER_EMAIL)")
        return

    species = detection["species"]
    now     = datetime.now().timestamp()

    last = _last_alert_times.get(species, 0)
    if now - last < COOLDOWN_SECONDS:
        return

    _last_alert_times[species] = now

    thread = threading.Thread(
        target=_send_email,
        args=(detection, frame_jpeg),
        daemon=True
    )
    thread.start()


def _send_email(detection: dict, frame_jpeg: bytes):
    """Builds and sends the alert email with screenshot attached."""
    SMTP_EMAIL     = os.environ.get("SMTP_EMAIL", "")
    SMTP_PASSWORD  = os.environ.get("SMTP_PASSWORD", "")
    RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "")

    species    = detection["species"]
    confidence = detection["confidence"]
    timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    subject = f"Wildlife Alert: {species.capitalize()} Detected!"

    body = f"""
Wildlife Detection Alert
------------------------
Species    : {species.capitalize()}
Confidence : {confidence:.1%}
Time       : {timestamp}

A {species.capitalize()} was detected with {confidence:.1%} confidence.
Screenshot is attached to this email.

This alert was sent automatically by the Wildlife Detection System.
    """

    print(f"Sending alert for {species} to {RECEIVER_EMAIL}...")

    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_EMAIL
        msg["To"]      = RECEIVER_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        if frame_jpeg:
            image = MIMEImage(frame_jpeg, name=f"{species}_{timestamp}.jpg")
            image.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"{species}_{timestamp}.jpg"
            )
            msg.attach(image)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"Alert sent for {species} with screenshot attached!")

        # ── FIX 4: Import from db_manager not db.py ──────────────────────────
        from database.db_manager import mark_alert_sent   # was: from database.db
        mark_alert_sent(species)

    except smtplib.SMTPAuthenticationError:
        print("Authentication failed — check App Password and 2-Step Verification is ON")
        print(f"   Password length: {len(SMTP_PASSWORD)} chars (should be 16)")

    except smtplib.SMTPException as e:
        print(f"SMTP error: {e}")

    except Exception as e:
        print(f"Unexpected error sending alert: {e}")