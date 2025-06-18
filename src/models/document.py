#from src.main import db
from src.extensions import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID

class DocumentType(db.Model):
    __tablename__ = 'document_types'
    
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

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_number = db.Column(db.String(50), unique=True, nullable=False)
    document_name = db.Column(db.String(255), nullable=False)
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'))
    organization_id = db.Column(UUID(as_uuid=True), db.ForeignKey('organizations.id'))
    agreement_id = db.Column(UUID(as_uuid=True), db.ForeignKey('agreements.id'))
    election_id = db.Column(UUID(as_uuid=True), db.ForeignKey('ballot_elections.id'))
    workshop_id = db.Column(UUID(as_uuid=True), db.ForeignKey('training_workshops.id'))
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(50))
    upload_date = db.Column(db.Date, nullable=False)
    uploaded_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    is_public = db.Column(db.Boolean, default=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document_type = db.relationship('DocumentType', backref='documents')
    uploader = db.relationship('User', backref='uploaded_documents')
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'documentNumber': self.document_number,
            'documentName': self.document_name,
            'documentType': self.document_type.to_dict() if self.document_type else None,
            'organization': self.organization.to_dict() if self.organization else None,
            'agreement': self.agreement.to_dict() if self.agreement else None,
            'election': self.election.to_dict() if self.election else None,
            'workshop': self.workshop.to_dict() if self.workshop else None,
            'filePath': self.file_path,
            'fileSize': self.file_size,
            'fileType': self.file_type,
            'uploadDate': self.upload_date.isoformat() if self.upload_date else None,
            'uploadedBy': self.uploader.to_dict() if self.uploader else None,
            'isPublic': self.is_public,
            'description': self.description,
            'createdAt': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat()
        }
