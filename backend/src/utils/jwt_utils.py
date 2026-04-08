# backend/src/utils/jwt_utils.py
import jwt
import datetime
import os

# Get secret from environment or use default (change in production!)
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-super-secret-jwt-key-change-this-in-production')
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

def generate_token(user_id, email, role='user'):
    """Generate JWT token"""
    # Modern way: use timezone-aware UTC datetime
    now = datetime.datetime.utcnow()
    expiry = now + datetime.timedelta(hours=JWT_EXPIRY_HOURS)
    
    payload = {
        'id': user_id,
        'email': email,
        'role': role,
        'exp': expiry,
        'iat': now
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def decode_token(token):
    """Decode token without verification (for debugging)"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'], options={'verify_signature': False})
    except:
        return None