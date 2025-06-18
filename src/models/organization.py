#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class Organization(db.Model):
    __tablename__ = 'organizations'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    organization_name = db.Column(db.String(255), nullable=False)
    organization_type_id = db.Column(db.Integer, db.ForeignKey('organization_types.id'))
    registration_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # 'active', 'suspended', 'deregistered'
    address = db.Column(db.Text)
    district_id = db.Column(db.Integer, db.ForeignKey('districts.id'))
    contact_person = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    website = db.Column(db.String(255))
    membership_count = db.Column(db.Integer)
    is_compliant = db.Column(db.Boolean, default=True)
    last_compliance_check = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization_type = db.relationship('OrganizationType', backref='organizations')
    district = db.relationship('District', backref='organizations')
    officials = db.relationship('OrganizationOfficial', backref='organization', lazy='dynamic')
    constitutions = db.relationship('OrganizationConstitution', backref='organization', lazy='dynamic')
    agreements_primary = db.relationship('Agreement', foreign_keys='Agreement.primary_organization_id', backref='primary_organization', lazy='dynamic')
    agreements_counterparty = db.relationship('Agreement', foreign_keys='Agreement.counterparty_organization_id', backref='counterparty_organization', lazy='dynamic')
    ballot_elections = db.relationship('BallotElection', backref='organization', lazy='dynamic')
    compliance_records = db.relationship('ComplianceRecord', backref='organization', lazy='dynamic')
    inspections = db.relationship('Inspection', backref='organization', lazy='dynamic')
    non_compliance_issues = db.relationship('NonComplianceIssue', backref='organization', lazy='dynamic')
    documents = db.relationship('Document', backref='organization', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'registrationNumber': self.registration_number,
            'organizationName': self.organization_name,
            'organizationType': self.organization_type.to_dict() if self.organization_type else None,
            'registrationDate': self.registration_date.isoformat() if self.registration_date else None,
            'expiryDate': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'address': self.address,
            'district': self.district.to_dict() if self.district else None,
            'contactPerson': self.contact_person,
            'contactEmail': self.contact_email,
            'contactPhone': self.contact_phone,
            'website': self.website,
            'membershipCount': self.membership_count,
            'isCompliant': self.is_compliant,
            'lastComplianceCheck': self.last_compliance_check.isoformat() if self.last_compliance_check else None,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

class OrganizationType(db.Model):
    __tablename__ = 'organization_types'
    
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

class OrganizationOfficial(db.Model):
    __tablename__ = 'organization_officials'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workshop_participants = db.relationship('WorkshopParticipant', backref='official', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'position': self.position,
            'firstName': self.first_name,
            'lastName': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'isCurrent': self.is_current
        }

class OrganizationConstitution(db.Model):
    __tablename__ = 'organization_constitutions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    approval_date = db.Column(db.Date)
    approved_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    document_path = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False)  # 'draft', 'pending', 'approved', 'rejected'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approver = db.relationship('User', backref='approved_constitutions')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'versionNumber': self.version_number,
            'effectiveDate': self.effective_date.isoformat() if self.effective_date else None,
            'approvalDate': self.approval_date.isoformat() if self.approval_date else None,
            'approvedBy': self.approver.to_dict() if self.approver else None,
            'documentPath': self.document_path,
            'status': self.status,
            'notes': self.notes
        }
