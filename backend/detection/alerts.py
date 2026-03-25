"""
================================================================
  backend/detection/alerts.py  — EMAIL ALERT SERVICE
  Sends ONE email with a screenshot of the detected animal.
================================================================
"""

import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# ── EMAIL CONFIGURATION ───────────────────────────────────────────────────────
SMTP_SERVER    = "smtp.gmail.com"
SMTP_PORT      = 587
SMTP_EMAIL     = "example@gmail.com"
SMTP_PASSWORD  = "pacacuqfbfjq"        
RECEIVER_EMAIL = "example@gmail.com"  

COOLDOWN_SECONDS = 30   # Only alert once per species every 30 seconds

_last_alert_times: dict = {}


def check_and_send_alert(detection: dict, frame_jpeg: bytes):
    """
    Called after every logged detection in model.py.
    
    Parameters:
      detection  — { species, confidence, bbox }
      frame_jpeg — JPEG bytes of the annotated frame (with bounding box drawn)
    
    Sends ONE email with the screenshot attached if cooldown has passed.
    """
    species = detection["species"]
    now     = datetime.now().timestamp()

    last = _last_alert_times.get(species, 0)
    if now - last < COOLDOWN_SECONDS:
        return  # Still in cooldown

    _last_alert_times[species] = now

    # Send email in background thread so it doesn't slow video
    thread = threading.Thread(
        target=_send_email,
        args=(detection, frame_jpeg),
        daemon=True
    )
    thread.start()


def _send_email(detection: dict, frame_jpeg: bytes):
    """Builds and sends the alert email with screenshot attached."""
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

    print(f"📧 Sending alert for {species} to {RECEIVER_EMAIL}...")

    try:
        msg = MIMEMultipart()
        msg["From"]    = SMTP_EMAIL
        msg["To"]      = RECEIVER_EMAIL
        msg["Subject"] = subject

        # ── BODY TEXT ──────────────────────────────────────────────────────
        msg.attach(MIMEText(body, "plain"))

        # ── ATTACH SCREENSHOT ──────────────────────────────────────────────
        # frame_jpeg is the annotated frame with bounding box already drawn
        if frame_jpeg:
            image = MIMEImage(frame_jpeg, name=f"{species}_{timestamp}.jpg")
            image.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"{species}_{timestamp}.jpg"
            )
            msg.attach(image)

        # ── SEND ───────────────────────────────────────────────────────────
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"✅ Alert sent for {species} with screenshot attached!")

        from database.db import mark_alert_sent
        mark_alert_sent(species)

    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed — check App Password and 2-Step Verification is ON")
        print(f"   Password length: {len(SMTP_PASSWORD)} chars (should be 16)")

    except smtplib.SMTPException as e:
        print(f"❌ SMTP error: {e}")

    except Exception as e:
        print(f"❌ Unexpected error sending alert: {e}")
