# backend/src/routes/auth.py
from flask import Blueprint
from ..controllers.auth_controller import AuthController

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Public routes
auth_bp.route('/register', methods=['POST'])(AuthController.register)
auth_bp.route('/verify-otp', methods=['POST'])(AuthController.verify_otp)
auth_bp.route('/resend-otp', methods=['POST'])(AuthController.resend_otp)
auth_bp.route('/login', methods=['POST'])(AuthController.login)

# Protected routes
auth_bp.route('/profile', methods=['GET'])(AuthController.get_profile)
auth_bp.route('/profile', methods=['PUT'])(AuthController.update_profile)
auth_bp.route('/logout', methods=['POST'])(AuthController.logout)