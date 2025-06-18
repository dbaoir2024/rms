from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.agreement import Agreement, AgreementType, AgreementAmendment, Dispute, DisputeType
from src.routes.auth import token_required

agreements_bp = Blueprint('agreements', __name__)

# Get all agreements with pagination and filtering
@agreements_bp.route('', methods=['GET'])
@token_required
def get_agreements(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    type_id = request.args.get('type', None, type=int)
    organization_id = request.args.get('organization', None)
    expiring_before = request.args.get('expiringBefore', None)
    expiring_after = request.args.get('expiringAfter', None)
    
    # Build query
    query = Agreement.query
    
    # Apply filters
    if search:
        query = query.filter(
            (Agreement.agreement_name.ilike(f'%{search}%')) |
            (Agreement.agreement_number.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(Agreement.status == status)
    
    if type_id:
        query = query.filter(Agreement.agreement_type_id == type_id)
    
    if organization_id:
        query = query.filter(
            (Agreement.primary_organization_id == organization_id) |
            (Agreement.counterparty_organization_id == organization_id)
        )
    
    if expiring_before:
        try:
            expiring_before_date = datetime.fromisoformat(expiring_before.replace('Z', '+00:00')).date()
            query = query.filter(Agreement.expiry_date <= expiring_before_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid expiring before date format'
            }), 400
    
    if expiring_after:
        try:
            expiring_after_date = datetime.fromisoformat(expiring_after.replace('Z', '+00:00')).date()
            query = query.filter(Agreement.expiry_date >= expiring_after_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid expiring after date format'
            }), 400
    
    # Paginate results
    paginated_agreements = query.order_by(Agreement.agreement_name).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [agreement.to_dict() for agreement in paginated_agreements.items],
            'total': paginated_agreements.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_agreements.pages
        },
        'message': 'Agreements retrieved successfully'
    }), 200

# Get agreement by ID
@agreements_bp.route('/<agreement_id>', methods=['GET'])
@token_required
def get_agreement(current_user, agreement_id):
    try:
        agreement = Agreement.query.filter_by(id=agreement_id).first()
        
        if not agreement:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': 'Agreement not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': agreement.to_dict(),
            'message': 'Agreement retrieved successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Create new agreement
@agreements_bp.route('', methods=['POST'])
@token_required
def create_agreement(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['agreementNumber', 'agreementName', 'agreementTypeId', 'primaryOrganizationId', 'effectiveDate', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if agreement number already exists
    if Agreement.query.filter_by(agreement_number=data['agreementNumber']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Agreement number already exists'
        }), 409
    
    # Parse dates
    try:
        effective_date = datetime.fromisoformat(data['effectiveDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid effective date format'
        }), 400
    
    expiry_date = None
    if 'expiryDate' in data and data['expiryDate']:
        try:
            expiry_date = datetime.fromisoformat(data['expiryDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid expiry date format'
            }), 400
    
    # Create new agreement
    new_agreement = Agreement(
        id=uuid.uuid4(),
        agreement_number=data['agreementNumber'],
        agreement_name=data['agreementName'],
        agreement_type_id=data['agreementTypeId'],
        primary_organization_id=data['primaryOrganizationId'],
        counterparty_name=data.get('counterpartyName'),
        counterparty_organization_id=data.get('counterpartyOrganizationId'),
        effective_date=effective_date.date(),
        expiry_date=expiry_date.date() if expiry_date else None,
        status=data['status'],
        document_path=data.get('documentPath'),
        notes=data.get('notes')
    )
    
    db.session.add(new_agreement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_agreement.to_dict(),
        'message': 'Agreement created successfully'
    }), 201

# Update agreement
@agreements_bp.route('/<agreement_id>', methods=['PUT'])
@token_required
def update_agreement(current_user, agreement_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    agreement = Agreement.query.filter_by(id=agreement_id).first()
    
    if not agreement:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Agreement not found'
        }), 404
    
    # Check if agreement number already exists for another agreement
    if 'agreementNumber' in data and data['agreementNumber'] != agreement.agreement_number:
        existing_agreement = Agreement.query.filter_by(agreement_number=data['agreementNumber']).first()
        if existing_agreement and str(existing_agreement.id) != agreement_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Agreement number already exists'
            }), 409
    
    # Update fields
    if 'agreementNumber' in data:
        agreement.agreement_number = data['agreementNumber']
    if 'agreementName' in data:
        agreement.agreement_name = data['agreementName']
    if 'agreementTypeId' in data:
        agreement.agreement_type_id = data['agreementTypeId']
    if 'primaryOrganizationId' in data:
        agreement.primary_organization_id = data['primaryOrganizationId']
    if 'counterpartyName' in data:
        agreement.counterparty_name = data['counterpartyName']
    if 'counterpartyOrganizationId' in data:
        agreement.counterparty_organization_id = data['counterpartyOrganizationId']
    if 'status' in data:
        agreement.status = data['status']
    if 'documentPath' in data:
        agreement.document_path = data['documentPath']
    if 'notes' in data:
        agreement.notes = data['notes']
    
    # Parse dates
    if 'effectiveDate' in data:
        try:
            effective_date = datetime.fromisoformat(data['effectiveDate'].replace('Z', '+00:00'))
            agreement.effective_date = effective_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid effective date format'
            }), 400
    
    if 'expiryDate' in data:
        if data['expiryDate']:
            try:
                expiry_date = datetime.fromisoformat(data['expiryDate'].replace('Z', '+00:00'))
                agreement.expiry_date = expiry_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid expiry date format'
                }), 400
        else:
            agreement.expiry_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': agreement.to_dict(),
        'message': 'Agreement updated successfully'
    }), 200

# Delete agreement
@agreements_bp.route('/<agreement_id>', methods=['DELETE'])
@token_required
def delete_agreement(current_user, agreement_id):
    agreement = Agreement.query.filter_by(id=agreement_id).first()
    
    if not agreement:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Agreement not found'
        }), 404
    
    # Check if user has permission to delete
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete agreements'
        }), 403
    
    # In a real application, you might want to check for dependencies
    # before deleting, or implement soft delete
    
    db.session.delete(agreement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Agreement deleted successfully'
    }), 200

# Get agreement types
@agreements_bp.route('/types', methods=['GET'])
@token_required
def get_agreement_types(current_user):
    types = AgreementType.query.all()
    
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in types],
        'message': 'Agreement types retrieved successfully'
    }), 200

# Get agreement amendments
@agreements_bp.route('/<agreement_id>/amendments', methods=['GET'])
@token_required
def get_agreement_amendments(current_user, agreement_id):
    agreement = Agreement.query.filter_by(id=agreement_id).first()
    
    if not agreement:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Agreement not found'
        }), 404
    
    amendments = AgreementAmendment.query.filter_by(agreement_id=agreement_id).order_by(AgreementAmendment.amendment_date.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [amendment.to_dict() for amendment in amendments],
        'message': 'Agreement amendments retrieved successfully'
    }), 200

# Create agreement amendment
@agreements_bp.route('/<agreement_id>/amendments', methods=['POST'])
@token_required
def create_agreement_amendment(current_user, agreement_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    agreement = Agreement.query.filter_by(id=agreement_id).first()
    
    if not agreement:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Agreement not found'
        }), 404
    
    # Check required fields
    required_fields = ['amendmentNumber', 'amendmentDate']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if amendment number already exists
    existing_amendment = AgreementAmendment.query.filter_by(
        agreement_id=agreement_id,
        amendment_number=data['amendmentNumber']
    ).first()
    
    if existing_amendment:
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Amendment number already exists for this agreement'
        }), 409
    
    # Parse amendment date
    try:
        amendment_date = datetime.fromisoformat(data['amendmentDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid amendment date format'
        }), 400
    
    # Create new amendment
    new_amendment = AgreementAmendment(
        id=uuid.uuid4(),
        agreement_id=agreement_id,
        amendment_number=data['amendmentNumber'],
        amendment_date=amendment_date.date(),
        description=data.get('description'),
        document_path=data.get('documentPath')
    )
    
    db.session.add(new_amendment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_amendment.to_dict(),
        'message': 'Agreement amendment created successfully'
    }), 201

# Update agreement amendment
@agreements_bp.route('/amendments/<amendment_id>', methods=['PUT'])
@token_required
def update_agreement_amendment(current_user, amendment_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    amendment = AgreementAmendment.query.filter_by(id=amendment_id).first()
    
    if not amendment:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Amendment not found'
        }), 404
    
    # Check if amendment number already exists for another amendment
    if 'amendmentNumber' in data and data['amendmentNumber'] != amendment.amendment_number:
        existing_amendment = AgreementAmendment.query.filter_by(
            agreement_id=amendment.agreement_id,
            amendment_number=data['amendmentNumber']
        ).first()
        
        if existing_amendment and str(existing_amendment.id) != amendment_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Amendment number already exists for this agreement'
            }), 409
    
    # Update fields
    if 'amendmentNumber' in data:
        amendment.amendment_number = data['amendmentNumber']
    if 'description' in data:
        amendment.description = data['description']
    if 'documentPath' in data:
        amendment.document_path = data['documentPath']
    
    # Parse amendment date if provided
    if 'amendmentDate' in data:
        try:
            amendment_date = datetime.fromisoformat(data['amendmentDate'].replace('Z', '+00:00'))
            amendment.amendment_date = amendment_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid amendment date format'
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': amendment.to_dict(),
        'message': 'Agreement amendment updated successfully'
    }), 200

# Delete agreement amendment
@agreements_bp.route('/amendments/<amendment_id>', methods=['DELETE'])
@token_required
def delete_agreement_amendment(current_user, amendment_id):
    amendment = AgreementAmendment.query.filter_by(id=amendment_id).first()
    
    if not amendment:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Amendment not found'
        }), 404
    
    db.session.delete(amendment)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Agreement amendment deleted successfully'
    }), 200

# Get dispute types
@agreements_bp.route('/dispute-types', methods=['GET'])
@token_required
def get_dispute_types(current_user):
    types = DisputeType.query.all()
    
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in types],
        'message': 'Dispute types retrieved successfully'
    }), 200

# Get disputes
@agreements_bp.route('/disputes', methods=['GET'])
@token_required
def get_disputes(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    type_id = request.args.get('type', None, type=int)
    organization_id = request.args.get('organization', None)
    date_from = request.args.get('dateFrom', None)
    date_to = request.args.get('dateTo', None)
    
    # Build query
    query = Dispute.query
    
    # Apply filters
    if search:
        query = query.filter(
            (Dispute.dispute_number.ilike(f'%{search}%')) |
            (Dispute.resolution_summary.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(Dispute.status == status)
    
    if type_id:
        query = query.filter(Dispute.dispute_type_id == type_id)
    
    if organization_id:
        query = query.filter(
            (Dispute.organization_id == organization_id) |
            (Dispute.counterparty_id == organization_id)
        )
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
            query = query.filter(Dispute.filing_date >= date_from_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date from format'
            }), 400
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
            query = query.filter(Dispute.filing_date <= date_to_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date to format'
            }), 400
    
    # Paginate results
    paginated_disputes = query.order_by(Dispute.filing_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [dispute.to_dict() for dispute in paginated_disputes.items],
            'total': paginated_disputes.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_disputes.pages
        },
        'message': 'Disputes retrieved successfully'
    }), 200

# Get dispute by ID
@agreements_bp.route('/disputes/<dispute_id>', methods=['GET'])
@token_required
def get_dispute(current_user, dispute_id):
    dispute = Dispute.query.filter_by(id=dispute_id).first()
    
    if not dispute:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Dispute not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': dispute.to_dict(),
        'message': 'Dispute retrieved successfully'
    }), 200

# Create dispute
@agreements_bp.route('/disputes', methods=['POST'])
@token_required
def create_dispute(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['disputeNumber', 'organizationId', 'filingDate', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if dispute number already exists
    if Dispute.query.filter_by(dispute_number=data['disputeNumber']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Dispute number already exists'
        }), 409
    
    # Parse dates
    try:
        filing_date = datetime.fromisoformat(data['filingDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid filing date format'
        }), 400
    
    resolution_date = None
    if 'resolutionDate' in data and data['resolutionDate']:
        try:
            resolution_date = datetime.fromisoformat(data['resolutionDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid resolution date format'
            }), 400
    
    # Create new dispute
    new_dispute = Dispute(
        id=uuid.uuid4(),
        dispute_number=data['disputeNumber'],
        dispute_type_id=data.get('disputeTypeId'),
        agreement_id=data.get('agreementId'),
        organization_id=data['organizationId'],
        counterparty_id=data.get('counterpartyId'),
        filing_date=filing_date.date(),
        resolution_date=resolution_date.date() if resolution_date else None,
        status=data['status'],
        resolution_summary=data.get('resolutionSummary'),
        document_path=data.get('documentPath')
    )
    
    db.session.add(new_dispute)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_dispute.to_dict(),
        'message': 'Dispute created successfully'
    }), 201

# Update dispute
@agreements_bp.route('/disputes/<dispute_id>', methods=['PUT'])
@token_required
def update_dispute(current_user, dispute_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    dispute = Dispute.query.filter_by(id=dispute_id).first()
    
    if not dispute:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Dispute not found'
        }), 404
    
    # Check if dispute number already exists for another dispute
    if 'disputeNumber' in data and data['disputeNumber'] != dispute.dispute_number:
        existing_dispute = Dispute.query.filter_by(dispute_number=data['disputeNumber']).first()
        if existing_dispute and str(existing_dispute.id) != dispute_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Dispute number already exists'
            }), 409
    
    # Update fields
    if 'disputeNumber' in data:
        dispute.dispute_number = data['disputeNumber']
    if 'disputeTypeId' in data:
        dispute.dispute_type_id = data['disputeTypeId']
    if 'agreementId' in data:
        dispute.agreement_id = data['agreementId']
    if 'organizationId' in data:
        dispute.organization_id = data['organizationId']
    if 'counterpartyId' in data:
        dispute.counterparty_id = data['counterpartyId']
    if 'status' in data:
        dispute.status = data['status']
    if 'resolutionSummary' in data:
        dispute.resolution_summary = data['resolutionSummary']
    if 'documentPath' in data:
        dispute.document_path = data['documentPath']
    
    # Parse dates
    if 'filingDate' in data:
        try:
            filing_date = datetime.fromisoformat(data['filingDate'].replace('Z', '+00:00'))
            dispute.filing_date = filing_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid filing date format'
            }), 400
    
    if 'resolutionDate' in data:
        if data['resolutionDate']:
            try:
                resolution_date = datetime.fromisoformat(data['resolutionDate'].replace('Z', '+00:00'))
                dispute.resolution_date = resolution_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid resolution date format'
                }), 400
        else:
            dispute.resolution_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': dispute.to_dict(),
        'message': 'Dispute updated successfully'
    }), 200

# Delete dispute
@agreements_bp.route('/disputes/<dispute_id>', methods=['DELETE'])
@token_required
def delete_dispute(current_user, dispute_id):
    dispute = Dispute.query.filter_by(id=dispute_id).first()
    
    if not dispute:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Dispute not found'
        }), 404
    
    db.session.delete(dispute)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Dispute deleted successfully'
    }), 200
