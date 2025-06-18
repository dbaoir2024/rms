#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class ComplianceRequirement(db.Model):
    __tablename__ = 'compliance_requirements'
    
    id = db.Column(db.Integer, primary_key=True)
    requirement_name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    legal_reference = db.Column(db.String(100))
    frequency = db.Column(db.String(50))  # 'annual', 'quarterly', 'monthly', 'one-time'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    compliance_records = db.relationship('ComplianceRecord', backref='requirement', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'requirementName': self.requirement_name,
            'description': self.description,
            'legalReference': self.legal_reference,
            'frequency': self.frequency
        }

class ComplianceRecord(db.Model):
    __tablename__ = 'compliance_records'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    requirement_id = db.Column(db.Integer, db.ForeignKey('compliance_requirements.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    submission_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # 'pending', 'submitted', 'approved', 'rejected', 'overdue'
    approved_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    document_path = db.Column(db.String(255))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    approver = db.relationship('User', backref='approved_compliance_records')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'organization': self.organization.to_dict() if self.organization else None,
            'requirement': self.requirement.to_dict() if self.requirement else None,
            'dueDate': self.due_date.isoformat() if self.due_date else None,
            'submissionDate': self.submission_date.isoformat() if self.submission_date else None,
            'status': self.status,
            'approvedBy': self.approver.to_dict() if self.approver else None,
            'documentPath': self.document_path,
            'notes': self.notes
        }

class Inspection(db.Model):
    __tablename__ = 'inspections'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False)
    inspector_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    inspection_type = db.Column(db.String(50), nullable=False)
    findings = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False)  # 'scheduled', 'completed', 'cancelled', 'follow-up-required'
    document_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    inspector = db.relationship('User', backref='conducted_inspections')
    non_compliance_issues = db.relationship('NonComplianceIssue', backref='inspection', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'organization': self.organization.to_dict() if self.organization else None,
            'inspectionDate': self.inspection_date.isoformat() if self.inspection_date else None,
            'inspector': self.inspector.to_dict() if self.inspector else None,
            'inspectionType': self.inspection_type,
            'findings': self.findings,
            'recommendations': self.recommendations,
            'status': self.status,
            'documentPath': self.document_path,
            'nonComplianceIssues': [i.to_dict() for i in self.non_compliance_issues],
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }

class NonComplianceIssue(db.Model):
    __tablename__ = 'non_compliance_issues'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'), nullable=False)
    inspection_id = db.Column(UUID(as_uuid=True), db.ForeignKey('inspections.id'))
    issue_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'minor', 'major', 'critical'
    resolution_deadline = db.Column(db.Date)
    resolution_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False)  # 'open', 'in_progress', 'resolved', 'escalated'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'issueDate': self.issue_date.isoformat() if self.issue_date else None,
            'description': self.description,
            'severity': self.severity,
            'resolutionDeadline': self.resolution_deadline.isoformat() if self.resolution_deadline else None,
            'resolutionDate': self.resolution_date.isoformat() if self.resolution_date else None,
            'status': self.status
        }
