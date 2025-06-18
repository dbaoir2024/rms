from flask import Blueprint, request, jsonify
from functools import wraps
import uuid
from datetime import datetime

from src.extensions import db
from src.models.ballot import BallotElection, BallotPosition, BallotCandidate, BallotResult
from src.routes.auth import token_required

ballots_bp = Blueprint('ballots', __name__)

# Get all ballot elections with pagination and filtering
@ballots_bp.route('/elections', methods=['GET'])
@token_required
def get_ballot_elections(current_user):
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('pageSize', 10, type=int)
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    organization_id = request.args.get('organization', None)
    date_from = request.args.get('dateFrom', None)
    date_to = request.args.get('dateTo', None)
    
    # Build query
    query = BallotElection.query
    
    # Apply filters
    if search:
        query = query.filter(
            (BallotElection.election_number.ilike(f'%{search}%')) |
            (BallotElection.purpose.ilike(f'%{search}%'))
        )
    
    if status:
        query = query.filter(BallotElection.status == status)
    
    if organization_id:
        query = query.filter(BallotElection.organization_id == organization_id)
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00')).date()
            query = query.filter(BallotElection.election_date >= date_from_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date from format'
            }), 400
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00')).date()
            query = query.filter(BallotElection.election_date <= date_to_obj)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid date to format'
            }), 400
    
    # Paginate results
    paginated_elections = query.order_by(BallotElection.election_date.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': [election.to_dict() for election in paginated_elections.items],
            'total': paginated_elections.total,
            'page': page,
            'pageSize': per_page,
            'totalPages': paginated_elections.pages
        },
        'message': 'Ballot elections retrieved successfully'
    }), 200

# Get ballot election by ID
@ballots_bp.route('/elections/<election_id>', methods=['GET'])
@token_required
def get_ballot_election(current_user, election_id):
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    return jsonify({
        'success': True,
        'data': election.to_dict(),
        'message': 'Ballot election retrieved successfully'
    }), 200

# Create ballot election
@ballots_bp.route('/elections', methods=['POST'])
@token_required
def create_ballot_election(current_user):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    # Check required fields
    required_fields = ['electionNumber', 'organizationId', 'electionDate', 'purpose', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if election number already exists
    if BallotElection.query.filter_by(election_number=data['electionNumber']).first():
        return jsonify({
            'success': False,
            'error': 'Conflict',
            'message': 'Election number already exists'
        }), 409
    
    # Parse election date
    try:
        election_date = datetime.fromisoformat(data['electionDate'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid election date format'
        }), 400
    
    # Create new ballot election
    new_election = BallotElection(
        id=uuid.uuid4(),
        election_number=data['electionNumber'],
        organization_id=data['organizationId'],
        election_date=election_date.date(),
        purpose=data['purpose'],
        status=data['status'],
        supervisor_id=data.get('supervisorId'),
        location=data.get('location'),
        notes=data.get('notes')
    )
    
    db.session.add(new_election)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_election.to_dict(),
        'message': 'Ballot election created successfully'
    }), 201

# Update ballot election
@ballots_bp.route('/elections/<election_id>', methods=['PUT'])
@token_required
def update_ballot_election(current_user, election_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    # Check if election number already exists for another election
    if 'electionNumber' in data and data['electionNumber'] != election.election_number:
        existing_election = BallotElection.query.filter_by(election_number=data['electionNumber']).first()
        if existing_election and str(existing_election.id) != election_id:
            return jsonify({
                'success': False,
                'error': 'Conflict',
                'message': 'Election number already exists'
            }), 409
    
    # Update fields
    if 'electionNumber' in data:
        election.election_number = data['electionNumber']
    if 'organizationId' in data:
        election.organization_id = data['organizationId']
    if 'purpose' in data:
        election.purpose = data['purpose']
    if 'status' in data:
        election.status = data['status']
    if 'supervisorId' in data:
        election.supervisor_id = data['supervisorId']
    if 'location' in data:
        election.location = data['location']
    if 'notes' in data:
        election.notes = data['notes']
    
    # Parse election date if provided
    if 'electionDate' in data:
        try:
            election_date = datetime.fromisoformat(data['electionDate'].replace('Z', '+00:00'))
            election.election_date = election_date.date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': 'Invalid election date format'
            }), 400
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': election.to_dict(),
        'message': 'Ballot election updated successfully'
    }), 200

# Delete ballot election
@ballots_bp.route('/elections/<election_id>', methods=['DELETE'])
@token_required
def delete_ballot_election(current_user, election_id):
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    # Check if user has permission to delete
    if not current_user.role or 'ADMIN' not in current_user.role.role_code:
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to delete ballot elections'
        }), 403
    
    # In a real application, you might want to check for dependencies
    # before deleting, or implement soft delete
    
    db.session.delete(election)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ballot election deleted successfully'
    }), 200

# Get ballot positions for an election
@ballots_bp.route('/elections/<election_id>/positions', methods=['GET'])
@token_required
def get_ballot_positions(current_user, election_id):
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    positions = BallotPosition.query.filter_by(election_id=election_id).all()
    
    return jsonify({
        'success': True,
        'data': [position.to_dict() for position in positions],
        'message': 'Ballot positions retrieved successfully'
    }), 200

# Create ballot position
@ballots_bp.route('/elections/<election_id>/positions', methods=['POST'])
@token_required
def create_ballot_position(current_user, election_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    # Check required fields
    if 'positionName' not in data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Position name is required'
        }), 400
    
    # Create new ballot position
    new_position = BallotPosition(
        id=uuid.uuid4(),
        election_id=election_id,
        position_name=data['positionName'],
        description=data.get('description')
    )
    
    db.session.add(new_position)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_position.to_dict(),
        'message': 'Ballot position created successfully'
    }), 201

# Update ballot position
@ballots_bp.route('/positions/<position_id>', methods=['PUT'])
@token_required
def update_ballot_position(current_user, position_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    position = BallotPosition.query.filter_by(id=position_id).first()
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot position not found'
        }), 404
    
    # Update fields
    if 'positionName' in data:
        position.position_name = data['positionName']
    if 'description' in data:
        position.description = data['description']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': position.to_dict(),
        'message': 'Ballot position updated successfully'
    }), 200

# Delete ballot position
@ballots_bp.route('/positions/<position_id>', methods=['DELETE'])
@token_required
def delete_ballot_position(current_user, position_id):
    position = BallotPosition.query.filter_by(id=position_id).first()
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot position not found'
        }), 404
    
    db.session.delete(position)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ballot position deleted successfully'
    }), 200

# Get candidates for a position
@ballots_bp.route('/positions/<position_id>/candidates', methods=['GET'])
@token_required
def get_ballot_candidates(current_user, position_id):
    position = BallotPosition.query.filter_by(id=position_id).first()
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot position not found'
        }), 404
    
    candidates = BallotCandidate.query.filter_by(position_id=position_id).all()
    
    return jsonify({
        'success': True,
        'data': [candidate.to_dict() for candidate in candidates],
        'message': 'Ballot candidates retrieved successfully'
    }), 200

# Create ballot candidate
@ballots_bp.route('/positions/<position_id>/candidates', methods=['POST'])
@token_required
def create_ballot_candidate(current_user, position_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    position = BallotPosition.query.filter_by(id=position_id).first()
    
    if not position:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot position not found'
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
    
    # Create new ballot candidate
    new_candidate = BallotCandidate(
        id=uuid.uuid4(),
        position_id=position_id,
        first_name=data['firstName'],
        last_name=data['lastName'],
        bio=data.get('bio')
    )
    
    db.session.add(new_candidate)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': new_candidate.to_dict(),
        'message': 'Ballot candidate created successfully'
    }), 201

# Update ballot candidate
@ballots_bp.route('/candidates/<candidate_id>', methods=['PUT'])
@token_required
def update_ballot_candidate(current_user, candidate_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    candidate = BallotCandidate.query.filter_by(id=candidate_id).first()
    
    if not candidate:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot candidate not found'
        }), 404
    
    # Update fields
    if 'firstName' in data:
        candidate.first_name = data['firstName']
    if 'lastName' in data:
        candidate.last_name = data['lastName']
    if 'bio' in data:
        candidate.bio = data['bio']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': candidate.to_dict(),
        'message': 'Ballot candidate updated successfully'
    }), 200

# Delete ballot candidate
@ballots_bp.route('/candidates/<candidate_id>', methods=['DELETE'])
@token_required
def delete_ballot_candidate(current_user, candidate_id):
    candidate = BallotCandidate.query.filter_by(id=candidate_id).first()
    
    if not candidate:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot candidate not found'
        }), 404
    
    db.session.delete(candidate)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ballot candidate deleted successfully'
    }), 200

# Get results for an election
@ballots_bp.route('/elections/<election_id>/results', methods=['GET'])
@token_required
def get_ballot_results(current_user, election_id):
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    results = BallotResult.query.filter_by(election_id=election_id).all()
    
    return jsonify({
        'success': True,
        'data': [result.to_dict() for result in results],
        'message': 'Ballot results retrieved successfully'
    }), 200

# Create or update ballot result
@ballots_bp.route('/elections/<election_id>/results', methods=['POST'])
@token_required
def create_ballot_result(current_user, election_id):
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'No data provided'
        }), 400
    
    election = BallotElection.query.filter_by(id=election_id).first()
    
    if not election:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot election not found'
        }), 404
    
    # Check required fields
    required_fields = ['positionId', 'candidateId', 'votesReceived']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'message': f'{field} is required'
            }), 400
    
    # Check if position exists
    position = BallotPosition.query.filter_by(id=data['positionId']).first()
    if not position or position.election_id != election_id:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid position ID'
        }), 400
    
    # Check if candidate exists
    candidate = BallotCandidate.query.filter_by(id=data['candidateId']).first()
    if not candidate or candidate.position_id != data['positionId']:
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': 'Invalid candidate ID'
        }), 400
    
    # Check if result already exists
    existing_result = BallotResult.query.filter_by(
        election_id=election_id,
        position_id=data['positionId'],
        candidate_id=data['candidateId']
    ).first()
    
    if existing_result:
        # Update existing result
        existing_result.votes_received = data['votesReceived']
        existing_result.is_elected = data.get('isElected', False)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': existing_result.to_dict(),
            'message': 'Ballot result updated successfully'
        }), 200
    else:
        # Create new result
        new_result = BallotResult(
            id=uuid.uuid4(),
            election_id=election_id,
            position_id=data['positionId'],
            candidate_id=data['candidateId'],
            votes_received=data['votesReceived'],
            is_elected=data.get('isElected', False)
        )
        
        db.session.add(new_result)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': new_result.to_dict(),
            'message': 'Ballot result created successfully'
        }), 201

# Delete ballot result
@ballots_bp.route('/results/<result_id>', methods=['DELETE'])
@token_required
def delete_ballot_result(current_user, result_id):
    result = BallotResult.query.filter_by(id=result_id).first()
    
    if not result:
        return jsonify({
            'success': False,
            'error': 'Not found',
            'message': 'Ballot result not found'
        }), 404
    
    db.session.delete(result)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ballot result deleted successfully'
    }), 200
