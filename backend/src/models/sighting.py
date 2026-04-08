# backend/src/models/sighting.py
import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from database.db_manager import get_db_connection, release_db_connection

class Sighting:
    @staticmethod
    def create(data):
        """Create a new sighting"""
        sighting_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            now = datetime.utcnow()
            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO sightings (id, user_id, species,video_filename, video_duration, 
                        detection_count ,location_lat, location_lng, 
                                           notes, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    sighting_id,
                    data.get('user_id'),
                    data.get('species'),
                    data.get('video_filename'),
                    data.get('video_duration'),
                    data.get('detection_count', 0),
                    data.get('lat'),
                    data.get('lng'),
                    data.get('notes'),
                    now
                ))
            else:
                cursor.execute("""
                    INSERT INTO sightings (id, user_id, species,video_filename, video_duration, 
                        detection_count, location_lat, location_lng, , notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sighting_id,
                    data.get('user_id'),
                    data.get('species'),
                    data.get('video_filename'),
                    data.get('video_duration'),
                    data.get('detection_count', 0),
                    data.get('lat'),
                    data.get('lng'),
                    data.get('notes'),
                    now
                ))
            
            conn.commit()
            return sighting_id
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def find_by_user(user_id, limit=50):
        """Find sightings by user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("""
                    SELECT * FROM sightings WHERE user_id = %s 
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM sightings WHERE user_id = ? 
                    ORDER BY created_at DESC LIMIT ?
                """, (user_id, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def find_all(limit=100):
        """Get all sightings"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("""
                    SELECT s.*, u.email as user_email 
                    FROM sightings s
                    LEFT JOIN users u ON s.user_id = u.id
                    ORDER BY s.created_at DESC LIMIT %s
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT s.*, u.email as user_email 
                    FROM sightings s
                    LEFT JOIN users u ON s.user_id = u.id
                    ORDER BY s.created_at DESC LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            release_db_connection(conn)

    @staticmethod
    def update(sighting_id, data):
        """Update an existing sighting"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            
            # Build the SET clause dynamically
            set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
            values = list(data.values())
            values.append(sighting_id)
            
            if USE_POSTGRES:
                # Convert ? to %s for PostgreSQL
                set_clause = set_clause.replace('?', '%s')
                cursor.execute(f"""
                    UPDATE sightings 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, values)
            else:
                cursor.execute(f"""
                    UPDATE sightings 
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, values)
            
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            release_db_connection(conn)