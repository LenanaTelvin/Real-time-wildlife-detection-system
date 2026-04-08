# backend/src/service/ai_detection_service.py
import sys
import os
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import your existing detection functions
from detection.model import (
    _run_detection,
    _draw_boxes,
    CONFIDENCE_THRESHOLD,
    SPECIES_COLORS,
    YOLO_AVAILABLE,
    model as yolo_model
)

class AIDetectionService:
    """Service that uses your existing detection/model.py"""
    
    def __init__(self):
        self.is_loaded = YOLO_AVAILABLE and yolo_model is not None
        self.confidence_threshold = CONFIDENCE_THRESHOLD
        
        # Your 3 species (normalized to match your model's output)
        self.classes = ['lions', 'hyenas', 'buffalo']  # Lowercase to match model.names
        
        # Colors from your SPECIES_COLORS
        self.colors = SPECIES_COLORS
        
        self.hex_colors = {
            'lions': '#22c55e',
            'hyenas': '#a855f7',
            'buffalo': '#ef4444'
        }
        
        print(f"✅ AI Detection Service initialized")
        print(f"   Model loaded: {self.is_loaded}")
        print(f"   Confidence threshold: {self.confidence_threshold}")
        print(f"   Species: {', '.join(self.classes)}")
    
    def detect_species(self, image_bytes, user_info=None):
        """Run detection using your existing _run_detection function"""
        start_time = time.time()
        
        # Check if model is available
        if not self.is_loaded:
            return {
                'success': False,
                'error': 'AI model not available',
                'inference_time_ms': 0
            }
        
        try:
            # Convert bytes to OpenCV image (numpy array)
            import cv2
            import numpy as np
            
            # Decode image bytes to OpenCV format
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {
                    'success': False,
                    'error': 'Could not decode image',
                    'inference_time_ms': 0
                }
            
            # Use your existing _run_detection function
            detections = _run_detection(frame)
            
            # Parse results
            parsed_detections = []
            class_counts = {'lions': 0, 'hyenas': 0, 'buffalo': 0}
            species_confidences = {'lions': 0, 'hyenas': 0, 'buffalo': 0}
            
            for det in detections:
                species = det['species'].lower()  # Normalize to lowercase
                confidence = det['confidence']
                
                parsed_detections.append({
                    'species': species,
                    'confidence': confidence,
                    'confidence_percentage': f"{confidence * 100:.1f}%",
                    'bounding_box': det['bbox'],
                    'color': self.colors.get(species, (255, 255, 255))
                })
                
                if species in class_counts:
                    class_counts[species] += 1
                if confidence > species_confidences.get(species, 0):
                    species_confidences[species] = confidence
            
            # Find top prediction
            top_species = None
            top_confidence = 0
            for species, conf in species_confidences.items():
                if conf > top_confidence:
                    top_confidence = conf
                    top_species = species
            
            inference_time = int((time.time() - start_time) * 1000)
            
            # Also save to database using your existing save_detection
            if parsed_detections and top_confidence >= self.confidence_threshold:
                try:
                    from database.db_manager import save_detection
                    # Create detection dict in the format your db_manager expects
                    detection_data = {
                        'species': top_species,
                        'confidence': top_confidence,
                        'bbox': parsed_detections[0]['bounding_box'] if parsed_detections else [0,0,0,0]
                    }
                    # Save with the image bytes
                    save_detection(detection_data, image_bytes)
                except Exception as db_error:
                    print(f"Database save error: {db_error}")
            
            return {
                'success': True,
                'detections': parsed_detections,
                'total_detections': len(parsed_detections),
                'class_counts': class_counts,
                'species_confidences': species_confidences,
                'top_prediction': {
                    'species': top_species,
                    'confidence': top_confidence,
                    'detected': top_confidence >= self.confidence_threshold,
                    'percentage': f"{top_confidence * 100:.1f}%" if top_species else "0%"
                },
                'is_known_species': top_confidence >= self.confidence_threshold,
                'inference_time_ms': inference_time,
                'confidence_threshold': self.confidence_threshold
            }
            
        except Exception as e:
            print(f"Detection error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'inference_time_ms': int((time.time() - start_time) * 1000)
            }
    
    def get_model_info(self):
        """Get model information"""
        return {
            'name': 'YOLOv11 Wildlife Detector',
            'species': ['lions', 'hyenas', 'buffalo'],
            'colors': self.hex_colors,
            'confidence_threshold': self.confidence_threshold,
            'is_loaded': self.is_loaded,
            'model_available': YOLO_AVAILABLE,
            'model_path': 'backend/best.pt'
        }

# Create singleton instance
ai_detection_service = AIDetectionService()