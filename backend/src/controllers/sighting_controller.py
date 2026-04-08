# backend/src/controllers/sighting_controller.py
from flask import request, jsonify
from ..models.sighting import Sighting
from ..middleware.auth_middleware import token_required

class SightingController:
    
    @staticmethod
    @token_required
    def create_sighting(current_user):
        """Create a new wildlife sighting"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['species']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            sighting_data = {
                'user_id': current_user.get('id'),
                'species': data.get('species'),
                'video_filename': data.get('video_filename'),
                'video_duration': data.get('video_duration'),
                'detection_count': data.get('detection_count', 1),
                'lat': data.get('lat'),
                'lng': data.get('lng'),
                'notes': data.get('notes')
            }
            
            sighting_id = Sighting.create(sighting_data)
            
            return jsonify({
                'success': True,
                'message': 'Sighting reported successfully',
                'sighting_id': sighting_id,
                'reported_by': current_user.get('email')
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def get_all_sightings():
        """Get all sightings (public)"""
        try:
            limit = request.args.get('limit', 100, type=int)
            sightings = Sighting.find_all(limit)
            
            return jsonify({
                'success': True,
                'count': len(sightings),
                'data': sightings
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def get_by_species(species):
        """Get sightings by species"""
        try:
            limit = request.args.get('limit', 50, type=int)
            sightings = Sighting.find_by_species(species, limit)
            
            return jsonify({
                'success': True,
                'species': species,
                'count': len(sightings),
                'data': sightings
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @token_required
    def get_my_sightings(current_user):
        """Get current user's sightings"""
        try:
            limit = request.args.get('limit', 50, type=int)
            sightings = Sighting.find_by_user(current_user.get('id'), limit)
            
            return jsonify({
                'success': True,
                'count': len(sightings),
                'data': sightings
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @token_required
    def update_sighting(current_user, sighting_id):
        """Update a sighting (only owner can update)"""
        try:
            # Get the data from request body
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # First, get the user's sightings
            sightings = Sighting.find_by_user(current_user.get('id'))
            
            # Find the specific sighting
            sighting = next((s for s in sightings if s.get('id') == sighting_id), None)
            
            if not sighting:
                return jsonify({'error': 'Sighting not found or not yours'}), 404
            
            # Define allowed fields that can be updated
            allowed_fields = [
                'species', 
                'video_filename', 
                'video_duration',
                'detection_count', 
                'location_lat', 
                'location_lng', 
                'notes'
            ]
            
            # Filter only allowed fields that were sent in the request
            update_data = {}
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
            
            if not update_data:
                return jsonify({'error': 'No valid fields to update'}), 400
            
            # Call update method in model (you need to add this to Sighting class)
            Sighting.update(sighting_id, update_data)
            
            return jsonify({
                'success': True,
                'message': 'Sighting updated successfully',
                'updated_fields': list(update_data.keys())
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    @token_required
    def delete_sighting(current_user, sighting_id):
        """Delete a sighting (only owner can delete)"""
        try:
            # This would need a delete method in the model
            return jsonify({
                'success': False,
                'message': 'Delete not implemented yet'
            }), 501
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500