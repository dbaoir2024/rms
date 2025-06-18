#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class BallotElection(db.Model):
    __tablename__ = 'ballot_elections'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_number = db.Column(db.String(50), unique=True, nullable=False)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    election_date = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'scheduled', 'in_progress', 'completed', 'cancelled'
    supervisor_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    location = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supervisor = db.relationship('User', backref='supervised_elections')
    positions = db.relationship('BallotPosition', backref='election', lazy='dynamic')
    documents = db.relationship('Document', backref='election', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'electionNumber': self.election_number,
            'organization': self.organization.to_dict() if self.organization else None,
            'electionDate': self.election_date.isoformat() if self.election_date else None,
            'purpose': self.purpose,
            'status': self.status,
            'supervisor': self.supervisor.to_dict() if self.supervisor else None,
            'location': self.location,
            'notes': self.notes,
            'positions': [p.to_dict() for p in self.positions],
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

class BallotPosition(db.Model):
    __tablename__ = 'ballot_positions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_elections.id'), nullable=False)
    position_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidates = db.relationship('BallotCandidate', backref='position', lazy='dynamic')
    results = db.relationship('BallotResult', backref='position', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'positionName': self.position_name,
            'description': self.description,
            'candidates': [c.to_dict() for c in self.candidates],
            'results': [r.to_dict() for r in self.results]
        }

class BallotCandidate(db.Model):
    __tablename__ = 'ballot_candidates'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    position_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_positions.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    results = db.relationship('BallotResult', backref='candidate', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'firstName': self.first_name,
            'lastName': self.last_name,
            'bio': self.bio
        }

class BallotResult(db.Model):
    __tablename__ = 'ballot_results'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    election_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_elections.id'), nullable=False)
    position_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_positions.id'), nullable=False)
    candidate_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_candidates.id'), nullable=False)
    votes_received = db.Column(db.Integer, nullable=False, default=0)
    is_elected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    election = db.relationship('BallotElection', backref='results')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'votesReceived': self.votes_received,
            'isElected': self.is_elected
        }
