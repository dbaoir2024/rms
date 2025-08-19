from src.extensions import db
from datetime import datetime

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    setting_key = db.Column(db.String(255), primary_key=True, unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemSetting {self.setting_key}: {self.setting_value}>'

    def to_dict(self):
        return {
            'settingKey': self.setting_key,
            'settingValue': self.setting_value,
            'description': self.description,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }

