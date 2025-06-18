from flask import Blueprint, request, jsonify
from src.models.election import UnionElection, ElectionNominee, NomineeVerification, ExecutivePosition
from src.extensions import db
from src.utils.auth import token_required, role_required
from datetime import datetime
import json

elections_bp = Blueprint('elections', __name__)

@elections_bp.route('/elections', methods=['GET'])
@token_required
def get_elections():
    """
    Get all elections with optional filtering
    """
    try:
        # Parse query parameters
        year = request.args.get('year', type=int)
        status = request.args.get('status')
        organization_id = request.args.get('organization_id', type=int)
        
        # Base query
        query = UnionElection.query
        
        # Apply filters
        if year:
            query = query.filter(db.extract('year', UnionElection.election_date) == year)
        if status and status != 'all':
            query = query.filter(UnionElection.status == status)
        if organization_id:
            query = query.filter(UnionElection.organization_id == organization_id)
        
        # Execute query
        elections = query.all()
        
        # Format response
        result = {
            'elections': [election.to_dict() for election in elections],
            'monthlyData': get_monthly_election_data(year if year else datetime.now().year)
        }
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections/<int:election_id>', methods=['GET'])
@token_required
def get_election(election_id):
    """
    Get a specific election by ID
    """
    try:
        election = UnionElection.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        return jsonify(election.to_dict(include_nominees=True)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections', methods=['POST'])
@token_required
@role_required(['REGISTRAR', 'DEPUTY_REGISTRAR', 'INSPECTOR'])
def create_election():
    """
    Create a new election
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['organization_id', 'election_date', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create new election
        new_election = UnionElection(
            organization_id=data['organization_id'],
            election_date=datetime.strptime(data['election_date'], '%Y-%m-%d').date(),
            status=data['status'],
            total_eligible_voters=data.get('total_eligible_voters', 0),
            actual_voters=data.get('actual_voters', 0),
            notes=data.get('notes', '')
        )
        
        db.session.add(new_election)
        db.session.commit()
        
        return jsonify(new_election.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections/<int:election_id>', methods=['PUT'])
@token_required
@role_required(['REGISTRAR', 'DEPUTY_REGISTRAR', 'INSPECTOR'])
def update_election(election_id):
    """
    Update an existing election
    """
    try:
        election = UnionElection.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        data = request.json
        
        # Update fields
        if 'election_date' in data:
            election.election_date = datetime.strptime(data['election_date'], '%Y-%m-%d').date()
        if 'status' in data:
            election.status = data['status']
        if 'total_eligible_voters' in data:
            election.total_eligible_voters = data['total_eligible_voters']
        if 'actual_voters' in data:
            election.actual_voters = data['actual_voters']
        if 'notes' in data:
            election.notes = data['notes']
        if 'supervised_by' in data:
            election.supervised_by = data['supervised_by']
        
        election.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify(election.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections/<int:election_id>/nominees', methods=['GET'])
@token_required
def get_election_nominees(election_id):
    """
    Get all nominees for a specific election
    """
    try:
        nominees = ElectionNominee.query.filter_by(election_id=election_id).all()
        
        return jsonify([nominee.to_dict() for nominee in nominees]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections/<int:election_id>/nominees', methods=['POST'])
@token_required
def add_election_nominee(election_id):
    """
    Add a new nominee to an election
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['position_id', 'member_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if election exists
        election = UnionElection.query.get(election_id)
        if not election:
            return jsonify({'error': 'Election not found'}), 404
        
        # Check if nominee already exists
        existing_nominee = ElectionNominee.query.filter_by(
            election_id=election_id,
            position_id=data['position_id'],
            member_id=data['member_id']
        ).first()
        
        if existing_nominee:
            return jsonify({'error': 'Nominee already exists for this position'}), 400
        
        # Create new nominee
        new_nominee = ElectionNominee(
            election_id=election_id,
            position_id=data['position_id'],
            member_id=data['member_id']
        )
        
        db.session.add(new_nominee)
        db.session.commit()
        
        return jsonify(new_nominee.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/nominees/<int:nominee_id>/verify', methods=['POST'])
@token_required
@role_required(['REGISTRAR', 'DEPUTY_REGISTRAR', 'INSPECTOR'])
def verify_nominee(nominee_id):
    """
    Verify a nominee in the verification workflow
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['verification_step', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if nominee exists
        nominee = ElectionNominee.query.get(nominee_id)
        if not nominee:
            return jsonify({'error': 'Nominee not found'}), 404
        
        # Create verification record
        verification = NomineeVerification(
            nominee_id=nominee_id,
            verification_step=data['verification_step'],
            verified_by=data.get('verified_by'),
            status=data['status'],
            comments=data.get('comments', '')
        )
        
        db.session.add(verification)
        db.session.commit()
        
        # Return updated nominee with verification status
        return jsonify(nominee.to_dict(include_verifications=True)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/positions', methods=['GET'])
@token_required
def get_executive_positions():
    """
    Get all executive positions
    """
    try:
        positions = ExecutivePosition.query.filter_by(is_active=True).all()
        
        return jsonify([position.to_dict() for position in positions]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@elections_bp.route('/elections/calculate-quorum', methods=['POST'])
@token_required
def calculate_quorum():
    """
    Calculate if quorum is met for an election
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['total_members', 'present_members']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        total_members = int(data['total_members'])
        present_members = int(data['present_members'])
        required_percentage = float(data.get('required_percentage', 50))
        
        if total_members <= 0:
            return jsonify({
                'error': 'Total members must be greater than zero',
                'is_quorum_met': False,
                'turnout_percentage': 0
            }), 400
        
        if present_members > total_members:
            return jsonify({
                'error': 'Present members cannot exceed total members',
                'is_quorum_met': False,
                'turnout_percentage': 0
            }), 400
        
        # Calculate turnout percentage
        turnout_percentage = (present_members / total_members) * 100
        
        # Check if quorum is met
        is_quorum_met = turnout_percentage >= required_percentage
        
        return jsonify({
            'total_members': total_members,
            'present_members': present_members,
            'required_percentage': required_percentage,
            'turnout_percentage': turnout_percentage,
            'is_quorum_met': is_quorum_met
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_monthly_election_data(year):
    """
    Helper function to get monthly election data for a specific year
    """
    result = []
    
    for month in range(1, 13):
        # Get counts for each status
        completed_count = UnionElection.query.filter(
            db.extract('year', UnionElection.election_date) == year,
            db.extract('month', UnionElection.election_date) == month,
            UnionElection.status == 'completed'
        ).count()
        
        pending_count = UnionElection.query.filter(
            db.extract('year', UnionElection.election_date) == year,
            db.extract('month', UnionElection.election_date) == month,
            UnionElection.status == 'pending'
        ).count()
        
        cancelled_count = UnionElection.query.filter(
            db.extract('year', UnionElection.election_date) == year,
            db.extract('month', UnionElection.election_date) == month,
            UnionElection.status == 'cancelled'
        ).count()
        
        # Add to result
        result.append({
            'month': datetime(year, month, 1).strftime('%b'),
            'completed': completed_count,
            'pending': pending_count,
            'cancelled': cancelled_count
        })
    
    return result
