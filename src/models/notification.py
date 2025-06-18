#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_entity_type = db.Column(db.String(50))  # 'organization', 'agreement', 'compliance', 'ballot', 'training'
    related_entity_id = db.Column(UUID(as_uuid=True))
    is_read = db.Column(db.Boolean, default=False)
    is_urgent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime)
    
    # Relationships
    user_notifications = db.relationship('UserNotification', backref='notification', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'notificationType': self.notification_type,
            'title': self.title,
            'message': self.message,
            'relatedEntityType': self.related_entity_type,
            'relatedEntityId': str(self.related_entity_id) if self.related_entity_id else None,
            'isRead': self.is_read,
            'isUrgent': self.is_urgent,
            'createdAt': self.created_at.isoformat(),
            'expiryDate': self.expiry_date.isoformat() if self.expiry_date else None
        }

class UserNotification(db.Model):
    __tablename__ = 'user_notifications'
    
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), primary_key=True)
    notification_id = db.Column(UUID(as_uuid=True), db.ForeignKey('notifications.id'), primary_key=True)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'userId': str(self.user_id),
            'notificationId': str(self.notification_id),
            'isRead': self.is_read,
            'readAt': self.read_at.isoformat() if self.read_at else None,
            'createdAt': self.created_at.isoformat()
        }
