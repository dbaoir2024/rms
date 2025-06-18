from flask import Blueprint, request, jsonify
from src.extensions import db  # No circular import!
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import uuid
from functools import wraps


from src.models.user import User, Role, Permission, Position

auth_bp = Blueprint('auth', __name__)

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if token is in headers
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Token is missing'
            }), 401
        
        try:
            # Decode token
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'Invalid token'
                }), 401
                
            if not current_user.is_active:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized',
                    'message': 'User account is inactive'
                }), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Invalid token'
            }), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

# Login route
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Email and password are required'
        }), 400
        
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Invalid email or password'
        }), 401
        
    if not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Invalid email or password'
        }), 401
        
    if not user.is_active:
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'User account is inactive'
        }), 401
        
    # Generate token
    token = jwt.encode({
        'user_id': str(user.id),
        'exp': datetime.datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    # Update last login
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': user.to_dict()
        },
        'message': 'Login successful'
    }), 200

# Google login route
@auth_bp.route('/google', methods=['POST'])
def google_login():
    data = request.get_json()
    
    if not data or not data.get('token'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Google token is required'
        }), 400
    
    # In a real implementation, you would verify the Google token
    # and extract user information from it
    # For this example, we'll assume the token contains user info
    
    # Check if user exists
    email = data.get('email')
    if not email:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Email is required'
        }), 400
        
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Create new user with Google info
        # In a real implementation, you would get this info from Google
        user = User(
            id=uuid.uuid4(),
            username=email.split('@')[0],
            email=email,
            password_hash=generate_password_hash('google_auth'),  # Placeholder
            first_name=data.get('firstName', 'Google'),
            last_name=data.get('lastName', 'User'),
            is_active=True
        )
        
        # Assign default role and position
        default_role = Role.query.filter_by(role_code='DATA_ENTRY').first()
        if default_role:
            user.role_id = default_role.id
            
        default_position = Position.query.filter_by(position_code='DLIROIR356').first()
        if default_position:
            user.position_id = default_position.id
            
        db.session.add(user)
        db.session.commit()
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'User account is inactive'
        }), 401
    
    # Generate token
    token = jwt.encode({
        'user_id': str(user.id),
        'exp': datetime.datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    # Update last login
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': user.to_dict()
        },
        'message': 'Google login successful'
    }), 200

# Register route
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
        
    required_fields = ['username', 'email', 'password', 'firstName', 'lastName', 'positionId']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Username already exists'
        }), 409
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Email already exists'
        }), 409
    
    # Create new user
    new_user = User(
        id=uuid.uuid4(),
        username=data['username'],
        email=data['email'],
        password_hash=generate_password_hash(data['password']),
        first_name=data['firstName'],
        last_name=data['lastName'],
        position_id=data['positionId'],
        role_id=data.get('roleId'),  # Optional
        is_active=True
    )
    
    # If no role provided, assign default role
    if not data.get('roleId'):
        default_role = Role.query.filter_by(role_code='DATA_ENTRY').first()
        if default_role:
            new_user.role_id = default_role.id
    
    db.session.add(new_user)
    db.session.commit()
    
    # Generate token
    token = jwt.encode({
        'user_id': str(new_user.id),
        'exp': datetime.datetime.utcnow() + app.config['JWT_EXPIRATION_DELTA']
    }, app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'success': True,
        'data': {
            'token': token,
            'user': new_user.to_dict()
        },
        'message': 'User registered successfully'
    }), 201

# Verify token route
@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    return jsonify({
        'success': True,
        'data': current_user.to_dict(),
        'message': 'Token is valid'
    }), 200

# Get user profile
@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({
        'success': True,
        'data': current_user.to_dict(),
        'message': 'Profile retrieved successfully'
    }), 200

# Update user profile
@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Update fields
    if 'firstName' in data:
        current_user.first_name = data['firstName']
    if 'lastName' in data:
        current_user.last_name = data['lastName']
    if 'email' in data:
        # Check if email already exists
        if data['email'] != current_user.email and User.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Email already exists'
            }), 409
        current_user.email = data['email']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': current_user.to_dict(),
        'message': 'Profile updated successfully'
    }), 200

# Change password
@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    
    if not data or not data.get('currentPassword') or not data.get('newPassword'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Current password and new password are required'
        }), 400
    
    # Verify current password
    if not check_password_hash(current_user.password_hash, data['currentPassword']):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Current password is incorrect'
        }), 401
    
    # Update password
    current_user.password_hash = generate_password_hash(data['newPassword'])
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    }), 200

# Request password reset
@auth_bp.route('/request-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Email is required'
        }), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        # Don't reveal that the user doesn't exist
        return jsonify({
            'success': True,
            'message': 'If your email is registered, you will receive a password reset link'
        }), 200
    
    # In a real implementation, you would generate a reset token
    # and send an email with a reset link
    
    return jsonify({
        'success': True,
        'message': 'If your email is registered, you will receive a password reset link'
    }), 200

# Reset password with token
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    
    if not data or not data.get('token') or not data.get('newPassword'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Token and new password are required'
        }), 400
    
    # In a real implementation, you would verify the reset token
    # and find the associated user
    
    # For this example, we'll assume the token is valid
    # and contains the user ID
    
    try:
        # Decode token
        token_data = jwt.decode(data['token'], app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.filter_by(id=token_data['user_id']).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid token'
            }), 400
        
        # Update password
        user.password_hash = generate_password_hash(data['newPassword'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        }), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Token has expired'
        }), 400
    except jwt.InvalidTokenError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid token'
        }), 400

# Get all roles
@auth_bp.route('/roles', methods=['GET'])
@token_required
def get_roles(current_user):
    # Check if user has permission
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    roles = Role.query.all()
    
    return jsonify({
        'success': True,
        'data': [role.to_dict() for role in roles],
        'message': 'Roles retrieved successfully'
    }), 200

# Get all positions
@auth_bp.route('/positions', methods=['GET'])
@token_required
def get_positions(current_user):
    positions = Position.query.all()
    
    return jsonify({
        'success': True,
        'data': [position.to_dict() for position in positions],
        'message': 'Positions retrieved successfully'
    }), 200
