# backend/src/models/user.py
import sqlite3
import sys
import os
import uuid
import bcrypt
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from database.db_manager import get_db_connection, release_db_connection

class User:
    @staticmethod
    def create(email, password, name=None, role='user'):
        """Create a new user (unverified)"""
        user_id = str(uuid.uuid4())
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.utcnow()

        try:
            # Ensure OTP columns exist
            User._ensure_otp_columns(cursor)
            
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO users (id, email, password, name, role, created_at, is_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, 0)
                """, (user_id, email, password_hash, name, role, now))
            else:
                cursor.execute("""
                    INSERT INTO users (id, email, password, name, role, created_at, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (user_id, email, password_hash, name, role, now))
            
            conn.commit()
            return user_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def _ensure_otp_columns(cursor):
        """Ensure OTP columns exist in the users table"""
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_verified' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
        if 'otp_code' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN otp_code TEXT")
        if 'otp_expires_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN otp_expires_at TIMESTAMP")
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            else:
                cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            else:
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def update(user_id, data):
        """Update user information"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            for key, value in data.items():
                if USE_POSTGRES:
                    cursor.execute(f"UPDATE users SET {key} = %s WHERE id = %s", (value, user_id))
                else:
                    cursor.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
            conn.commit()
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def update_otp(email, otp_code, expires_at):
        """Store OTP for user"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("""
                    UPDATE users SET otp_code = %s, otp_expires_at = %s
                    WHERE email = %s
                """, (otp_code, expires_at, email))
            else:
                cursor.execute("""
                    UPDATE users SET otp_code = ?, otp_expires_at = ?
                    WHERE email = ?
                """, (otp_code, expires_at, email))
            conn.commit()
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def verify_otp(email, otp_code):
        """Verify OTP code and mark email as verified"""
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.utcnow()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE email = %s AND otp_code = %s AND otp_expires_at > %s
                """, (email, otp_code, now))
            else:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE email = ? AND otp_code = ? AND otp_expires_at > ?
                """, (email, otp_code, now))
            
            row = cursor.fetchone()
            
            if row:
                # Mark as verified and clear OTP
                if USE_POSTGRES:
                    cursor.execute("""
                        UPDATE users SET is_verified = 1, otp_code = NULL, otp_expires_at = NULL
                        WHERE email = %s
                    """, (email,))
                else:
                    cursor.execute("""
                        UPDATE users SET is_verified = 1, otp_code = NULL, otp_expires_at = NULL
                        WHERE email = ?
                    """, (email,))
                conn.commit()
                return True
            return False
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def is_email_verified(email):
        """Check if email is verified"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            from ..config.database import USE_POSTGRES
            if USE_POSTGRES:
                cursor.execute("SELECT is_verified FROM users WHERE email = %s", (email,))
            else:
                cursor.execute("SELECT is_verified FROM users WHERE email = ?", (email,))
            
            row = cursor.fetchone()
            return row and row[0] == 1
        finally:
            release_db_connection(conn)
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify password"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))