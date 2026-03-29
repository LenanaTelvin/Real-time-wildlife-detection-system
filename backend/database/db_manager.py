"""
================================================================
  backend/database/db_manager.py  — UNIFIED DATABASE LAYER
  Handles both SQLite (local dev) and PostgreSQL (Render/prod).

  ── FIX 1: This is now the SINGLE database module used everywhere ──
  db.py (SQLite-only) has been retired. All imports across the
  project now point here:
    app.py          → init_database()
    api/routes.py   → save_detection, get_detection_logs,
                       get_detection_stats, delete_detection_by_id
    detection/model.py  → save_detection
    detection/alerts.py → mark_alert_sent

  Previously app.py called init_database() from db_manager (creating
  PostgreSQL tables) while routes.py and model.py imported from db.py
  (writing to a local SQLite file that doesn't exist on Render).
  All reads and writes were silently going to the wrong database.
================================================================
"""

import os
from datetime import datetime
import sqlite3

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# ── DATABASE SELECTION ────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = USE_POSTGRES = bool(DATABASE_URL and DATABASE_URL.strip())

pg_pool = None


def get_db_connection():
    if USE_POSTGRES:
        global pg_pool
        if pg_pool is None:
            pg_pool = ConnectionPool(DATABASE_URL, kwargs={"row_factory": dict_row})
        return pg_pool.getconn()

    conn = sqlite3.connect("wildlife_detections.db")
    conn.row_factory = sqlite3.Row
    return conn


def release_db_connection(conn):
    """Returns a PostgreSQL connection to the pool, or closes SQLite connection."""
    if USE_POSTGRES:
        if pg_pool:
            pg_pool.putconn(conn)
    else:
        conn.close()


# ── CREATE TABLES ─────────────────────────────────────────────────────────────
def init_database():
    """
    Creates the users and detections tables if they don't exist.
    Automatically uses the correct SQL dialect for the active database.
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    username   VARCHAR(100) NOT NULL,
                    email      VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id             SERIAL PRIMARY KEY,
                    species        VARCHAR(100) NOT NULL,
                    confidence     FLOAT NOT NULL,
                    timestamp      VARCHAR(20) NOT NULL,
                    date           VARCHAR(20) NOT NULL,
                    frame_snapshot TEXT,
                    alert_sent     INTEGER DEFAULT 0,
                    user_id        INTEGER REFERENCES users(id)
                )
            """)

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()['count'] == 0:
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (%s, %s)",
                    ("admin", "admin@example.com")
                )

        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT NOT NULL,
                    email      TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    species        TEXT    NOT NULL,
                    confidence     REAL    NOT NULL,
                    timestamp      TEXT    NOT NULL,
                    date           TEXT    NOT NULL,
                    frame_snapshot TEXT,
                    alert_sent     INTEGER DEFAULT 0,
                    user_id        INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (?, ?)",
                    ("admin", "admin@example.com")
                )

        conn.commit()
        print(f"Database ready — using: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}")

    except Exception as e:
        print(f"Database initialisation error: {e}")
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)


# ── WRITE ─────────────────────────────────────────────────────────────────────
def save_detection(detection: dict, frame_bytes: bytes = None):
    """
    Inserts one detection event into the database.
    Called by detection/model.py for both webcam and remote (phone) frames.

    detection = {
        "species":    "lions",
        "confidence": 0.87,
        "bbox":       [x1, y1, x2, y2]
    }
    """
    import base64
    now      = datetime.now()
    snapshot = base64.b64encode(frame_bytes).decode() if frame_bytes else None

    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO detections
                   (species, confidence, timestamp, date, frame_snapshot)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    detection["species"],
                    detection["confidence"],
                    now.strftime("%H:%M:%S"),
                    now.strftime("%Y-%m-%d"),
                    snapshot,
                )
            )
        else:
            cursor.execute(
                """INSERT INTO detections
                   (species, confidence, timestamp, date, frame_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    detection["species"],
                    detection["confidence"],
                    now.strftime("%H:%M:%S"),
                    now.strftime("%Y-%m-%d"),
                    snapshot,
                )
            )

        conn.commit()

    finally:
        release_db_connection(conn)


def mark_alert_sent(species: str):
    """Marks the most recent detection of a species as alerted."""
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute(
                """UPDATE detections SET alert_sent=1
                   WHERE id = (
                       SELECT id FROM detections
                       WHERE species=%s
                       ORDER BY id DESC
                       LIMIT 1
                   )""",
                (species,)
            )
        else:
            cursor.execute(
                """UPDATE detections SET alert_sent=1
                   WHERE id = (
                       SELECT id FROM detections
                       WHERE species=?
                       ORDER BY id DESC
                       LIMIT 1
                   )""",
                (species,)
            )

        conn.commit()

    finally:
        release_db_connection(conn)


def delete_detection_by_id(detection_id: int):
    """Removes one detection row. Called when user clicks Delete in the UI."""
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute("DELETE FROM detections WHERE id=%s", (detection_id,))
        else:
            cursor.execute("DELETE FROM detections WHERE id=?", (detection_id,))

        conn.commit()

    finally:
        release_db_connection(conn)


# ── READ ──────────────────────────────────────────────────────────────────────
def get_detection_logs(limit: int = 50, species_filter: str = None) -> list:
    """Returns detection rows for the history table, newest first."""
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            if species_filter:
                cursor.execute(
                    "SELECT * FROM detections WHERE species=%s ORDER BY id DESC LIMIT %s",
                    (species_filter, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM detections ORDER BY id DESC LIMIT %s",
                    (limit,)
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        else:
            if species_filter:
                cursor.execute(
                    "SELECT * FROM detections WHERE species=? ORDER BY id DESC LIMIT ?",
                    (species_filter, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,)
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    finally:
        release_db_connection(conn)


def get_detection_stats() -> dict:
    """
    Returns totals for the stats panel.
    Response shape:
    {
      "total": 245,
      "by_species": { "lions": 120, "hyenas": 85, "Buffalo": 40 },
      "today": 30
    }
    """
    conn   = get_db_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as total FROM detections")
            total = cursor.fetchone()['total']

            cursor.execute(
                "SELECT species, COUNT(*) as cnt FROM detections GROUP BY species"
            )
            rows       = cursor.fetchall()
            by_species = {r['species']: r['cnt'] for r in rows}

            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) as count FROM detections WHERE date=%s", (today,)
            )
            today_count = cursor.fetchone()['count']

        else:
            total = cursor.execute(
                "SELECT COUNT(*) FROM detections"
            ).fetchone()[0]

            rows = cursor.execute(
                "SELECT species, COUNT(*) as cnt FROM detections GROUP BY species"
            ).fetchall()
            by_species = {r["species"]: r["cnt"] for r in rows}

            today = datetime.now().strftime("%Y-%m-%d")
            today_count = cursor.execute(
                "SELECT COUNT(*) FROM detections WHERE date=?", (today,)
            ).fetchone()[0]

        return {"total": total, "by_species": by_species, "today": today_count}

    finally:
        release_db_connection(conn)