# backend/src/config/database.py
import sys
import os

# Add parent directory to path to import your existing db_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import your existing database manager
from database.db_manager import (
    get_db_connection,
    release_db_connection,
    init_database,
    save_detection,
    get_detection_logs,
    get_detection_stats,
    delete_detection_by_id,
    mark_alert_sent,
    USE_POSTGRES
)

# Re-export for easy access from src modules
__all__ = [
    'get_db_connection',
    'release_db_connection', 
    'init_database',
    'save_detection',
    'get_detection_logs',
    'get_detection_stats',
    'delete_detection_by_id',
    'mark_alert_sent',
    'USE_POSTGRES'
]

# Also provide a db object for compatibility with existing code
class DatabaseWrapper:
    @staticmethod
    def get_connection():
        return get_db_connection()
    
    @staticmethod
    def release_connection(conn):
        return release_db_connection(conn)
    
    @staticmethod
    def save_detection(detection, frame_bytes=None):
        return save_detection(detection, frame_bytes)
    
    @staticmethod
    def get_stats():
        return get_detection_stats()
    
    @staticmethod
    def get_logs(limit=50, species_filter=None):
        return get_detection_logs(limit, species_filter)

db = DatabaseWrapper()