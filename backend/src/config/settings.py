# backend/src/config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # App settings
    APP_NAME = "Wildlife Detection System"
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    
    # JWT settings
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-key-change-this')
    JWT_ACCESS_EXPIRY_HOURS = int(os.getenv('JWT_ACCESS_EXPIRY_HOURS', 24))
    
    # Email settings
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@wildlifedetection.com')
    
    # Frontend URL for email links
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Upload settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 10))
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mov'}
    
    # AI settings
    CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.68))
    
settings = Settings()