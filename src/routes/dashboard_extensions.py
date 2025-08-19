from flask import Blueprint, request, jsonify
from src.routes.auth import token_required
from src.models.organization import Organization
from src.models.agreement import Agreement
from src.models.ballot import BallotElection
from src.models.training import TrainingWorkshop
from src.models.compliance import ComplianceRecord
from src.extensions import db

dashboard_ext_bp = Blueprint('dashboard_ext', __name__)

@dashboard_ext_bp.route('/organization-compliance', methods=['GET'])
@token_required
def get_organization_compliance(current_user):
    # This endpoint will leverage the organization_compliance_summary_view
    # Assuming the view is accessible via SQLAlchemy model or raw SQL
    # For simplicity, let's mock the data or query directly if a model for view exists
    # In a real scenario, you'd query the view directly or through a mapped model
    
    # Example: Querying a simplified version or directly from tables if view model is not ready
    # This is a placeholder, actual implementation would query the view
    organizations_data = db.session.execute(
        "SELECT organization_name, is_compliant FROM organizations"
    ).fetchall()
    
    # Transform data for frontend
    result = [{
        'organizationName': org.organization_name,
        'isCompliant': org.is_compliant
    } for org in organizations_data]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Organization compliance data retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/upcoming-agreement-renewals', methods=['GET'])
@token_required
def get_upcoming_agreement_renewals(current_user):
    # This endpoint will leverage the upcoming_agreement_expirations_view
    # For simplicity, querying directly from agreements table for now
    upcoming_agreements = Agreement.query.filter(
        Agreement.expiry_date.between(db.func.current_date(), db.func.current_date() + db.text('interval \'90 days\''))
    ).all()

    result = [{
        'id': str(agreement.id),
        'agreementName': agreement.agreement_name,
        'expiryDate': agreement.expiry_date.isoformat()
    } for agreement in upcoming_agreements]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Upcoming agreement renewals retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/upcoming-ballots', methods=['GET'])
@token_required
def get_upcoming_ballots(current_user):
    # This endpoint will leverage the pending_ballot_elections_view
    # For simplicity, querying directly from ballot_elections table for now
    upcoming_ballots = BallotElection.query.filter(
        BallotElection.election_date.between(db.func.current_date(), db.func.current_date() + db.text('interval \'90 days\''))
    ).all()

    result = [{
        'id': str(ballot.id),
        'electionNumber': ballot.election_number,
        'electionDate': ballot.election_date.isoformat()
    } for ballot in upcoming_ballots]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Upcoming ballots retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/upcoming-trainings', methods=['GET'])
@token_required
def get_upcoming_trainings(current_user):
    # This endpoint will leverage the upcoming_training_workshops_view
    # For simplicity, querying directly from training_workshops table for now
    upcoming_trainings = TrainingWorkshop.query.filter(
        TrainingWorkshop.workshop_date >= db.func.current_date()
    ).all()

    result = [{
        'id': str(training.id),
        'workshopName': training.workshop_name,
        'workshopDate': training.workshop_date.isoformat()
    } for training in upcoming_trainings]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Upcoming trainings retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/organization-growth', methods=['GET'])
@token_required
def get_organization_growth(current_user):
    # This endpoint will leverage the union_growth_by_year_view
    # For simplicity, querying directly from organizations table for now
    growth_data = db.session.execute(
        "SELECT EXTRACT(YEAR FROM registration_date) as year, COUNT(*) as count FROM organizations GROUP BY year ORDER BY year"
    ).fetchall()

    result = [{
        'year': int(row.year),
        'count': int(row.count)
    } for row in growth_data]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Organization growth data retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/dispute-resolution', methods=['GET'])
@token_required
def get_dispute_resolution(current_user):
    # This endpoint will leverage the dispute_resolution_summary_view
    # For simplicity, querying directly from dispute_resolutions table for now
    dispute_data = db.session.execute(
        "SELECT status, COUNT(*) as count FROM dispute_resolutions GROUP BY status"
    ).fetchall()

    result = [{
        'status': row.status,
        'count': int(row.count)
    } for row in dispute_data]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Dispute resolution data retrieved successfully'
    }), 200

@dashboard_ext_bp.route('/geo-distribution', methods=['GET'])
@token_required
def get_geo_distribution(current_user):
    # This endpoint will leverage the union_geographic_distribution_view
    # For simplicity, querying directly from organizations and districts/regions for now
    geo_data = db.session.execute(
        """SELECT r.region_name, d.district_name, COUNT(o.id) as count
           FROM organizations o
           JOIN districts d ON o.district_id = d.id
           JOIN regions r ON d.region_id = r.id
           GROUP BY r.region_name, d.district_name
           ORDER BY r.region_name, d.district_name"""
    ).fetchall()

    result = [{
        'region': row.region_name,
        'district': row.district_name,
        'count': int(row.count)
    } for row in geo_data]

    return jsonify({
        'success': True,
        'data': result,
        'message': 'Geographic distribution data retrieved successfully'
    }), 200


