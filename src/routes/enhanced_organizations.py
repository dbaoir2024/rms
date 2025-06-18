from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime
import os
import re
from werkzeug.utils import secure_filename

from src.extensions import db
from src.models.organization import Organization, OrganizationType, OrganizationOfficial, OrganizationConstitution
from src.models.membership import MembershipList, MembershipVettingHistory
from src.routes.auth import token_required

# Updated organizations blueprint with enhanced features
organizations_bp = Blueprint('organizations', __name__)

# Get all organizations with pagination and filtering
@organizations_bp.route('', methods=['GET'])
@token_required
def get_organizations(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    org_type = request.args.get('type', None, type=int)
    status = request.args.get('status', None)
    region_id = request.args.get('region', None, type=int)
    district_id = request.args.get('district', None, type=int)
    is_compliant = request.args.get('isCompliant', None)
    
    # Build query
    query = Organization.query
    
    # Apply filters
    if search:
        query = query.filter(
            (Organization.organization_name.ilike(f'%{search}%')) |
            (Organization.registration_number.ilike(f'%{search}%'))
        )
    
    if org_type:
        query = query.filter(Organization.organization_type_id == org_type)
    
    if status:
        query = query.filter(Organization.status == status)
    
    if region_id:
        query = query.join(District).filter(District.region_id == region_id)
    
    if district_id:
        query = query.filter(Organization.district_id == district_id)
    
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

# Create organization with IO-XX format validation
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
    
    # Validate registration number format (IO-XX)
    reg_number = data['registrationNumber']
    if not re.match(r'^IO-\d{2,}$', reg_number):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Registration number must be in format IO-XX (e.g., IO-01, IO-02)'
        }), 400
    
    # Check if registration number already exists
    if Organization.query.filter_by(registration_number=reg_number).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Registration number already exists'
        }), 409
    
    # Parse dates
    try:
        registration_date = datetime.fromisoformat(data['registrationDate'].replace('Z', '+00:00'))
        first_registered_date = registration_date
        
        if 'firstRegisteredDate' in data and data['firstRegisteredDate']:
            first_registered_date = datetime.fromisoformat(data['firstRegisteredDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid date format'
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
    
    # Create new organization
    new_organization = Organization(
        id=uuid.uuid4(),
        registration_number=reg_number,
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
        membership_count=data.get('membershipCount', 0),
        is_compliant=data.get('isCompliant', True),
        first_registered_date=first_registered_date.date()
    )
    
    db.session.add(new_organization)
    
    # Create historical record for trend analysis
    historical_record = OrganizationHistoricalData(
        id=uuid.uuid4(),
        organization_id=new_organization.id,
        record_date=datetime.utcnow().date(),
        status=new_organization.status,
        membership_count=new_organization.membership_count,
        is_compliant=new_organization.is_compliant
    )
    
    db.session.add(historical_record)
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
    
    # Validate registration number format if provided
    if 'registrationNumber' in data:
        reg_number = data['registrationNumber']
        if not re.match(r'^IO-\d{2,}$', reg_number):
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Registration number must be in format IO-XX (e.g., IO-01, IO-02)'
            }), 400
        
        # Check if registration number already exists for another organization
        existing_org = Organization.query.filter_by(registration_number=reg_number).first()
        if existing_org and str(existing_org.id) != organization_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Registration number already exists'
            }), 409
        
        organization.registration_number = reg_number
    
    # Update fields
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
    
    # Parse dates
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
    
    if 'firstRegisteredDate' in data:
        try:
            first_registered_date = datetime.fromisoformat(data['firstRegisteredDate'].replace('Z', '+00:00'))
            organization.first_registered_date = first_registered_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid first registered date format'
            }), 400
    
    # Create historical record for trend analysis if significant changes
    if 'status' in data or 'membershipCount' in data or 'isCompliant' in data:
        historical_record = OrganizationHistoricalData(
            id=uuid.uuid4(),
            organization_id=organization.id,
            record_date=datetime.utcnow().date(),
            status=organization.status,
            membership_count=organization.membership_count,
            is_compliant=organization.is_compliant
        )
        db.session.add(historical_record)
    
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
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete organizations'
        }), 403
    
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Instead of deleting, mark as deregistered
    organization.status = 'deregistered'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Organization marked as deregistered successfully'
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
    
    # Parse dates
    try:
        start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid start date format'
        }), 400
    
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
            'message': 'Organization official not found'
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
    
    # Parse dates
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
            'message': 'Organization official not found'
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
    
    constitutions = OrganizationConstitution.query.filter_by(organization_id=organization_id).all()
    
    return jsonify({
        'success': True,
        'data': [constitution.to_dict() for constitution in constitutions],
        'message': 'Organization constitutions retrieved successfully'
    }), 200

# Upload organization constitution with OCR processing
@organizations_bp.route('/<organization_id>/constitutions', methods=['POST'])
@token_required
def upload_organization_constitution(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No file selected'
        }), 400
    
    # Get form data
    version_number = request.form.get('versionNumber', type=int)
    effective_date = request.form.get('effectiveDate')
    status = request.form.get('status', 'pending')
    notes = request.form.get('notes')
    
    if not version_number or not effective_date:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Version number and effective date are required'
        }), 400
    
    # Parse effective date
    try:
        effective_date_obj = datetime.fromisoformat(effective_date.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid effective date format'
        }), 400
    
    # Save file
    filename = secure_filename(f"{organization.registration_number}_constitution_v{version_number}_{int(datetime.utcnow().timestamp())}.pdf")
    upload_folder = os.path.join(os.getcwd(), 'uploads', 'constitutions')
    
    # Create directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # Process OCR (in a real implementation, this would use a proper OCR library)
    # For this example, we'll simulate OCR processing
    ocr_content = "This is simulated OCR content for the constitution document."
    
    # Create new constitution record
    new_constitution = OrganizationConstitution(
        id=uuid.uuid4(),
        organization_id=organization_id,
        version_number=version_number,
        effective_date=effective_date_obj.date(),
        document_path=file_path,
        ocr_content=ocr_content,
        status=status,
        notes=notes
    )
    
    db.session.add(new_constitution)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_constitution.to_dict(),
        'message': 'Constitution uploaded successfully'
    }), 201

# Search constitution by clause or content
@organizations_bp.route('/constitutions/search', methods=['GET'])
@token_required
def search_constitutions(current_user):
    query = request.args.get('query', '')
    organization_id = request.args.get('organizationId')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Search query is required'
        }), 400
    
    # Build search query
    search_query = OrganizationConstitution.query.filter(
        OrganizationConstitution.ocr_content.ilike(f'%{query}%')
    )
    
    if organization_id:
        search_query = search_query.filter(OrganizationConstitution.organization_id == organization_id)
    
    results = search_query.all()
    
    return jsonify({
        'success': True,
        'data': [
            {
                'constitution': constitution.to_dict(),
                'organization': Organization.query.get(constitution.organization_id).to_dict(),
                'matchedText': constitution.ocr_content[:500] + '...' if len(constitution.ocr_content) > 500 else constitution.ocr_content
            }
            for constitution in results
        ],
        'message': f'Found {len(results)} constitutions matching "{query}"'
    }), 200

# Get membership lists for an organization
@organizations_bp.route('/<organization_id>/membership-lists', methods=['GET'])
@token_required
def get_membership_lists(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    membership_lists = MembershipList.query.filter_by(organization_id=organization_id).order_by(MembershipList.submission_date.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [membership_list.to_dict() for membership_list in membership_lists],
        'message': 'Membership lists retrieved successfully'
    }), 200

# Upload membership list
@organizations_bp.route('/<organization_id>/membership-lists', methods=['POST'])
@token_required
def upload_membership_list(current_user, organization_id):
    organization = Organization.query.filter_by(id=organization_id).first()
    
    if not organization:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Organization not found'
        }), 404
    
    # Check if file is provided
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No file provided'
        }), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No file selected'
        }), 400
    
    # Get form data
    submission_date = request.form.get('submissionDate')
    submitted_by = request.form.get('submittedBy')
    member_count = request.form.get('memberCount', type=int)
    notes = request.form.get('notes')
    
    if not submission_date or not member_count:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Submission date and member count are required'
        }), 400
    
    # Parse submission date
    try:
        submission_date_obj = datetime.fromisoformat(submission_date.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid submission date format'
        }), 400
    
    # Save file
    filename = secure_filename(f"{organization.registration_number}_membership_{int(datetime.utcnow().timestamp())}.{file.filename.split('.')[-1]}")
    upload_folder = os.path.join(os.getcwd(), 'uploads', 'membership_lists')
    
    # Create directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # Get previous membership count
    previous_list = MembershipList.query.filter_by(organization_id=organization_id).order_by(MembershipList.submission_date.desc()).first()
    previous_count = previous_list.member_count if previous_list else 0
    
    # Calculate change percentage
    change_percentage = ((member_count - previous_count) / previous_count * 100) if previous_count > 0 else 0
    
    # Create new membership list record
    new_membership_list = MembershipList(
        id=uuid.uuid4(),
        organization_id=organization_id,
        submission_date=submission_date_obj.date(),
        submitted_by=submitted_by,
        member_count=member_count,
        previous_count=previous_count,
        change_percentage=change_percentage,
        status='submitted',
        document_path=file_path,
        notes=notes
    )
    
    db.session.add(new_membership_list)
    
    # Update organization membership count
    organization.membership_count = member_count
    
    # Create historical record for trend analysis
    historical_record = OrganizationHistoricalData(
        id=uuid.uuid4(),
        organization_id=organization.id,
        record_date=datetime.utcnow().date(),
        status=organization.status,
        membership_count=member_count,
        is_compliant=organization.is_compliant
    )
    
    db.session.add(historical_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_membership_list.to_dict(),
        'message': 'Membership list uploaded successfully'
    }), 201

# Review membership list (for registrar or labor officers)
@organizations_bp.route('/membership-lists/<list_id>/review', methods=['PUT'])
@token_required
def review_membership_list(current_user, list_id):
    # Check if user has appropriate role
    if not current_user.role or not any(role in current_user.role.role_code for role in ['REGISTRAR', 'DEPUTY_REGISTRAR', 'INSPECTOR']):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to review membership lists'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    membership_list = MembershipList.query.filter_by(id=list_id).first()
    
    if not membership_list:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Membership list not found'
        }), 404
    
    # Check required fields
    if 'status' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Status is required'
        }), 400
    
    # Update membership list
    membership_list.status = data['status']
    membership_list.reviewed_by = current_user.id
    membership_list.review_date = datetime.utcnow().date()
    
    if 'notes' in data:
        membership_list.notes = data['notes']
    
    # Create vetting history record
    vetting_record = MembershipVettingHistory(
        id=uuid.uuid4(),
        membership_list_id=list_id,
        vetting_date=datetime.utcnow().date(),
        vetted_by=current_user.id,
        status='completed',
        issues_found=data.get('issuesFound'),
        resolution=data.get('resolution')
    )
    
    db.session.add(vetting_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': membership_list.to_dict(),
        'message': 'Membership list reviewed successfully'
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

# Get organization trend data
@organizations_bp.route('/trends', methods=['GET'])
@token_required
def get_organization_trends(current_user):
    # Get query parameters
    start_year = request.args.get('startYear', 1963, type=int)
    end_year = request.args.get('endYear', datetime.utcnow().year, type=int)
    
    # Get organizations by registration year
    orgs_by_year = {}
    for year in range(start_year, end_year + 1):
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        
        # Count new registrations
        new_registrations = Organization.query.filter(
            Organization.first_registered_date.between(start_date, end_date)
        ).count()
        
        # Count active organizations at the end of the year
        active_orgs = Organization.query.filter(
            Organization.first_registered_date <= end_date,
            or_(
                Organization.status == 'active',
                and_(
                    Organization.status == 'deregistered',
                    Organization.updated_at > datetime(year, 12, 31)
                )
            )
        ).count()
        
        # Count deregistered organizations during the year
        deregistered_orgs = Organization.query.filter(
            Organization.status == 'deregistered',
            extract('year', Organization.updated_at) == year
        ).count()
        
        orgs_by_year[year] = {
            'year': year,
            'newRegistrations': new_registrations,
            'activeOrganizations': active_orgs,
            'deregisteredOrganizations': deregistered_orgs
        }
    
    # Get employment trend data
    employment_trends = EmploymentTrendData.query.order_by(EmploymentTrendData.record_date).all()
    
    return jsonify({
        'success': True,
        'data': {
            'organizationsByYear': list(orgs_by_year.values()),
            'employmentTrends': [trend.to_dict() for trend in employment_trends]
        },
        'message': 'Organization trend data retrieved successfully'
    }), 200
