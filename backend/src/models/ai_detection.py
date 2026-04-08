# backend/src/models/ai_detection.py
import json
from datetime import datetime
from ..config.database import get_db_connection, release_db_connection

class AIDetection:
    """Model for AI detection results - uses your existing db_manager"""
    
    @staticmethod
    def create(data):
        """Create a new detection record using your existing save_detection"""
        # Your existing save_detection expects a specific format
        detection_data = {
            'species': data.get('top_species', '').lower(),
            'confidence': data.get('top_confidence', 0),
            'bbox': data.get('bounding_box', [0, 0, 0, 0])
        }
        
        frame_bytes = data.get('frame_bytes')
        
        # Use your existing save_detection function
        from ..config.database import save_detection
        save_detection(detection_data, frame_bytes)
        
        # Also store additional metadata in a separate table if needed
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if ai_detections table exists, create if not
            if AIDetection._table_exists(cursor):
                # Store additional AI-specific data
                AIDetection._save_ai_metadata(cursor, data)
                conn.commit()
        except Exception as e:
            print(f"Note: AI metadata not stored: {e}")
        finally:
            release_db_connection(conn)
        
        return {'id': data.get('id'), 'success': True}
    
    @staticmethod
    def _table_exists(cursor):
        """Check if ai_detections table exists"""
        from ..config.database import USE_POSTGRES
        
        if USE_POSTGRES:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'ai_detections'
                )
            """)
            return cursor.fetchone()[0]
        else:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_detections'"
            )
            return cursor.fetchone() is not None
    
    @staticmethod
    def _save_ai_metadata(cursor, data):
        """Save AI-specific metadata"""
        from ..config.database import USE_POSTGRES
        
        # Create table if not exists
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_detections (
                    id SERIAL PRIMARY KEY,
                    detection_id INTEGER,
                    image_filename TEXT,
                    total_detections INTEGER,
                    class_counts TEXT,
                    top_species TEXT,
                    top_confidence REAL,
                    inference_time_ms INTEGER,
                    processed_by_user_id TEXT,
                    processed_by_email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_detections 
                (detection_id, image_filename, total_detections, class_counts, 
                 top_species, top_confidence, inference_time_ms, 
                 processed_by_user_id, processed_by_email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('detection_id'),
                data.get('image_filename'),
                data.get('total_detections', 0),
                json.dumps(data.get('class_counts', {})),
                data.get('top_species'),
                data.get('top_confidence', 0),
                data.get('inference_time_ms', 0),
                data.get('processed_by_user_id'),
                data.get('processed_by_email')
            ))
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    detection_id INTEGER,
                    image_filename TEXT,
                    total_detections INTEGER,
                    class_counts TEXT,
                    top_species TEXT,
                    top_confidence REAL,
                    inference_time_ms INTEGER,
                    processed_by_user_id TEXT,
                    processed_by_email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO ai_detections 
                (detection_id, image_filename, total_detections, class_counts, 
                 top_species, top_confidence, inference_time_ms, 
                 processed_by_user_id, processed_by_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('detection_id'),
                data.get('image_filename'),
                data.get('total_detections', 0),
                json.dumps(data.get('class_counts', {})),
                data.get('top_species'),
                data.get('top_confidence', 0),
                data.get('inference_time_ms', 0),
                data.get('processed_by_user_id'),
                data.get('processed_by_email')
            ))
    
    @staticmethod
    def find_by_user(user_id):
        """Get detections for a specific user"""
        from ..config.database import get_detection_logs
        
        # Use your existing get_detection_logs
        logs = get_detection_logs(limit=100)
        
        # Filter by user if needed (your existing table might not have user_id)
        # For now, return all logs
        return logs
    
    @staticmethod
    def get_statistics():
        """Get detection statistics using your existing function"""
        from ..config.database import get_detection_stats
        return get_detection_stats()
    
    @staticmethod
    def get_recent(limit=50):
        """Get recent detections"""
        from ..config.database import get_detection_logs
        return get_detection_logs(limit=limit)
    
    @staticmethod
    def delete_by_id(detection_id):
        """Delete a detection"""
        from ..config.database import delete_detection_by_id
        return delete_detection_by_id(detection_id)