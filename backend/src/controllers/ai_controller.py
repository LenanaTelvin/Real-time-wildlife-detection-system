# backend/src/controllers/ai_controller.py
from flask import request, jsonify
from ..service.ai_detection_service import ai_detection_service
from ..middleware.auth_middleware import token_required

# Import your existing db_manager functions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from database.db_manager import get_detection_stats, get_detection_logs

class AIController:
    
    @staticmethod
    @token_required
    def get_model_info(current_user):
        """Get AI model information"""
        model_info = ai_detection_service.get_model_info()
        return jsonify({
            'success': True,
            'model': model_info,
            'user': {
                'id': current_user.get('id'),
                'email': current_user.get('email')
            }
        }), 200
    
    # Video detect function AIController
    @staticmethod
    @token_required
    def detect_video(current_user):
        """Run AI detection on uploaded video"""
        try:
            if 'video' not in request.files:
                return jsonify({'error': 'No video provided'}), 400
            
            file = request.files['video']
            if file.filename == '':
                return jsonify({'error': 'No video selected'}), 400
            
            # Check file extension
            allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({'error': f'Video format not supported. Use: {allowed_extensions}'}), 400
            
            # Read video bytes
            video_bytes = file.read()
            
            # Save temporarily to process
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_video:
                temp_video.write(video_bytes)
                temp_path = temp_video.name
            
            try:
                # Import video processing functions from your existing model
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                from detection.model import _run_detection, _draw_boxes, CONFIDENCE_THRESHOLD
                
                import cv2
                
                # Open video
                cap = cv2.VideoCapture(temp_path)
                
                # Get video properties
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = total_frames / fps if fps > 0 else 0
                
                # Process video (sample every 10th frame for performance)
                sample_rate = request.form.get('sample_rate', 10, type=int)
                
                detections_summary = []
                species_counts = {'lions': 0, 'hyenas': 0, 'buffalo': 0}
                frame_results = []
                processed_frames = 0
                
                frame_count = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Process every Nth frame
                    if frame_count % sample_rate == 0:
                        # Run detection using your existing function
                        detections = _run_detection(frame)
                        
                        if detections:
                            # Draw boxes on frame
                            annotated = _draw_boxes(frame, detections)
                            
                            # Save frame as base64 for response (optional - only first few)
                            if len(frame_results) < 5:  # Only keep first 5 sample frames
                                _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                                import base64
                                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                frame_results.append({
                                    'frame_number': frame_count,
                                    'timestamp': frame_count / fps,
                                    'detections': detections,
                                    'image': frame_base64
                                })
                        
                        # Count species
                        for det in detections:
                            species = det['species'].lower()
                            if species in species_counts:
                                species_counts[species] += 1
                        
                        detections_summary.extend(detections)
                        processed_frames += 1
                    
                    frame_count += 1
                
                cap.release()
                
                # Calculate summary
                total_detections = len(detections_summary)
                
                # Find primary species (most detected)
                primary_species = max(species_counts, key=species_counts.get) if total_detections > 0 else None
                
                # Save detection to database (summary)
                if total_detections > 0:
                    from database.db_manager import save_detection
                    detection_data = {
                        'species': primary_species,
                        'confidence': 0.9,  # Average confidence could be calculated
                        'bbox': [0, 0, 0, 0]
                    }
                    save_detection(detection_data, None)
                
                # Clean up temp file
                os.unlink(temp_path)
                
                return jsonify({
                    'success': True,
                    'video_info': {
                        'filename': file.filename,
                        'duration_seconds': round(duration, 2),
                        'total_frames': total_frames,
                        'processed_frames': processed_frames,
                        'fps': fps,
                        'sample_rate': sample_rate
                    },
                    'detection_summary': {
                        'total_detections': total_detections,
                        'species_counts': species_counts,
                        'primary_species': primary_species
                    },
                    'sample_frames': frame_results,
                    'processed_by': current_user.get('email'),
                    'confidence_threshold': CONFIDENCE_THRESHOLD
                }), 200
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise e
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    

    
    @staticmethod
    @token_required
    def get_stats(current_user):
        """Get detection statistics"""
        stats = get_detection_stats()
        return jsonify({
            'success': True,
            'statistics': stats,
            'user': current_user.get('email')
        }), 200
    
    @staticmethod
    @token_required
    def get_history(current_user):
        """Get detection history"""
        limit = request.args.get('limit', 50, type=int)
        species = request.args.get('species', None)
        logs = get_detection_logs(limit=limit, species_filter=species)
        
        # Convert any non-serializable types
        for log in logs:
            if 'id' in log:
                log['id'] = str(log['id'])
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': logs,
            'user': current_user.get('email')
        }), 200