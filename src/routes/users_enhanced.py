from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.user import User, Role, Permission
from src.routes.auth import token_required

users_enhanced_bp = Blueprint('users_enhanced', __name__)

# Get all users with pagination and filtering
@users_enhanced_bp.route('', methods=['GET'])
@token_required
def get_users(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to view users'
        }), 403
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    role_id = request.args.get('role', None, type=int)
    
    # Build query
    query = User.query.filter(User.is_deleted == False)
    
    # Apply filters
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(User.status == status)
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    # Paginate results
    paginated_users = query.order_by(User.username).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [user.to_dict() for user in paginated_users.items],
            'total': paginated_users.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_users.pages
        },
        'message': 'Users retrieved successfully'
    }), 200

# Get user by ID
@users_enhanced_bp.route('/<user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    # Check if user has admin role or is viewing their own profile
    if not (current_user.role and 'ADMIN' in current_user.role.role_code) and str(current_user.id) != user_id:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to view this user'
        }), 403
    
    try:
        user = User.query.filter_by(id=user_id, is_deleted=False).first()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': user.to_dict(),
            'message': 'User retrieved successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Create new user
@users_enhanced_bp.route('', methods=['POST'])
@token_required
def create_user(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to create users'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['username', 'email', 'password', 'roleId']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username'], is_deleted=False).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Username already exists'
        }), 409
    
    if User.query.filter_by(email=data['email'], is_deleted=False).first():
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
        role_id=data['roleId'],
        status=data.get('status', 'ACTIVE'),
        first_name=data.get('firstName'),
        last_name=data.get('lastName'),
        phone=data.get('phone'),
        position=data.get('position')
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_user.to_dict(),
        'message': 'User created successfully'
    }), 201

# Update user
@users_enhanced_bp.route('/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    # Check if user has admin role or is updating their own profile
    if not (current_user.role and 'ADMIN' in current_user.role.role_code) and str(current_user.id) != user_id:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to update this user'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    user = User.query.filter_by(id=user_id, is_deleted=False).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'User not found'
        }), 404
    
    # Check if username or email already exists for another user
    if 'username' in data and data['username'] != user.username:
        existing_user = User.query.filter_by(username=data['username'], is_deleted=False).first()
        if existing_user and str(existing_user.id) != user_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Username already exists'
            }), 409
    
    if 'email' in data and data['email'] != user.email:
        existing_user = User.query.filter_by(email=data['email'], is_deleted=False).first()
        if existing_user and str(existing_user.id) != user_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Email already exists'
            }), 409
    
    # Update fields
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'firstName' in data:
        user.first_name = data['firstName']
    if 'lastName' in data:
        user.last_name = data['lastName']
    if 'phone' in data:
        user.phone = data['phone']
    if 'position' in data:
        user.position = data['position']
    
    # Only admins can update role and status
    if current_user.role and 'ADMIN' in current_user.role.role_code:
        if 'roleId' in data:
            user.role_id = data['roleId']
        if 'status' in data:
            user.status = data['status']
    
    # Update password if provided
    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])
    
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': user.to_dict(),
        'message': 'User updated successfully'
    }), 200

# Delete user (soft delete)
@users_enhanced_bp.route('/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete users'
        }), 403
    
    user = User.query.filter_by(id=user_id, is_deleted=False).first()
    
    if not user:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'User not found'
        }), 404
    
    # Prevent self-deletion
    if str(current_user.id) == user_id:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'You cannot delete your own account'
        }), 400
    
    # Soft delete
    user.is_deleted = True
    user.status = 'INACTIVE'
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'User deleted successfully'
    }), 200

# Get all roles
@users_enhanced_bp.route('/roles', methods=['GET'])
@token_required
def get_roles(current_user):
    roles = Role.query.all()
    
    return jsonify({
        'success': True,
        'data': [role.to_dict() for role in roles],
        'message': 'Roles retrieved successfully'
    }), 200

# Get all permissions
@users_enhanced_bp.route('/permissions', methods=['GET'])
@token_required
def get_permissions(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to view permissions'
        }), 403
    
    permissions = Permission.query.all()
    
    return jsonify({
        'success': True,
        'data': [permission.to_dict() for permission in permissions],
        'message': 'Permissions retrieved successfully'
    }), 200

