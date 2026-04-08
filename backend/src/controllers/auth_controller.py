# backend/src/controllers/auth_controller.py
from flask import request, jsonify
from ..service.auth_service import AuthService
from ..service.otp_service import OTPService
from ..utils.jwt_utils import generate_token
from ..middleware.auth_middleware import token_required

class AuthController:
    
    @staticmethod
    def register():
        """Register new user - sends OTP for verification"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')

            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            # Check if user already exists and is verified
            from ..models.user import User
            existing = User.find_by_email(email)
            if existing:
                if existing.get('is_verified'):
                    return jsonify({'error': 'Email already registered'}), 400
                else:
                    # Resend OTP for unverified user
                    OTPService.create_and_send_otp(email)
                    return jsonify({
                        'success': True,
                        'message': 'User exists but not verified. OTP sent again.',
                        'requires_verification': True,
                        'email': email
                    }), 200
            
            # Create new user
            result = AuthService.register_user(email, password, name)
            
            # Send OTP
            otp_sent = OTPService.create_and_send_otp(email)
            
            return jsonify({
                'success': True,
                'message': 'Registration successful! Please verify your email with the OTP sent.',
                'requires_verification': True,
                'email': email,
                'user_id': result['user_id'],
                'otp_sent': otp_sent
            }), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def verify_otp():
        """Verify OTP code"""
        try:
            data = request.get_json()
            email = data.get('email')
            otp_code = data.get('otp_code')
            
            if not email or not otp_code:
                return jsonify({'error': 'Email and OTP code required'}), 400
            
            from ..models.user import User
            is_valid = User.verify_otp(email, otp_code)
            
            if is_valid:
                # Get user to generate token
                user = User.find_by_email(email)
                token = generate_token(user['id'], user['email'], user.get('role', 'user'))
                
                return jsonify({
                    'success': True,
                    'message': 'Email verified successfully!',
                    'token': token,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'name': user.get('name'),
                        'role': user.get('role', 'user')
                    }
                }), 200
            else:
                return jsonify({'error': 'Invalid or expired OTP'}), 400
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def resend_otp():
        """Resend OTP code"""
        try:
            data = request.get_json()
            email = data.get('email')
            
            if not email:
                return jsonify({'error': 'Email required'}), 400
            
            from ..models.user import User
            user = User.find_by_email(email)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if user.get('is_verified'):
                return jsonify({'error': 'Email already verified'}), 400
            
            # Resend OTP
            otp_sent = OTPService.create_and_send_otp(email)
            
            return jsonify({
                'success': True,
                'message': 'OTP sent successfully',
                'otp_sent': otp_sent
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @staticmethod
    def login():
        """Login user - requires verified email"""
        try:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return jsonify({'error': 'Email and password required'}), 400
            
            from ..models.user import User
            
            # Check if email is verified
            if not User.is_email_verified(email):
                return jsonify({
                    'error': 'Email not verified. Please verify your email first.',
                    'requires_verification': True,
                    'email': email
                }), 403
            
            user = AuthService.login_user(email, password)
            
            # Generate token
            token = generate_token(user['id'], user['email'], user['role'])
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user,
                'token': token
            }), 200
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        

    @staticmethod
    @token_required
    def get_profile(current_user):
        """Get current user profile"""
        from ..models.user import User
        
        user = User.find_by_id(current_user['id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Remove password from response
        user.pop('password', None)
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
    
    @staticmethod
    @token_required
    def update_profile(current_user):
        """Update user profile"""
        from ..models.user import User
        
        data = request.get_json()
        allowed_fields = ['name']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        User.update(current_user['id'], update_data)
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        }), 200
    
    @staticmethod
    @token_required
    def logout(current_user):
        """Logout user"""
        # In a real implementation, you would blacklist the token
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200