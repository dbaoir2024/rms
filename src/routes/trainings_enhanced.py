from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.training import TrainingWorkshop, WorkshopParticipant
from src.models.user import User
from src.routes.auth import token_required

trainings_enhanced_bp = Blueprint('trainings_enhanced', __name__)

# Get all training workshops with pagination and filtering
@trainings_enhanced_bp.route('', methods=['GET'])
@token_required
def get_training_workshops(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    date_from = request.args.get('dateFrom', '')
    date_to = request.args.get('dateTo', '')
    
    # Build query
    query = TrainingWorkshop.query
    
    # Apply filters
    if search:
        query = query.filter(
            (TrainingWorkshop.workshop_name.ilike(f'%{search}%')) |
            (TrainingWorkshop.description.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(TrainingWorkshop.status == status)
    
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(TrainingWorkshop.workshop_date >= from_date.date())
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(TrainingWorkshop.workshop_date <= to_date.date())
        except ValueError:
            pass
    
    # Paginate results
    paginated_workshops = query.order_by(TrainingWorkshop.workshop_date.desc()).paginate(page=page, per_page=per_page)
    
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
@trainings_enhanced_bp.route('/<workshop_id>', methods=['GET'])
@token_required
def get_training_workshop(current_user, workshop_id):
    try:
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
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': str(e)
        }), 500

# Create new training workshop
@trainings_enhanced_bp.route('', methods=['POST'])
@token_required
def create_training_workshop(current_user):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to create training workshops'
        }), 403
    
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['workshopName', 'workshopDate', 'location']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Parse workshop date
    try:
        workshop_date = datetime.fromisoformat(data['workshopDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid workshop date format'
        }), 400
    
    # Create new training workshop
    new_workshop = TrainingWorkshop(
        id=uuid.uuid4(),
        workshop_name=data['workshopName'],
        workshop_date=workshop_date.date(),
        location=data['location'],
        description=data.get('description'),
        status=data.get('status', 'scheduled'),
        max_participants=data.get('maxParticipants'),
        facilitator=data.get('facilitator'),
        cost=data.get('cost')
    )
    
    db.session.add(new_workshop)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_workshop.to_dict(),
        'message': 'Training workshop created successfully'
    }), 201

# Update training workshop
@trainings_enhanced_bp.route('/<workshop_id>', methods=['PUT'])
@token_required
def update_training_workshop(current_user, workshop_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to update training workshops'
        }), 403
    
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
    if 'location' in data:
        workshop.location = data['location']
    if 'description' in data:
        workshop.description = data['description']
    if 'status' in data:
        workshop.status = data['status']
    if 'maxParticipants' in data:
        workshop.max_participants = data['maxParticipants']
    if 'facilitator' in data:
        workshop.facilitator = data['facilitator']
    if 'cost' in data:
        workshop.cost = data['cost']
    
    # Parse workshop date if provided
    if 'workshopDate' in data:
        try:
            workshop_date = datetime.fromisoformat(data['workshopDate'].replace('Z', '+00:00'))
            workshop.workshop_date = workshop_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid workshop date format'
            }), 400
    
    workshop.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': workshop.to_dict(),
        'message': 'Training workshop updated successfully'
    }), 200

# Delete training workshop
@trainings_enhanced_bp.route('/<workshop_id>', methods=['DELETE'])
@token_required
def delete_training_workshop(current_user, workshop_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete training workshops'
        }), 403
    
    workshop = TrainingWorkshop.query.filter_by(id=workshop_id).first()
    
    if not workshop:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Training workshop not found'
        }), 404
    
    # Delete participants first (due to foreign key constraint)
    WorkshopParticipant.query.filter_by(workshop_id=workshop_id).delete()
    
    # Delete workshop
    db.session.delete(workshop)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Training workshop deleted successfully'
    }), 200

# Get participants for a workshop
@trainings_enhanced_bp.route('/<workshop_id>/participants', methods=['GET'])
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

# Add participant to workshop
@trainings_enhanced_bp.route('/<workshop_id>/participants', methods=['POST'])
@token_required
def add_workshop_participant(current_user, workshop_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to add workshop participants'
        }), 403
    
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
    required_fields = ['userId']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if user exists
    user = User.query.filter_by(id=data['userId']).first()
    if not user:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'User not found'
        }), 404
    
    # Check if participant already exists
    existing_participant = WorkshopParticipant.query.filter_by(
        workshop_id=workshop_id,
        user_id=data['userId']
    ).first()
    
    if existing_participant:
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'User is already a participant in this workshop'
        }), 409
    
    # Create new participant
    new_participant = WorkshopParticipant(
        id=uuid.uuid4(),
        workshop_id=workshop_id,
        user_id=data['userId'],
        attendance_status=data.get('attendanceStatus', 'registered'),
        registration_date=datetime.utcnow().date()
    )
    
    db.session.add(new_participant)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_participant.to_dict(),
        'message': 'Workshop participant added successfully'
    }), 201

# Update workshop participant
@trainings_enhanced_bp.route('/participants/<participant_id>', methods=['PUT'])
@token_required
def update_workshop_participant(current_user, participant_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to update workshop participants'
        }), 403
    
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
    if 'attendanceStatus' in data:
        participant.attendance_status = data['attendanceStatus']
    
    participant.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': participant.to_dict(),
        'message': 'Workshop participant updated successfully'
    }), 200

# Remove participant from workshop
@trainings_enhanced_bp.route('/participants/<participant_id>', methods=['DELETE'])
@token_required
def remove_workshop_participant(current_user, participant_id):
    # Check if user has admin role
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to remove workshop participants'
        }), 403
    
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
        'message': 'Workshop participant removed successfully'
    }), 200

