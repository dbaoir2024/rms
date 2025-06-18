#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class Agreement(db.Model):
    __tablename__ = 'agreements'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_number = db.Column(db.String(50), unique=True, nullable=False)
    agreement_name = db.Column(db.String(255), nullable=False)
    agreement_type_id = db.Column(db.Integer, db.ForeignKey('agreement_types.id'))
    primary_organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'))
    counterparty_name = db.Column(db.String(255))
    counterparty_organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'))
    effective_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # 'active', 'expired', 'terminated', 'in_negotiation'
    document_path = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agreement_type = db.relationship('AgreementType', backref='agreements')
    amendments = db.relationship('AgreementAmendment', backref='agreement', lazy='dynamic')
    disputes = db.relationship('Dispute', backref='agreement', lazy='dynamic')
    documents = db.relationship('Document', backref='agreement', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'agreementNumber': self.agreement_number,
            'agreementName': self.agreement_name,
            'agreementType': self.agreement_type.to_dict() if self.agreement_type else None,
            'primaryOrganization': self.primary_organization.to_dict() if self.primary_organization else None,
            'counterpartyName': self.counterparty_name,
            'counterpartyOrganization': self.counterparty_organization.to_dict() if self.counterparty_organization else None,
            'effectiveDate': self.effective_date.isoformat() if self.effective_date else None,
            'expiryDate': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'documentPath': self.document_path,
            'notes': self.notes,
            'amendments': [a.to_dict() for a in self.amendments],
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

class AgreementType(db.Model):
    __tablename__ = 'agreement_types'
    
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

class AgreementAmendment(db.Model):
    __tablename__ = 'agreement_amendments'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('agreements.id'), nullable=False)
    amendment_number = db.Column(db.String(20), nullable=False)
    amendment_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    document_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'amendmentNumber': self.amendment_number,
            'amendmentDate': self.amendment_date.isoformat() if self.amendment_date else None,
            'description': self.description,
            'documentPath': self.document_path
        }

class DisputeType(db.Model):
    __tablename__ = 'dispute_types'
    
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

class Dispute(db.Model):
    __tablename__ = 'disputes'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispute_number = db.Column(db.String(50), unique=True, nullable=False)
    dispute_type_id = db.Column(db.Integer, db.ForeignKey('dispute_types.id'))
    agreement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('agreements.id'))
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    counterparty_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'))
    filing_date = db.Column(db.Date, nullable=False)
    resolution_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'in_progress', 'resolved', 'escalated'
    resolution_summary = db.Column(db.Text)
    document_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dispute_type = db.relationship('DisputeType', backref='disputes')
    organization = db.relationship('Organization', foreign_keys=[organization_id], backref='disputes_filed')
    counterparty = db.relationship('Organization', foreign_keys=[counterparty_id], backref='disputes_received')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'disputeNumber': self.dispute_number,
            'disputeType': self.dispute_type.to_dict() if self.dispute_type else None,
            'agreement': self.agreement.to_dict() if self.agreement else None,
            'organization': self.organization.to_dict() if self.organization else None,
            'counterparty': self.counterparty.to_dict() if self.counterparty else None,
            'filingDate': self.filing_date.isoformat() if self.filing_date else None,
            'resolutionDate': self.resolution_date.isoformat() if self.resolution_date else None,
            'status': self.status,
            'resolutionSummary': self.resolution_summary,
            'documentPath': self.document_path,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }
