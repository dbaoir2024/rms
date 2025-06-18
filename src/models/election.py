#from src.main import db
from src.extensions import db
import datetime

class ExecutivePosition(db.Model):
    __tablename__ = 'executive_positions'
    
    id = db.Column(db.Integer, primary_key=True)
    position_name = db.Column(db.String(100), nullable=False)
    position_code = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'position_name': self.position_name,
            'position_code': self.position_code,
            'description': self.description,
            'is_active': self.is_active
        }

class UnionElection(db.Model):
    __tablename__ = 'union_elections'
    
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    election_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    voter_turnout = db.Column(db.Numeric(5, 2))
    total_eligible_voters = db.Column(db.Integer)
    actual_voters = db.Column(db.Integer)
    quorum_met = db.Column(db.Boolean)
    supervised_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    organization = db.relationship('Organization', backref='elections')
    supervisor = db.relationship('User', backref='supervised_elections')
    nominees = db.relationship('ElectionNominee', backref='election', cascade='all, delete-orphan')
    
    def to_dict(self, include_nominees=False):
        result = {
            'id': self.id,
            'organization_id': self.organization_id,
            'unionName': self.organization.organization_name if self.organization else None,
            'registrationNumber': self.organization.registration_number if self.organization else None,
            'election_date': self.election_date.isoformat() if self.election_date else None,
            'status': self.status,
            'voter_turnout': float(self.voter_turnout) if self.voter_turnout else None,
            'total_eligible_voters': self.total_eligible_voters,
            'actual_voters': self.actual_voters,
            'quorum_met': self.quorum_met,
            'supervised_by': self.supervised_by,
            'supervisor_name': self.supervisor.full_name if self.supervisor else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'positionsCount': len(set([n.position_id for n in self.nominees])) if self.nominees else 0
        }
        
        if include_nominees:
            result['nominees'] = [nominee.to_dict() for nominee in self.nominees]
        
        return result

class ElectionNominee(db.Model):
    __tablename__ = 'election_nominees'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('union_elections.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('executive_positions.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('organization_members.id'), nullable=False)
    nomination_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    verification_status = db.Column(db.String(30), default='pending')
    is_valid_member = db.Column(db.Boolean)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    position = db.relationship('ExecutivePosition')
    member = db.relationship('OrganizationMember')
    verifications = db.relationship('NomineeVerification', backref='nominee', cascade='all, delete-orphan')
    
    def to_dict(self, include_verifications=False):
        result = {
            'id': self.id,
            'election_id': self.election_id,
            'position_id': self.position_id,
            'position_name': self.position.position_name if self.position else None,
            'member_id': self.member_id,
            'member_name': f"{self.member.first_name} {self.member.last_name}" if self.member else None,
            'nomination_date': self.nomination_date.isoformat() if self.nomination_date else None,
            'verification_status': self.verification_status,
            'is_valid_member': self.is_valid_member,
            'rejection_reason': self.rejection_reason
        }
        
        if include_verifications:
            result['verifications'] = [v.to_dict() for v in self.verifications]
        
        return result

class NomineeVerification(db.Model):
    __tablename__ = 'nominee_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    nominee_id = db.Column(db.Integer, db.ForeignKey('election_nominees.id'), nullable=False)
    verification_step = db.Column(db.String(30), nullable=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verification_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    verifier = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nominee_id': self.nominee_id,
            'verification_step': self.verification_step,
            'verified_by': self.verified_by,
            'verifier_name': self.verifier.full_name if self.verifier else None,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'status': self.status,
            'comments': self.comments
        }

class ElectionResult(db.Model):
    __tablename__ = 'election_results'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('union_elections.id'), nullable=False)
    position_id = db.Column(db.Integer, db.ForeignKey('executive_positions.id'), nullable=False)
    nominee_id = db.Column(db.Integer, db.ForeignKey('election_nominees.id'), nullable=False)
    votes_received = db.Column(db.Integer, default=0)
    is_elected = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    election = db.relationship('UnionElection')
    position = db.relationship('ExecutivePosition')
    nominee = db.relationship('ElectionNominee')
    
    def to_dict(self):
        return {
            'id': self.id,
            'election_id': self.election_id,
            'position_id': self.position_id,
            'position_name': self.position.position_name if self.position else None,
            'nominee_id': self.nominee_id,
            'nominee_name': f"{self.nominee.member.first_name} {self.nominee.member.last_name}" if self.nominee and self.nominee.member else None,
            'votes_received': self.votes_received,
            'is_elected': self.is_elected
        }

class ElectionObserver(db.Model):
    __tablename__ = 'election_observers'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('union_elections.id'), nullable=False)
    observer_name = db.Column(db.String(255), nullable=False)
    organization = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    election = db.relationship('UnionElection')
    
    def to_dict(self):
        return {
            'id': self.id,
            'election_id': self.election_id,
            'observer_name': self.observer_name,
            'organization': self.organization,
            'role': self.role,
            'contact_info': self.contact_info
        }

class ElectionDocument(db.Model):
    __tablename__ = 'election_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('union_elections.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    election = db.relationship('UnionElection')
    uploader = db.relationship('User')
    
    def to_dict(self):
        return {
            'id': self.id,
            'election_id': self.election_id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'uploaded_by': self.uploaded_by,
            'uploader_name': self.uploader.full_name if self.uploader else None,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'notes': self.notes
        }
