# backend/src/service/auth_service.py
import sys
import os
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class AuthService:
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        return True, "OK"
    
    @staticmethod
    def register_user(email, password, name=None):
        """Register a new user"""
        from ..models.user import User
        
        # Validate inputs
        if not AuthService.validate_email(email):
            raise ValueError("Invalid email format")
        
        valid, msg = AuthService.validate_password(password)
        if not valid:
            raise ValueError(msg)
        
        # Check if user exists
        existing = User.find_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        
        # Create user
        user_id = User.create(email, password, name, 'user')
        
        return {
            'user_id': user_id,
            'email': email,
            'name': name
        }
    
    @staticmethod
    def login_user(email, password):
        """Login user"""
        from ..models.user import User
        
        user = User.find_by_email(email)
        if not user:
            raise ValueError("Invalid credentials")
        
        if not User.verify_password(password, user['password']):
            raise ValueError("Invalid credentials")
        
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user.get('name'),
            'role': user.get('role', 'user')
        }