# backend/src/routes/sightings.py
from flask import Blueprint
from ..controllers.sighting_controller import SightingController

sightings_bp = Blueprint('sightings', __name__, url_prefix='/api/sightings')

# Public routes
sightings_bp.route('/', methods=['GET'])(SightingController.get_all_sightings)

# Protected routes (require auth)
sightings_bp.route('/', methods=['POST'])(SightingController.create_sighting)
sightings_bp.route('/my-sightings', methods=['GET'])(SightingController.get_my_sightings)
sightings_bp.route('/<sighting_id>', methods=['PUT'])(SightingController.update_sighting)
sightings_bp.route('/<sighting_id>', methods=['DELETE'])(SightingController.delete_sighting)