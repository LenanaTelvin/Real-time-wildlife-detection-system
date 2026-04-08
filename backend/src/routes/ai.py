# backend/src/routes/ai.py
from flask import Blueprint,jsonify
from ..controllers.ai_controller import AIController

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# Model info
ai_bp.route('/info', methods=['GET'])(AIController.get_model_info)

# Video detection endpoint
ai_bp.route('/detect-video', methods=['POST'])(AIController.detect_video)

@ai_bp.route('/video-info', methods=['GET'])
def video_info():
    """Get video processing info"""
    from detection.model import CONFIDENCE_THRESHOLD, MODEL_PATH, YOLO_AVAILABLE
    
    return jsonify({
        'success': True,
        'video_processing': {
            'supported_formats': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'confidence_threshold': CONFIDENCE_THRESHOLD,
            'model_loaded': YOLO_AVAILABLE,
            'model_path': MODEL_PATH,
            'species': ['lions', 'hyenas', 'buffalo']
        }
    }), 200
# Statistics and history (using your existing db functions)
ai_bp.route('/stats', methods=['GET'])(AIController.get_stats)
ai_bp.route('/history', methods=['GET'])(AIController.get_history)