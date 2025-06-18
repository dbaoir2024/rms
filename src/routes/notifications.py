from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime, timedelta

from src.extensions import db
from src.models.notification import Notification, UserNotification
from src.routes.auth import token_required

notifications_bp = Blueprint('notifications', __name__)

# Get all notifications for current user
@notifications_bp.route('', methods=['GET'])
@token_required
def get_notifications(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    is_read = request.args.get('isRead', None)
    is_urgent = request.args.get('isUrgent', None)
    
    # Build query for user notifications
    query = UserNotification.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if is_read is not None:
        is_read_bool = is_read.lower() == 'true'
        query = query.filter(UserNotification.is_read == is_read_bool)
    
    # Join with notifications table
    query = query.join(Notification)
    
    if is_urgent is not None:
        is_urgent_bool = is_urgent.lower() == 'true'
        query = query.filter(Notification.is_urgent == is_urgent_bool)
    
    # Order by creation date (newest first)
    query = query.order_by(Notification.created_at.desc())
    
    # Paginate results
    paginated_notifications = query.paginate(page=page, per_page=per_page)
    
    # Get notification data
    notification_data = []
    for user_notification in paginated_notifications.items:
        notification = Notification.query.get(user_notification.notification_id)
        if notification:
            notification_dict = notification.to_dict()
            notification_dict['isRead'] = user_notification.is_read
            notification_dict['readAt'] = user_notification.read_at.isoformat() if user_notification.read_at else None
            notification_data.append(notification_dict)
    
    return jsonify({
        'success': True,
        'data': {
            'items': notification_data,
            'total': paginated_notifications.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_notifications.pages,
            'unreadCount': UserNotification.query.filter_by(user_id=current_user.id, is_read=False).count()
        },
        'message': 'Notifications retrieved successfully'
    }), 200

# Get notification by ID
@notifications_bp.route('/<notification_id>', methods=['GET'])
@token_required
def get_notification(current_user, notification_id):
    # Check if notification exists
    notification = Notification.query.filter_by(id=notification_id).first()
    
    if not notification:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Notification not found'
        }), 404
    
    # Check if user has access to this notification
    user_notification = UserNotification.query.filter_by(
        user_id=current_user.id,
        notification_id=notification_id
    ).first()
    
    if not user_notification:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have access to this notification'
        }), 403
    
    # Get notification data
    notification_dict = notification.to_dict()
    notification_dict['isRead'] = user_notification.is_read
    notification_dict['readAt'] = user_notification.read_at.isoformat() if user_notification.read_at else None
    
    return jsonify({
        'success': True,
        'data': notification_dict,
        'message': 'Notification retrieved successfully'
    }), 200

# Mark notification as read
@notifications_bp.route('/<notification_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_user, notification_id):
    # Check if notification exists
    notification = Notification.query.filter_by(id=notification_id).first()
    
    if not notification:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Notification not found'
        }), 404
    
    # Check if user has access to this notification
    user_notification = UserNotification.query.filter_by(
        user_id=current_user.id,
        notification_id=notification_id
    ).first()
    
    if not user_notification:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have access to this notification'
        }), 403
    
    # Mark as read
    user_notification.is_read = True
    user_notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notification marked as read'
    }), 200

# Mark all notifications as read
@notifications_bp.route('/read-all', methods=['PUT'])
@token_required
def mark_all_notifications_read(current_user):
    # Get all unread notifications for user
    unread_notifications = UserNotification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).all()
    
    # Mark all as read
    now = datetime.utcnow()
    for notification in unread_notifications:
        notification.is_read = True
        notification.read_at = now
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'All notifications marked as read',
        'data': {
            'count': len(unread_notifications)
        }
    }), 200

# Create notification (admin only)
@notifications_bp.route('', methods=['POST'])
@token_required
def create_notification(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to create notifications'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['notificationType', 'title', 'message', 'userIds']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse expiry date if provided
    expiry_date = None
    if 'expiryDate' in data and data['expiryDate']:
        try:
            expiry_date = datetime.fromisoformat(data['expiryDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid expiry date format'
            }), 400
    else:
        # Default expiry is 30 days from now
        expiry_date = datetime.utcnow() + timedelta(days=30)
    
    # Create new notification
    new_notification = Notification(
        id=uuid.uuid4(),
        notification_type=data['notificationType'],
        title=data['title'],
        message=data['message'],
        related_entity_type=data.get('relatedEntityType'),
        related_entity_id=data.get('relatedEntityId'),
        is_urgent=data.get('isUrgent', False),
        expiry_date=expiry_date
    )
    
    db.session.add(new_notification)
    
    # Create user notifications
    user_ids = data['userIds']
    user_notifications = []
    
    for user_id in user_ids:
        user_notification = UserNotification(
            user_id=user_id,
            notification_id=new_notification.id
        )
        user_notifications.append(user_notification)
    
    db.session.add_all(user_notifications)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': {
            'notification': new_notification.to_dict(),
            'userCount': len(user_notifications)
        },
        'message': 'Notification created successfully'
    }), 201

# Delete notification (admin only)
@notifications_bp.route('/<notification_id>', methods=['DELETE'])
@token_required
def delete_notification(current_user, notification_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete notifications'
        }), 403
    
    notification = Notification.query.filter_by(id=notification_id).first()
    
    if not notification:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Notification not found'
        }), 404
    
    # Delete user notifications first (due to foreign key constraint)
    UserNotification.query.filter_by(notification_id=notification_id).delete()
    
    # Delete notification
    db.session.delete(notification)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Notification deleted successfully'
    }), 200
