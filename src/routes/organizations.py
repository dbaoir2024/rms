from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.organization import Organization, OrganizationType, OrganizationOfficial, OrganizationConstitution
from src.models.region import Region, District
from src.routes.auth import token_required

organizations_bp = Blueprint('organizations', __name__)

# Get all organizations with pagination and filtering
@organizations_bp.route('', methods=['GET'])
@token_required
def get_organizations(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    type_id = request.args.get('type', None, type=int)
    district_id = request.args.get('district', None, type=int)
    region_id = request.args.get('region', None, type=int)
    is_compliant = request.args.get('isCompliant', None)
    
    # Build query
    query = Organization.query
    
    # Apply filters
    if search:
        query = query.filter(
            (Organization.organization_name.ilike(f'%{search}%')) |
            (Organization.registration_number.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(Organization.status == status)
    
    if type_id:
        query = query.filter(Organization.organization_type_id == type_id)
    
    if district_id:
        query = query.filter(Organization.district_id == district_id)
    
    if region_id:
        query = query.join(District).filter(District.region_id == region_id)
    
    if is_compliant is not None:
        is_compliant_bool = is_compliant.lower() == 'true'
        query = query.filter(Organization.is_compliant == is_compliant_bool)
    
    # Paginate results
    paginated_orgs = query.order_by(Organization.organization_name).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [org.to_dict() for org in paginated_orgs.items],
            'total': paginated_orgs.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_orgs.pages
        },
        'message': 'Organizations retrieved successfully'
    }), 200

# Get organization by ID
@organizations_bp.route('/<organization_id>', methods=['GET'])
@token_required
def get_organization(current_user, organization_id):
    try:
        organization = Organization.query.filter_by(id=organization_id).first()
        
        if not organization:
            return jsonify({
                'success': False,
                'error': 'Not found',
                'message': 'Organization not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': organization.to_dict(),
            'message': 'Organization retrieved successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Create new organization
@organizations_bp.route('', methods=['POST'])
@token_required
def create_organization(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['registrationNumber', 'organizationName', 'organizationTypeId', 'registrationDate', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if registration number already exists
    if Organization.query.filter_by(registration_number=data['registrationNumber']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Registration number already exists'
        }), 409
    
    # Parse date
    try:
        registration_date = datetime.fromisoformat(data['registrationDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid registration date format'
        }), 400
    
    # Parse expiry date if provided
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
    
    # Create new organization
    new_organization = Organization(
        id=uuid.uuid4(),
        registration_number=data['registrationNumber'],
        organization_name=data['organizationName'],
        organization_type_id=data['organizationTypeId'],
        registration_date=registration_date.date(),
        expiry_date=expiry_date.date() if expiry_date else None,
        status=data['status'],
        address=data.get('address'),
        district_id=data.get('districtId'),
        contact_person=data.get('contactPerson'),
        contact_email=data.get('contactEmail'),
        contact_phone=data.get('contactPhone'),
        website=data.get('website'),
        membership_count=data.get('membershipCount'),
        is_compliant=data.get('isCompliant', True)
    )
    
    db.session.add(new_organization)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_organization.to_dict(),
        'message': 'Organization created successfully'
    }), 201

# Update organization
@organizations_bp.route('/<organization_id>', methods=['PUT'])
@token_required
def update_organization(current_user, organization_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check if registration number already exists for another organization
    if 'registrationNumber' in data and data['registrationNumber'] != organization.registration_number:
        existing_org = Organization.query.filter_by(registration_number=data['registrationNumber']).first()
        if existing_org and str(existing_org.id) != organization_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Registration number already exists'
            }), 409
    
    # Update fields
    if 'registrationNumber' in data:
        organization.registration_number = data['registrationNumber']
    if 'organizationName' in data:
        organization.organization_name = data['organizationName']
    if 'organizationTypeId' in data:
        organization.organization_type_id = data['organizationTypeId']
    if 'status' in data:
        organization.status = data['status']
    if 'address' in data:
        organization.address = data['address']
    if 'districtId' in data:
        organization.district_id = data['districtId']
    if 'contactPerson' in data:
        organization.contact_person = data['contactPerson']
    if 'contactEmail' in data:
        organization.contact_email = data['contactEmail']
    if 'contactPhone' in data:
        organization.contact_phone = data['contactPhone']
    if 'website' in data:
        organization.website = data['website']
    if 'membershipCount' in data:
        organization.membership_count = data['membershipCount']
    if 'isCompliant' in data:
        organization.is_compliant = data['isCompliant']
    
    # Parse registration date if provided
    if 'registrationDate' in data:
        try:
            registration_date = datetime.fromisoformat(data['registrationDate'].replace('Z', '+00:00'))
            organization.registration_date = registration_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid registration date format'
            }), 400
    
    # Parse expiry date if provided
    if 'expiryDate' in data:
        if data['expiryDate']:
            try:
                expiry_date = datetime.fromisoformat(data['expiryDate'].replace('Z', '+00:00'))
                organization.expiry_date = expiry_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid expiry date format'
                }), 400
        else:
            organization.expiry_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': organization.to_dict(),
        'message': 'Organization updated successfully'
    }), 200

# Delete organization
@organizations_bp.route('/<organization_id>', methods=['DELETE'])
@token_required
def delete_organization(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check if user has permission to delete
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete organizations'
        }), 403
    
    # In a real application, you might want to check for dependencies
    # before deleting, or implement soft delete
    
    db.session.delete(organization)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Organization deleted successfully'
    }), 200

# Get organization types
@organizations_bp.route('/types', methods=['GET'])
@token_required
def get_organization_types(current_user):
    types = OrganizationType.query.all()
    
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in types],
        'message': 'Organization types retrieved successfully'
    }), 200

# Get organization officials
@organizations_bp.route('/<organization_id>/officials', methods=['GET'])
@token_required
def get_organization_officials(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    officials = OrganizationOfficial.query.filter_by(organization_id=organization_id).all()
    
    return jsonify({
        'success': True,
        'data': [official.to_dict() for official in officials],
        'message': 'Organization officials retrieved successfully'
    }), 200

# Create organization official
@organizations_bp.route('/<organization_id>/officials', methods=['POST'])
@token_required
def create_organization_official(current_user, organization_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check required fields
    required_fields = ['position', 'firstName', 'lastName', 'startDate']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse start date
    try:
        start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid start date format'
        }), 400
    
    # Parse end date if provided
    end_date = None
    if 'endDate' in data and data['endDate']:
        try:
            end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid end date format'
            }), 400
    
    # Create new official
    new_official = OrganizationOfficial(
        id=uuid.uuid4(),
        organization_id=organization_id,
        position=data['position'],
        first_name=data['firstName'],
        last_name=data['lastName'],
        email=data.get('email'),
        phone=data.get('phone'),
        start_date=start_date.date(),
        end_date=end_date.date() if end_date else None,
        is_current=data.get('isCurrent', True)
    )
    
    db.session.add(new_official)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_official.to_dict(),
        'message': 'Organization official created successfully'
    }), 201

# Update organization official
@organizations_bp.route('/officials/<official_id>', methods=['PUT'])
@token_required
def update_organization_official(current_user, official_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    official = OrganizationOfficial.query.filter_by(id=official_id).first()
    
    if not official:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Official not found'
        }), 404
    
    # Update fields
    if 'position' in data:
        official.position = data['position']
    if 'firstName' in data:
        official.first_name = data['firstName']
    if 'lastName' in data:
        official.last_name = data['lastName']
    if 'email' in data:
        official.email = data['email']
    if 'phone' in data:
        official.phone = data['phone']
    if 'isCurrent' in data:
        official.is_current = data['isCurrent']
    
    # Parse start date if provided
    if 'startDate' in data:
        try:
            start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
            official.start_date = start_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid start date format'
            }), 400
    
    # Parse end date if provided
    if 'endDate' in data:
        if data['endDate']:
            try:
                end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
                official.end_date = end_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid end date format'
                }), 400
        else:
            official.end_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': official.to_dict(),
        'message': 'Organization official updated successfully'
    }), 200

# Delete organization official
@organizations_bp.route('/officials/<official_id>', methods=['DELETE'])
@token_required
def delete_organization_official(current_user, official_id):
    official = OrganizationOfficial.query.filter_by(id=official_id).first()
    
    if not official:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Official not found'
        }), 404
    
    db.session.delete(official)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Organization official deleted successfully'
    }), 200

# Get organization constitutions
@organizations_bp.route('/<organization_id>/constitutions', methods=['GET'])
@token_required
def get_organization_constitutions(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    constitutions = OrganizationConstitution.query.filter_by(organization_id=organization_id).order_by(OrganizationConstitution.version_number.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [constitution.to_dict() for constitution in constitutions],
        'message': 'Organization constitutions retrieved successfully'
    }), 200

# Create organization constitution
@organizations_bp.route('/<organization_id>/constitutions', methods=['POST'])
@token_required
def create_organization_constitution(current_user, organization_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check required fields
    required_fields = ['versionNumber', 'effectiveDate', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if version number already exists
    existing_constitution = OrganizationConstitution.query.filter_by(
        organization_id=organization_id,
        version_number=data['versionNumber']
    ).first()
    
    if existing_constitution:
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Version number already exists for this organization'
        }), 409
    
    # Parse effective date
    try:
        effective_date = datetime.fromisoformat(data['effectiveDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid effective date format'
        }), 400
    
    # Parse approval date if provided
    approval_date = None
    if 'approvalDate' in data and data['approvalDate']:
        try:
            approval_date = datetime.fromisoformat(data['approvalDate'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid approval date format'
            }), 400
    
    # Create new constitution
    new_constitution = OrganizationConstitution(
        id=uuid.uuid4(),
        organization_id=organization_id,
        version_number=data['versionNumber'],
        effective_date=effective_date.date(),
        approval_date=approval_date.date() if approval_date else None,
        approved_by=data.get('approvedBy'),
        document_path=data.get('documentPath'),
        status=data['status'],
        notes=data.get('notes')
    )
    
    db.session.add(new_constitution)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_constitution.to_dict(),
        'message': 'Organization constitution created successfully'
    }), 201

# Update organization constitution
@organizations_bp.route('/constitutions/<constitution_id>', methods=['PUT'])
@token_required
def update_organization_constitution(current_user, constitution_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    constitution = OrganizationConstitution.query.filter_by(id=constitution_id).first()
    
    if not constitution:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Constitution not found'
        }), 404
    
    # Check if version number already exists for another constitution
    if 'versionNumber' in data and data['versionNumber'] != constitution.version_number:
        existing_constitution = OrganizationConstitution.query.filter_by(
            organization_id=constitution.organization_id,
            version_number=data['versionNumber']
        ).first()
        
        if existing_constitution and str(existing_constitution.id) != constitution_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Version number already exists for this organization'
            }), 409
    
    # Update fields
    if 'versionNumber' in data:
        constitution.version_number = data['versionNumber']
    if 'status' in data:
        constitution.status = data['status']
    if 'documentPath' in data:
        constitution.document_path = data['documentPath']
    if 'notes' in data:
        constitution.notes = data['notes']
    if 'approvedBy' in data:
        constitution.approved_by = data['approvedBy']
    
    # Parse effective date if provided
    if 'effectiveDate' in data:
        try:
            effective_date = datetime.fromisoformat(data['effectiveDate'].replace('Z', '+00:00'))
            constitution.effective_date = effective_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid effective date format'
            }), 400
    
    # Parse approval date if provided
    if 'approvalDate' in data:
        if data['approvalDate']:
            try:
                approval_date = datetime.fromisoformat(data['approvalDate'].replace('Z', '+00:00'))
                constitution.approval_date = approval_date.date()
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Bad request',
                    'message': 'Invalid approval date format'
                }), 400
        else:
            constitution.approval_date = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': constitution.to_dict(),
        'message': 'Organization constitution updated successfully'
    }), 200

# Delete organization constitution
@organizations_bp.route('/constitutions/<constitution_id>', methods=['DELETE'])
@token_required
def delete_organization_constitution(current_user, constitution_id):
    constitution = OrganizationConstitution.query.filter_by(id=constitution_id).first()
    
    if not constitution:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Constitution not found'
        }), 404
    
    db.session.delete(constitution)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Organization constitution deleted successfully'
    }), 200

# Get regions
@organizations_bp.route('/regions', methods=['GET'])
@token_required
def get_regions(current_user):
    regions = Region.query.all()
    
    return jsonify({
        'success': True,
        'data': [region.to_dict() for region in regions],
        'message': 'Regions retrieved successfully'
    }), 200

# Get districts
@organizations_bp.route('/districts', methods=['GET'])
@token_required
def get_districts(current_user):
    region_id = request.args.get('region', None, type=int)
    
    query = District.query
    
    if region_id:
        query = query.filter_by(region_id=region_id)
    
    districts = query.all()
    
    return jsonify({
        'success': True,
        'data': [district.to_dict() for district in districts],
        'message': 'Districts retrieved successfully'
    }), 200
