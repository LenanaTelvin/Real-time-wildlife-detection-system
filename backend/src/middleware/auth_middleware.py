# backend/src/middleware/auth_middleware.py
from functools import wraps
from flask import request, jsonify, g
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.utils.jwt_utils import verify_token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        auth_header = request.headers.get('Authorization')
        if auth_header:
            if ' ' in auth_header:
                token = auth_header.split(' ')[1]
            else:
                token = auth_header
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        current_user = verify_token(token)
        if not current_user:
            return jsonify({'error': 'Token is invalid or expired'}), 401
        
        g.current_user = current_user
        return f(current_user, *args, **kwargs)
    
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.get('role') not in roles:
                return jsonify({'error': f'Role required: {", ".join(roles)}'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator