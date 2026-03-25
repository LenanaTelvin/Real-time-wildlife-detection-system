"""
================================================================
  backend/database/db_manager.py  — DATABASE ABSTRACTION LAYER
  Provides a unified interface for both SQLite (local) and 
  PostgreSQL (production on Render).
================================================================
"""

import os
import json
from datetime import datetime
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = DATABASE_URL is not None

# PostgreSQL connection pool (for production)
pg_pool = None

def get_db_connection():
    """Returns a database connection based on environment."""
    if USE_POSTGRES:
        global pg_pool
        if pg_pool is None:
            pg_pool = SimpleConnectionPool(
                1, 20, DATABASE_URL, cursor_factory=RealDictCursor
            )
        return pg_pool.getconn()
    else:
        # SQLite for local development
        conn = sqlite3.connect("wildlife_detections.db")
        conn.row_factory = sqlite3.Row
        return conn

def release_db_connection(conn):
    """Release database connection back to pool (PostgreSQL) or close (SQLite)."""
    if USE_POSTGRES:
        global pg_pool
        if pg_pool:
            pg_pool.putconn(conn)
    else:
        conn.close()

def init_database():
    """
    Creates tables if they don't exist yet.
    Works with both SQLite and PostgreSQL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            # PostgreSQL schema
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
            
            # Seed default user
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()['count'] == 0:
                cursor.execute(
                    "INSERT INTO users (username, email) VALUES (%s, %s)",
                    ("admin", "admin@example.com")
                )
        else:
            # SQLite schema (existing code)
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
        print(f"✅ Database ready! Using: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        release_db_connection(conn)

def save_detection(detection: dict, frame_bytes: bytes = None):
    """
    Inserts one detection into the database.
    """
    import base64
    now = datetime.now()
    snapshot = base64.b64encode(frame_bytes).decode() if frame_bytes else None
    
    conn = get_db_connection()
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
    """
    Marks the most recent detection of that species as alerted.
    """
    conn = get_db_connection()
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
    """Removes one row by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("DELETE FROM detections WHERE id=%s", (detection_id,))
        else:
            cursor.execute("DELETE FROM detections WHERE id=?", (detection_id,))
        
        conn.commit()
    finally:
        release_db_connection(conn)

def get_detection_logs(limit: int = 50, species_filter: str = None) -> list:
    """Returns detection rows for the history table."""
    conn = get_db_connection()
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
            # Convert RealDictRow to regular dict
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
    """Returns total counts for stats panel."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as total FROM detections")
            total = cursor.fetchone()['total']
            
            cursor.execute(
                "SELECT species, COUNT(*) as cnt FROM detections GROUP BY species"
            )
            rows = cursor.fetchall()
            by_species = {r['species']: r['cnt'] for r in rows}
            
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) as count FROM detections WHERE date=%s",
                (today,)
            )
            today_count = cursor.fetchone()['count']
        else:
            total = cursor.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
            
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