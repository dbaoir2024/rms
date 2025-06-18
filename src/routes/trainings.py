from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.training import TrainingWorkshop, TrainingType, WorkshopParticipant
from src.routes.auth import token_required

trainings_bp = Blueprint('trainings', __name__)

# Get all training workshops with pagination and filtering
@trainings_bp.route('/workshops', methods=['GET'])
@token_required
def get_training_workshops(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    type_id = request.args.get('type', None, type=int)
    date_from = request.args.get('dateFrom', None)
    date_to = request.args.get('dateTo', None)
    
    # Build query
    query = TrainingWorkshop.query
    
    # Apply filters
    if search:
        query = query.filter(
            (TrainingWorkshop.workshop_name.ilike(f'%{search}%')) |
            (TrainingWorkshop.facilitator.ilike(f'%{search}%')) |
            (TrainingWorkshop.location.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(TrainingWorkshop.status == status)
    
    if type_id:
        query = query.filter(TrainingWorkshop.training_type_id == type_id)
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
            query = query.filter(TrainingWorkshop.start_date >= date_from_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date from format'
            }), 400
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
            query = query.filter(TrainingWorkshop.end_date <= date_to_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date to format'
            }), 400
    
    # Paginate results
    paginated_workshops = query.order_by(TrainingWorkshop.start_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [workshop.to_dict() for workshop in paginated_workshops.items],
            'total': paginated_workshops.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_workshops.pages
        },
        'message': 'Training workshops retrieved successfully'
    }), 200

# Get training workshop by ID
@trainings_bp.route('/workshops/<workshop_id>', methods=['GET'])
@token_required
def get_training_workshop(current_user, workshop_id):
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': workshop.to_dict(),
        'message': 'Training workshop retrieved successfully'
    }), 200

# Create training workshop
@trainings_bp.route('/workshops', methods=['POST'])
@token_required
def create_training_workshop(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['workshopName', 'startDate', 'endDate', 'status']
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
        end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid date format'
        }), 400
    
    # Check if end date is after start date
    if end_date < start_date:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'End date must be after start date'
        }), 400
    
    # Create new training workshop
    new_workshop = TrainingWorkshop(
        id=uuid.uuid4(),
        workshop_name=data['workshopName'],
        training_type_id=data.get('trainingTypeId'),
        start_date=start_date.date(),
        end_date=end_date.date(),
        location=data.get('location'),
        facilitator=data.get('facilitator'),
        max_participants=data.get('maxParticipants'),
        status=data['status'],
        description=data.get('description'),
        materials_path=data.get('materialsPath')
    )
    
    db.session.add(new_workshop)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_workshop.to_dict(),
        'message': 'Training workshop created successfully'
    }), 201

# Update training workshop
@trainings_bp.route('/workshops/<workshop_id>', methods=['PUT'])
@token_required
def update_training_workshop(current_user, workshop_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    # Update fields
    if 'workshopName' in data:
        workshop.workshop_name = data['workshopName']
    if 'trainingTypeId' in data:
        workshop.training_type_id = data['trainingTypeId']
    if 'location' in data:
        workshop.location = data['location']
    if 'facilitator' in data:
        workshop.facilitator = data['facilitator']
    if 'maxParticipants' in data:
        workshop.max_participants = data['maxParticipants']
    if 'status' in data:
        workshop.status = data['status']
    if 'description' in data:
        workshop.description = data['description']
    if 'materialsPath' in data:
        workshop.materials_path = data['materialsPath']
    
    # Parse dates
    if 'startDate' in data:
        try:
            start_date = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
            workshop.start_date = start_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid start date format'
            }), 400
    
    if 'endDate' in data:
        try:
            end_date = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
            workshop.end_date = end_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid end date format'
            }), 400
    
    # Check if end date is after start date
    if workshop.end_date < workshop.start_date:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'End date must be after start date'
        }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': workshop.to_dict(),
        'message': 'Training workshop updated successfully'
    }), 200

# Delete training workshop
@trainings_bp.route('/workshops/<workshop_id>', methods=['DELETE'])
@token_required
def delete_training_workshop(current_user, workshop_id):
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    # Check if user has permission to delete
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete training workshops'
        }), 403
    
    db.session.delete(workshop)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Training workshop deleted successfully'
    }), 200

# Get training types
@trainings_bp.route('/types', methods=['GET'])
@token_required
def get_training_types(current_user):
    types = TrainingType.query.all()
    
    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in types],
        'message': 'Training types retrieved successfully'
    }), 200

# Get workshop participants
@trainings_bp.route('/workshops/<workshop_id>/participants', methods=['GET'])
@token_required
def get_workshop_participants(current_user, workshop_id):
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    participants = WorkshopParticipant.query.filter_by(workshop_id=workshop_id).all()
    
    return jsonify({
        'success': True,
        'data': [participant.to_dict() for participant in participants],
        'message': 'Workshop participants retrieved successfully'
    }), 200

# Create workshop participant
@trainings_bp.route('/workshops/<workshop_id>/participants', methods=['POST'])
@token_required
def create_workshop_participant(current_user, workshop_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    # Check required fields
    required_fields = ['firstName', 'lastName']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if max participants limit is reached
    if workshop.max_participants:
        current_participants_count = WorkshopParticipant.query.filter_by(workshop_id=workshop_id).count()
        if current_participants_count >= workshop.max_participants:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Maximum number of participants reached'
            }), 400
    
    # Create new participant
    new_participant = WorkshopParticipant(
        id=uuid.uuid4(),
        workshop_id=workshop_id,
        organization_id=data.get('organizationId'),
        official_id=data.get('officialId'),
        first_name=data['firstName'],
        last_name=data['lastName'],
        email=data.get('email'),
        phone=data.get('phone'),
        attendance_status=data.get('attendanceStatus', 'registered'),
        certificate_issued=data.get('certificateIssued', False),
        notes=data.get('notes')
    )
    
    db.session.add(new_participant)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_participant.to_dict(),
        'message': 'Workshop participant created successfully'
    }), 201

# Update workshop participant
@trainings_bp.route('/participants/<participant_id>', methods=['PUT'])
@token_required
def update_workshop_participant(current_user, participant_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    participant = WorkshopParticipant.query.filter_by(id=participant_id).first()
    
    if not participant:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Workshop participant not found'
        }), 404
    
    # Update fields
    if 'firstName' in data:
        participant.first_name = data['firstName']
    if 'lastName' in data:
        participant.last_name = data['lastName']
    if 'organizationId' in data:
        participant.organization_id = data['organizationId']
    if 'officialId' in data:
        participant.official_id = data['officialId']
    if 'email' in data:
        participant.email = data['email']
    if 'phone' in data:
        participant.phone = data['phone']
    if 'attendanceStatus' in data:
        participant.attendance_status = data['attendanceStatus']
    if 'certificateIssued' in data:
        participant.certificate_issued = data['certificateIssued']
    if 'notes' in data:
        participant.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': participant.to_dict(),
        'message': 'Workshop participant updated successfully'
    }), 200

# Delete workshop participant
@trainings_bp.route('/participants/<participant_id>', methods=['DELETE'])
@token_required
def delete_workshop_participant(current_user, participant_id):
    participant = WorkshopParticipant.query.filter_by(id=participant_id).first()
    
    if not participant:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Workshop participant not found'
        }), 404
    
    db.session.delete(participant)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Workshop participant deleted successfully'
    }), 200
