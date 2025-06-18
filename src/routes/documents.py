from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime
import os

from src.extensions import db
from src.models.document import Document, DocumentType
from src.routes.auth import token_required

documents_bp = Blueprint('documents', __name__)

# Get all documents with pagination and filtering
@documents_bp.route('', methods=['GET'])
@token_required
def get_documents(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    document_type_id = request.args.get('type', None, type=int)
    organization_id = request.args.get('organization', None)
    agreement_id = request.args.get('agreement', None)
    election_id = request.args.get('election', None)
    workshop_id = request.args.get('workshop', None)
    is_public = request.args.get('isPublic', None)
    
    # Build query
    query = Document.query
    
    # Apply filters
    if search:
        query = query.filter(
            (Document.document_name.ilike(f'%{search}%')) |
            (Document.document_number.ilike(f'%{search}%')) |
            (Document.description.ilike(f'%{search}%'))
        )
    
    if document_type_id:
        query = query.filter(Document.document_type_id == document_type_id)
    
    if organization_id:
        query = query.filter(Document.organization_id == organization_id)
    
    if agreement_id:
        query = query.filter(Document.agreement_id == agreement_id)
    
    if election_id:
        query = query.filter(Document.election_id == election_id)
    
    if workshop_id:
        query = query.filter(Document.workshop_id == workshop_id)
    
    if is_public is not None:
        is_public_bool = is_public.lower() == 'true'
        query = query.filter(Document.is_public == is_public_bool)
    
    # Paginate results
    paginated_documents = query.order_by(Document.upload_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [document.to_dict() for document in paginated_documents.items],
            'total': paginated_documents.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_documents.pages
        },
        'message': 'Documents retrieved successfully'
    }), 200

# Get document by ID
@documents_bp.route('/<document_id>', methods=['GET'])
@token_required
def get_document(current_user, document_id):
    document = Document.query.filter_by(id=document_id).first()
    
    if not document:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Document not found'
        }), 404
    
    # Check if document is public or user has access
    if not document.is_public and not current_user.role:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to access this document'
        }), 403
    
    return jsonify({
        'success': True,
        'data': document.to_dict(),
        'message': 'Document retrieved successfully'
    }), 200

# Create document
@documents_bp.route('', methods=['POST'])
@token_required
def create_document(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['documentNumber', 'documentName', 'filePath', 'uploadDate']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if document number already exists
    if Document.query.filter_by(document_number=data['documentNumber']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Document number already exists'
        }), 409
    
    # Parse upload date
    try:
        upload_date = datetime.fromisoformat(data['uploadDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid upload date format'
        }), 400
    
    # Get file size and type if available
    file_size = None
    file_type = None
    file_path = data['filePath']
    
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        _, file_extension = os.path.splitext(file_path)
        file_type = file_extension.lstrip('.')
    
    # Create new document
    new_document = Document(
        id=uuid.uuid4(),
        document_number=data['documentNumber'],
        document_name=data['documentName'],
        document_type_id=data.get('documentTypeId'),
        organization_id=data.get('organizationId'),
        agreement_id=data.get('agreementId'),
        election_id=data.get('electionId'),
        workshop_id=data.get('workshopId'),
        file_path=file_path,
        file_size=data.get('fileSize', file_size),
        file_type=data.get('fileType', file_type),
        upload_date=upload_date.date(),
        uploaded_by=current_user.id,
        is_public=data.get('isPublic', False),
        description=data.get('description')
    )
    
    db.session.add(new_document)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_document.to_dict(),
        'message': 'Document created successfully'
    }), 201

# Update document
@documents_bp.route('/<document_id>', methods=['PUT'])
@token_required
def update_document(current_user, document_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    document = Document.query.filter_by(id=document_id).first()
    
    if not document:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Document not found'
        }), 404
    
    # Check if document number already exists for another document
    if 'documentNumber' in data and data['documentNumber'] != document.document_number:
        existing_document = Document.query.filter_by(document_number=data['documentNumber']).first()
        if existing_document and str(existing_document.id) != document_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Document number already exists'
            }), 409
    
    # Update fields
    if 'documentNumber' in data:
        document.document_number = data['documentNumber']
    if 'documentName' in data:
        document.document_name = data['documentName']
    if 'documentTypeId' in data:
        document.document_type_id = data['documentTypeId']
    if 'organizationId' in data:
        document.organization_id = data['organizationId']
    if 'agreementId' in data:
        document.agreement_id = data['agreementId']
    if 'electionId' in data:
        document.election_id = data['electionId']
    if 'workshopId' in data:
        document.workshop_id = data['workshopId']
    if 'filePath' in data:
        document.file_path = data['filePath']
        
        # Update file size and type if path changed
        if os.path.exists(data['filePath']):
            document.file_size = os.path.getsize(data['filePath'])
            _, file_extension = os.path.splitext(data['filePath'])
            document.file_type = file_extension.lstrip('.')
    
    if 'fileSize' in data:
        document.file_size = data['fileSize']
    if 'fileType' in data:
        document.file_type = data['fileType']
    if 'isPublic' in data:
        document.is_public = data['isPublic']
    if 'description' in data:
        document.description = data['description']
    
    # Parse upload date if provided
    if 'uploadDate' in data:
        try:
            upload_date = datetime.fromisoformat(data['uploadDate'].replace('Z', '+00:00'))
            document.upload_date = upload_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid upload date format'
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': document.to_dict(),
        'message': 'Document updated successfully'
    }), 200

# Delete document
@documents_bp.route('/<document_id>', methods=['DELETE'])
@token_required
def delete_document(current_user, document_id):
    document = Document.query.filter_by(id=document_id).first()
    
    if not document:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Document not found'
        }), 404
    
    # Check if user has permission to delete
    if document.uploaded_by != current_user.id and not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete this document'
        }), 403
    
    # Delete file if it exists
    if os.path.exists(document.file_path):
        try:
            os.remove(document.file_path)
        except Exception as e:
            # Log error but continue with database deletion
            print(f"Error deleting file: {e}")
    
    db.session.delete(document)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Document deleted successfully'
    }), 200

# Get document types
@documents_bp.route('/types', methods=['GET'])
@token_required
def get_document_types(current_user):
    types = DocumentType.query.all()
    
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in types],
        'message': 'Document types retrieved successfully'
    }), 200

# Create document type
@documents_bp.route('/types', methods=['POST'])
@token_required
def create_document_type(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to create document types'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    if 'typeName' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Type name is required'
        }), 400
    
    # Check if type name already exists
    if DocumentType.query.filter_by(type_name=data['typeName']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Document type name already exists'
        }), 409
    
    # Create new document type
    new_type = DocumentType(
        type_name=data['typeName'],
        description=data.get('description')
    )
    
    db.session.add(new_type)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_type.to_dict(),
        'message': 'Document type created successfully'
    }), 201

# Update document type
@documents_bp.route('/types/<type_id>', methods=['PUT'])
@token_required
def update_document_type(current_user, type_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to update document types'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    doc_type = DocumentType.query.filter_by(id=type_id).first()
    
    if not doc_type:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Document type not found'
        }), 404
    
    # Check if type name already exists for another type
    if 'typeName' in data and data['typeName'] != doc_type.type_name:
        existing_type = DocumentType.query.filter_by(type_name=data['typeName']).first()
        if existing_type and existing_type.id != int(type_id):
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Document type name already exists'
            }), 409
    
    # Update fields
    if 'typeName' in data:
        doc_type.type_name = data['typeName']
    if 'description' in data:
        doc_type.description = data['description']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': doc_type.to_dict(),
        'message': 'Document type updated successfully'
    }), 200

# Delete document type
@documents_bp.route('/types/<type_id>', methods=['DELETE'])
@token_required
def delete_document_type(current_user, type_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete document types'
        }), 403
    
    doc_type = DocumentType.query.filter_by(id=type_id).first()
    
    if not doc_type:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Document type not found'
        }), 404
    
    # Check if type is in use
    if Document.query.filter_by(document_type_id=type_id).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Document type is in use and cannot be deleted'
        }), 409
    
    db.session.delete(doc_type)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Document type deleted successfully'
    }), 200
