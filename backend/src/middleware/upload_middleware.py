# backend/src/middleware/upload_middleware.py
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from functools import wraps

from ..config.settings import settings

def validate_file_extension(filename):
    """Check if file extension is allowed"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in settings.ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Check if file size is within limit"""
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= settings.MAX_FILE_SIZE_MB * 1024 * 1024

def handle_upload(f):
    """Decorator to handle file upload validation"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'file' not in request.files and 'image' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files.get('file') or request.files.get('image')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not validate_file_extension(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}'}), 400
        
        if not validate_file_size(file):
            return jsonify({'error': f'File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB'}), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Pass validated file to route
        return f(file, filename, *args, **kwargs)
    
    return decorated