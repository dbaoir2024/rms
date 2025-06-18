from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.compliance import ComplianceRequirement, ComplianceRecord, Inspection, NonComplianceIssue
from src.routes.auth import token_required

compliance_bp = Blueprint('compliance', __name__)

# Get all compliance requirements
@compliance_bp.route('/requirements', methods=['GET'])
@token_required
def get_compliance_requirements(current_user):
    requirements = ComplianceRequirement.query.all()
    
    return jsonify({
        'success': True,
        'data': [requirement.to_dict() for requirement in requirements],
        'message': 'Compliance requirements retrieved successfully'
    }), 200

# Get compliance records with pagination and filtering
@compliance_bp.route('/records', methods=['GET'])
@token_required
def get_compliance_records(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    organization_id = request.args.get('organization', None)
    requirement_id = request.args.get('requirement', None, type=int)
    status = request.args.get('status', None)
    due_before = request.args.get('dueBefore', None)
    due_after = request.args.get('dueAfter', None)
    
    # Build query
    query = ComplianceRecord.query
    
    # Apply filters
    if organization_id:
        query = query.filter(ComplianceRecord.organization_id == organization_id)
    
    if requirement_id:
        query = query.filter(ComplianceRecord.requirement_id == requirement_id)
    
    if status:
        query = query.filter(ComplianceRecord.status == status)
    
    if due_before:
        try:
            due_before_date = datetime.fromisoformat(due_before.replace('Z', '+00:00')).date()
            query = query.filter(ComplianceRecord.due_date <= due_before_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid due before date format'
            }), 400
    
    if due_after:
        try:
            due_after_date = datetime.fromisoformat(due_after.replace('Z', '+00:00')).date()
            query = query.filter(ComplianceRecord.due_date >= due_after_date)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid due after date format'
            }), 400
    
    # Paginate results
    paginated_records = query.order_by(ComplianceRecord.due_date).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [record.to_dict() for record in paginated_records.items],
            'total': paginated_records.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_records.pages
        },
        'message': 'Compliance records retrieved successfully'
    }), 200

# Get compliance record by ID
@compliance_bp.route('/records/<record_id>', methods=['GET'])
@token_required
def get_compliance_record(current_user, record_id):
    record = ComplianceRecord.query.filter_by(id=record_id).first()
    
    if not record:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Compliance record not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': record.to_dict(),
        'message': 'Compliance record retrieved successfully'
    }), 200

# Create compliance record
@compliance_bp.route('/records', methods=['POST'])
@token_required
def create_compliance_record(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['organizationId', 'requirementId', 'dueDate', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse dates
    try:
        due_date = datetime.fromisoformat(data['dueDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid due date format'
        }), 400
    
    submission_date = None
    if 'submissionDate' in data and data['submissionDate']:
        try:
            submission_date = datetime.fromisoformat(data['submissionDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid submission date format'
            }), 400
    
    # Create new compliance record
    new_record = ComplianceRecord(
        id=uuid.uuid4(),
        organization_id=data['organizationId'],
        requirement_id=data['requirementId'],
        due_date=due_date.date(),
        submission_date=submission_date.date() if submission_date else None,
        status=data['status'],
        approved_by=data.get('approvedBy'),
        document_path=data.get('documentPath'),
        notes=data.get('notes')
    )
    
    db.session.add(new_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_record.to_dict(),
        'message': 'Compliance record created successfully'
    }), 201

# Update compliance record
@compliance_bp.route('/records/<record_id>', methods=['PUT'])
@token_required
def update_compliance_record(current_user, record_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    record = ComplianceRecord.query.filter_by(id=record_id).first()
    
    if not record:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Compliance record not found'
        }), 404
    
    # Update fields
    if 'organizationId' in data:
        record.organization_id = data['organizationId']
    if 'requirementId' in data:
        record.requirement_id = data['requirementId']
    if 'status' in data:
        record.status = data['status']
    if 'approvedBy' in data:
        record.approved_by = data['approvedBy']
    if 'documentPath' in data:
        record.document_path = data['documentPath']
    if 'notes' in data:
        record.notes = data['notes']
    
    # Parse dates
    if 'dueDate' in data:
        try:
            due_date = datetime.fromisoformat(data['dueDate'].replace('Z', '+00:00'))
            record.due_date = due_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid due date format'
            }), 400
    
    if 'submissionDate' in data:
        if data['submissionDate']:
            try:
                submission_date = datetime.fromisoformat(data['submissionDate'].replace('Z', '+00:00'))
                record.submission_date = submission_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid submission date format'
                }), 400
        else:
            record.submission_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': record.to_dict(),
        'message': 'Compliance record updated successfully'
    }), 200

# Delete compliance record
@compliance_bp.route('/records/<record_id>', methods=['DELETE'])
@token_required
def delete_compliance_record(current_user, record_id):
    record = ComplianceRecord.query.filter_by(id=record_id).first()
    
    if not record:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Compliance record not found'
        }), 404
    
    db.session.delete(record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Compliance record deleted successfully'
    }), 200

# Get inspections with pagination and filtering
@compliance_bp.route('/inspections', methods=['GET'])
@token_required
def get_inspections(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    organization_id = request.args.get('organization', None)
    inspector_id = request.args.get('inspector', None)
    status = request.args.get('status', None)
    date_from = request.args.get('dateFrom', None)
    date_to = request.args.get('dateTo', None)
    
    # Build query
    query = Inspection.query
    
    # Apply filters
    if organization_id:
        query = query.filter(Inspection.organization_id == organization_id)
    
    if inspector_id:
        query = query.filter(Inspection.inspector_id == inspector_id)
    
    if status:
        query = query.filter(Inspection.status == status)
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
            query = query.filter(Inspection.inspection_date >= date_from_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date from format'
            }), 400
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
            query = query.filter(Inspection.inspection_date <= date_to_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date to format'
            }), 400
    
    # Paginate results
    paginated_inspections = query.order_by(Inspection.inspection_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [inspection.to_dict() for inspection in paginated_inspections.items],
            'total': paginated_inspections.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_inspections.pages
        },
        'message': 'Inspections retrieved successfully'
    }), 200

# Get inspection by ID
@compliance_bp.route('/inspections/<inspection_id>', methods=['GET'])
@token_required
def get_inspection(current_user, inspection_id):
    inspection = Inspection.query.filter_by(id=inspection_id).first()
    
    if not inspection:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Inspection not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': inspection.to_dict(),
        'message': 'Inspection retrieved successfully'
    }), 200

# Create inspection
@compliance_bp.route('/inspections', methods=['POST'])
@token_required
def create_inspection(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['organizationId', 'inspectionDate', 'inspectorId', 'inspectionType', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse inspection date
    try:
        inspection_date = datetime.fromisoformat(data['inspectionDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid inspection date format'
        }), 400
    
    # Create new inspection
    new_inspection = Inspection(
        id=uuid.uuid4(),
        organization_id=data['organizationId'],
        inspection_date=inspection_date.date(),
        inspector_id=data['inspectorId'],
        inspection_type=data['inspectionType'],
        findings=data.get('findings'),
        recommendations=data.get('recommendations'),
        status=data['status'],
        document_path=data.get('documentPath')
    )
    
    db.session.add(new_inspection)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_inspection.to_dict(),
        'message': 'Inspection created successfully'
    }), 201

# Update inspection
@compliance_bp.route('/inspections/<inspection_id>', methods=['PUT'])
@token_required
def update_inspection(current_user, inspection_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    inspection = Inspection.query.filter_by(id=inspection_id).first()
    
    if not inspection:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Inspection not found'
        }), 404
    
    # Update fields
    if 'organizationId' in data:
        inspection.organization_id = data['organizationId']
    if 'inspectorId' in data:
        inspection.inspector_id = data['inspectorId']
    if 'inspectionType' in data:
        inspection.inspection_type = data['inspectionType']
    if 'findings' in data:
        inspection.findings = data['findings']
    if 'recommendations' in data:
        inspection.recommendations = data['recommendations']
    if 'status' in data:
        inspection.status = data['status']
    if 'documentPath' in data:
        inspection.document_path = data['documentPath']
    
    # Parse inspection date if provided
    if 'inspectionDate' in data:
        try:
            inspection_date = datetime.fromisoformat(data['inspectionDate'].replace('Z', '+00:00'))
            inspection.inspection_date = inspection_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid inspection date format'
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': inspection.to_dict(),
        'message': 'Inspection updated successfully'
    }), 200

# Delete inspection
@compliance_bp.route('/inspections/<inspection_id>', methods=['DELETE'])
@token_required
def delete_inspection(current_user, inspection_id):
    inspection = Inspection.query.filter_by(id=inspection_id).first()
    
    if not inspection:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Inspection not found'
        }), 404
    
    db.session.delete(inspection)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Inspection deleted successfully'
    }), 200

# Get non-compliance issues with pagination and filtering
@compliance_bp.route('/issues', methods=['GET'])
@token_required
def get_non_compliance_issues(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    organization_id = request.args.get('organization', None)
    inspection_id = request.args.get('inspection', None)
    status = request.args.get('status', None)
    severity = request.args.get('severity', None)
    
    # Build query
    query = NonComplianceIssue.query
    
    # Apply filters
    if organization_id:
        query = query.filter(NonComplianceIssue.organization_id == organization_id)
    
    if inspection_id:
        query = query.filter(NonComplianceIssue.inspection_id == inspection_id)
    
    if status:
        query = query.filter(NonComplianceIssue.status == status)
    
    if severity:
        query = query.filter(NonComplianceIssue.severity == severity)
    
    # Paginate results
    paginated_issues = query.order_by(NonComplianceIssue.issue_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [issue.to_dict() for issue in paginated_issues.items],
            'total': paginated_issues.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_issues.pages
        },
        'message': 'Non-compliance issues retrieved successfully'
    }), 200

# Get non-compliance issue by ID
@compliance_bp.route('/issues/<issue_id>', methods=['GET'])
@token_required
def get_non_compliance_issue(current_user, issue_id):
    issue = NonComplianceIssue.query.filter_by(id=issue_id).first()
    
    if not issue:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Non-compliance issue not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': issue.to_dict(),
        'message': 'Non-compliance issue retrieved successfully'
    }), 200

# Create non-compliance issue
@compliance_bp.route('/issues', methods=['POST'])
@token_required
def create_non_compliance_issue(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['organizationId', 'issueDate', 'description', 'severity', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse dates
    try:
        issue_date = datetime.fromisoformat(data['issueDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid issue date format'
        }), 400
    
    resolution_deadline = None
    if 'resolutionDeadline' in data and data['resolutionDeadline']:
        try:
            resolution_deadline = datetime.fromisoformat(data['resolutionDeadline'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid resolution deadline format'
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
    
    # Create new non-compliance issue
    new_issue = NonComplianceIssue(
        id=uuid.uuid4(),
        organization_id=data['organizationId'],
        inspection_id=data.get('inspectionId'),
        issue_date=issue_date.date(),
        description=data['description'],
        severity=data['severity'],
        resolution_deadline=resolution_deadline.date() if resolution_deadline else None,
        resolution_date=resolution_date.date() if resolution_date else None,
        status=data['status']
    )
    
    db.session.add(new_issue)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_issue.to_dict(),
        'message': 'Non-compliance issue created successfully'
    }), 201

# Update non-compliance issue
@compliance_bp.route('/issues/<issue_id>', methods=['PUT'])
@token_required
def update_non_compliance_issue(current_user, issue_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    issue = NonComplianceIssue.query.filter_by(id=issue_id).first()
    
    if not issue:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Non-compliance issue not found'
        }), 404
    
    # Update fields
    if 'organizationId' in data:
        issue.organization_id = data['organizationId']
    if 'inspectionId' in data:
        issue.inspection_id = data['inspectionId']
    if 'description' in data:
        issue.description = data['description']
    if 'severity' in data:
        issue.severity = data['severity']
    if 'status' in data:
        issue.status = data['status']
    
    # Parse dates
    if 'issueDate' in data:
        try:
            issue_date = datetime.fromisoformat(data['issueDate'].replace('Z', '+00:00'))
            issue.issue_date = issue_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid issue date format'
            }), 400
    
    if 'resolutionDeadline' in data:
        if data['resolutionDeadline']:
            try:
                resolution_deadline = datetime.fromisoformat(data['resolutionDeadline'].replace('Z', '+00:00'))
                issue.resolution_deadline = resolution_deadline.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid resolution deadline format'
                }), 400
        else:
            issue.resolution_deadline = None
    
    if 'resolutionDate' in data:
        if data['resolutionDate']:
            try:
                resolution_date = datetime.fromisoformat(data['resolutionDate'].replace('Z', '+00:00'))
                issue.resolution_date = resolution_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid resolution date format'
                }), 400
        else:
            issue.resolution_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': issue.to_dict(),
        'message': 'Non-compliance issue updated successfully'
    }), 200

# Delete non-compliance issue
@compliance_bp.route('/issues/<issue_id>', methods=['DELETE'])
@token_required
def delete_non_compliance_issue(current_user, issue_id):
    issue = NonComplianceIssue.query.filter_by(id=issue_id).first()
    
    if not issue:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Non-compliance issue not found'
        }), 404
    
    db.session.delete(issue)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Non-compliance issue deleted successfully'
    }), 200
