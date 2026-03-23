"""
================================================================
  backend/utils/storage.py  — FILE UPLOAD MANAGEMENT
  Handles file uploads for both local development and Render
================================================================
"""

import os
import uuid
import shutil
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from pathlib import Path

class UploadManager:
    def __init__(self):
        # Check if we're on Render
        self.is_render = os.environ.get('RENDER') == 'true'
        self.is_production = os.environ.get('DATABASE_URL') is not None
        
        if self.is_render:
            # On Render, use /tmp for temporary storage (ephemeral)
            self.upload_folder = '/tmp/uploads'
            self.max_file_age_hours = 24  # Auto-clean after 24 hours
        else:
            # Local development (persistent)
            self.upload_folder = 'uploads'
            self.max_file_age_hours = 168  # Keep for 7 days locally
        
        # Create folder if it doesn't exist
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Allowed file extensions
        self.allowed_extensions = {'mp4', 'avi', 'mov', 'mkv', 'jpg', 'jpeg', 'png', 'webm'}
        
        # Max file size (100MB)
        self.max_file_size = 100 * 1024 * 1024
        
        print(f"📁 Upload folder initialized: {self.upload_folder}")
        if self.is_render:
            print("   Running on Render - using ephemeral storage (/tmp)")
    
    def allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_upload(self, file):
        """
        Save uploaded file and return path
        
        Args:
            file: Flask file object
            
        Returns:
            str: Path to saved file
        """
        # Validate file
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        if not self.allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}")
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Seek back to beginning
        
        if size > self.max_file_size:
            raise ValueError(f"File too large. Max size: {self.max_file_size / (1024*1024)}MB")
        
        # Generate secure filename with unique ID
        filename = secure_filename(file.filename)
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{unique_id}_{filename}"
        
        filepath = os.path.join(self.upload_folder, unique_filename)
        
        # Save the file
        file.save(filepath)
        
        # Store metadata (optional - for tracking)
        self._save_metadata(unique_filename, {
            'original_name': filename,
            'size': size,
            'uploaded_at': datetime.now().isoformat(),
            'path': filepath
        })
        
        print(f"✅ File saved: {unique_filename} ({size / (1024*1024):.2f}MB)")
        return filepath
    
    def _save_metadata(self, filename, metadata):
        """Save metadata for uploaded files (for cleanup tracking)"""
        metadata_file = os.path.join(self.upload_folder, '.upload_metadata.json')
        
        import json
        try:
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            data[filename] = metadata
            
            with open(metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save metadata: {e}")
    
    def get_file_path(self, filename):
        """Get full path for a file"""
        return os.path.join(self.upload_folder, filename)
    
    def delete_file(self, filename):
        """Delete a specific file"""
        filepath = self.get_file_path(filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️  Deleted file: {filename}")
            return True
        return False
    
    def cleanup_temp_files(self, age_hours=None):
        """
        Clean up temporary files older than specified hours
        
        Args:
            age_hours: Age threshold in hours (uses self.max_file_age_hours if not specified)
        """
        if age_hours is None:
            age_hours = self.max_file_age_hours
        
        cutoff_time = datetime.now() - timedelta(hours=age_hours)
        deleted_count = 0
        
        try:
            for filename in os.listdir(self.upload_folder):
                filepath = os.path.join(self.upload_folder, filename)
                
                # Skip metadata file
                if filename == '.upload_metadata.json':
                    continue
                
                # Skip directories
                if os.path.isdir(filepath):
                    continue
                
                # Check file age
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_mtime < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} old files from {self.upload_folder}")
        
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    def get_storage_info(self):
        """Get storage usage information"""
        total_size = 0
        file_count = 0
        
        try:
            for filename in os.listdir(self.upload_folder):
                filepath = os.path.join(self.upload_folder, filename)
                if os.path.isfile(filepath) and filename != '.upload_metadata.json':
                    total_size += os.path.getsize(filepath)
                    file_count += 1
        except Exception as e:
            print(f"⚠️  Could not get storage info: {e}")
        
        return {
            'folder': self.upload_folder,
            'file_count': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'is_ephemeral': self.is_render
        }


# Create a singleton instance
upload_manager = UploadManager()
