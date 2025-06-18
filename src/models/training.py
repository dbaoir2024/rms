#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class TrainingType(db.Model):
    __tablename__ = 'training_types'
    
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'typeName': self.type_name,
            'description': self.description
        }

class TrainingWorkshop(db.Model):
    __tablename__ = 'training_workshops'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workshop_name = db.Column(db.String(255), nullable=False)
    training_type_id = db.Column(db.Integer, db.ForeignKey('training_types.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(255))
    facilitator = db.Column(db.String(100))
    max_participants = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False)  # 'scheduled', 'in_progress', 'completed', 'cancelled'
    description = db.Column(db.Text)
    materials_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    training_type = db.relationship('TrainingType', backref='workshops')
    participants = db.relationship('WorkshopParticipant', backref='workshop', lazy='dynamic')
    documents = db.relationship('Document', backref='workshop', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'workshopName': self.workshop_name,
            'trainingType': self.training_type.to_dict() if self.training_type else None,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'facilitator': self.facilitator,
            'maxParticipants': self.max_participants,
            'status': self.status,
            'description': self.description,
            'materialsPath': self.materials_path,
            'participants': [p.to_dict() for p in self.participants],
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

class WorkshopParticipant(db.Model):
    __tablename__ = 'workshop_participants'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workshop_id = db.Column(UUID(as_uuid=True), db.ForeignKey('training_workshops.id'), nullable=False)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'))
    official_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organization_officials.id'))
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    attendance_status = db.Column(db.String(20), default='registered')  # 'registered', 'attended', 'absent', 'partial'
    certificate_issued = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = db.relationship('Organization', backref='workshop_participants')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'organization': self.organization.to_dict() if self.organization else None,
            'official': self.official.to_dict() if self.official else None,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'attendanceStatus': self.attendance_status,
            'certificateIssued': self.certificate_issued,
            'notes': self.notes
        }
