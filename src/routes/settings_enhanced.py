from flask import Blueprint, request, jsonify
from functools import wraps
from src.extensions import db
from src.models.setting import SystemSetting
from src.routes.auth import token_required

settings_enhanced_bp = Blueprint('settings_enhanced', __name__)

# Get all system settings
@settings_enhanced_bp.route('', methods=['GET'])
@token_required
def get_all_settings(current_user):
    # Only admins can view all settings
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to view system settings'
        }), 403

    settings = SystemSetting.query.all()
    return jsonify({
        'success': True,
        'data': [setting.to_dict() for setting in settings],
        'message': 'System settings retrieved successfully'
    }), 200

# Get a specific setting by key
@settings_enhanced_bp.route('/<string:setting_key>', methods=['GET'])
@token_required
def get_setting(current_user, setting_key):
    # Only admins can view specific settings
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to view system settings'
        }), 403

    setting = SystemSetting.query.filter_by(setting_key=setting_key).first()
    if not setting:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Setting not found'
        }), 404
    return jsonify({
        'success': True,
        'data': setting.to_dict(),
        'message': 'Setting retrieved successfully'
    }), 200

# Update a specific setting by key
@settings_enhanced_bp.route('/<string:setting_key>', methods=['PUT'])
@token_required
def update_setting(current_user, setting_key):
    # Only admins can update settings
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to update system settings'
        }), 403

    data = request.get_json()
    if not data or 'settingValue' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Setting value is required'
        }), 400

    setting = SystemSetting.query.filter_by(setting_key=setting_key).first()
    if not setting:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Setting not found'
        }), 404

    setting.setting_value = data['settingValue']
    setting.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({
        'success': True,
        'data': setting.to_dict(),
        'message': 'Setting updated successfully'
    }), 200

# Create a new setting
@settings_enhanced_bp.route('', methods=['POST'])
@token_required
def create_setting(current_user):
    # Only admins can create settings
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to create system settings'
        }), 403

    data = request.get_json()
    required_fields = ['settingKey', 'settingValue']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400

    if SystemSetting.query.filter_by(setting_key=data['settingKey']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Setting with this key already exists'
        }), 409

    new_setting = SystemSetting(
        setting_key=data['settingKey'],
        setting_value=data['settingValue'],
        description=data.get('description')
    )
    db.session.add(new_setting)
    db.session.commit()
    return jsonify({
        'success': True,
        'data': new_setting.to_dict(),
        'message': 'Setting created successfully'
    }), 201

# Delete a setting
@settings_enhanced_bp.route('/<string:setting_key>', methods=['DELETE'])
@token_required
def delete_setting(current_user, setting_key):
    # Only admins can delete settings
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message':'You do not have permission to delete system settings'
        }), 403

    setting = SystemSetting.query.filter_by(setting_key=setting_key).first()
    if not setting:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Setting not found'
        }), 404

    db.session.delete(setting)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Setting deleted successfully'
    }), 200


