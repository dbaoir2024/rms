from flask import Blueprint, request, jsonify
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
import calendar

from src.extensions import db
from src.models.organization import Organization, OrganizationType
from src.models.agreement import Agreement
from src.models.ballot import BallotElection
from src.models.training import TrainingWorkshop, WorkshopParticipant
from src.models.compliance import ComplianceRecord, Inspection, NonComplianceIssue
from src.models.region import Region, District
from src.routes.auth import token_required

dashboard_bp = Blueprint('dashboard', __name__)

# Get dashboard summary statistics
@dashboard_bp.route('/summary', methods=['GET'])
@token_required
def get_dashboard_summary(current_user):
    # Get total counts
    total_organizations = Organization.query.count()
    total_agreements = Agreement.query.count()
    total_elections = BallotElection.query.count()
    total_workshops = TrainingWorkshop.query.count()
    
    # Get active counts
    active_organizations = Organization.query.filter_by(status='active').count()
    active_agreements = Agreement.query.filter_by(status='active').count()
    upcoming_elections = BallotElection.query.filter(
        BallotElection.status.in_(['scheduled']),
        BallotElection.election_date > datetime.utcnow().date()
    ).count()
    upcoming_workshops = TrainingWorkshop.query.filter(
        TrainingWorkshop.status.in_(['scheduled']),
        TrainingWorkshop.start_date > datetime.utcnow().date()
    ).count()
    
    # Get compliance statistics
    compliant_orgs = Organization.query.filter_by(is_compliant=True).count()
    non_compliant_orgs = total_organizations - compliant_orgs
    
    # Get pending items
    pending_compliance = ComplianceRecord.query.filter(
        ComplianceRecord.status.in_(['pending', 'overdue']),
        ComplianceRecord.due_date <= (datetime.utcnow() + timedelta(days=30)).date()
    ).count()
    
    # Get recent non-compliance issues
    recent_issues = NonComplianceIssue.query.filter(
        NonComplianceIssue.status.in_(['open', 'in_progress']),
        NonComplianceIssue.issue_date >= (datetime.utcnow() - timedelta(days=30)).date()
    ).count()
    
    return jsonify({
        'success': True,
        'data': {
            'organizations': {
                'total': total_organizations,
                'active': active_organizations,
                'compliant': compliant_orgs,
                'nonCompliant': non_compliant_orgs
            },
            'agreements': {
                'total': total_agreements,
                'active': active_agreements
            },
            'elections': {
                'total': total_elections,
                'upcoming': upcoming_elections
            },
            'workshops': {
                'total': total_workshops,
                'upcoming': upcoming_workshops
            },
            'compliance': {
                'pendingSubmissions': pending_compliance,
                'recentIssues': recent_issues
            }
        },
        'message': 'Dashboard summary retrieved successfully'
    }), 200

# Get upcoming deadlines
@dashboard_bp.route('/deadlines', methods=['GET'])
@token_required
def get_upcoming_deadlines(current_user):
    # Get query parameters
    days = request.args.get('days', 30, type=int)
    
    # Calculate date range
    today = datetime.utcnow().date()
    end_date = today + timedelta(days=days)
    
    # Get upcoming compliance deadlines
    compliance_deadlines = ComplianceRecord.query.filter(
        ComplianceRecord.due_date.between(today, end_date),
        ComplianceRecord.status.in_(['pending', 'overdue'])
    ).order_by(ComplianceRecord.due_date).all()
    
    # Get upcoming agreement expirations
    agreement_expirations = Agreement.query.filter(
        Agreement.expiry_date.between(today, end_date),
        Agreement.status == 'active'
    ).order_by(Agreement.expiry_date).all()
    
    # Get upcoming elections
    upcoming_elections = BallotElection.query.filter(
        BallotElection.election_date.between(today, end_date),
        BallotElection.status == 'scheduled'
    ).order_by(BallotElection.election_date).all()
    
    # Get upcoming workshops
    upcoming_workshops = TrainingWorkshop.query.filter(
        TrainingWorkshop.start_date.between(today, end_date),
        TrainingWorkshop.status == 'scheduled'
    ).order_by(TrainingWorkshop.start_date).all()
    
    # Get upcoming non-compliance resolution deadlines
    issue_deadlines = NonComplianceIssue.query.filter(
        NonComplianceIssue.resolution_deadline.between(today, end_date),
        NonComplianceIssue.status.in_(['open', 'in_progress'])
    ).order_by(NonComplianceIssue.resolution_deadline).all()
    
    # Combine all deadlines into a single list
    all_deadlines = []
    
    for record in compliance_deadlines:
        organization = Organization.query.get(record.organization_id)
        all_deadlines.append({
            'type': 'compliance',
            'id': str(record.id),
            'date': record.due_date.isoformat(),
            'title': f"Compliance submission due for {organization.organization_name if organization else 'Unknown'}",
            'status': record.status,
            'entityId': str(record.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for agreement in agreement_expirations:
        organization = Organization.query.get(agreement.primary_organization_id)
        all_deadlines.append({
            'type': 'agreement',
            'id': str(agreement.id),
            'date': agreement.expiry_date.isoformat(),
            'title': f"Agreement {agreement.agreement_number} expires",
            'status': agreement.status,
            'entityId': str(agreement.primary_organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for election in upcoming_elections:
        organization = Organization.query.get(election.organization_id)
        all_deadlines.append({
            'type': 'election',
            'id': str(election.id),
            'date': election.election_date.isoformat(),
            'title': f"Ballot election for {organization.organization_name if organization else 'Unknown'}",
            'status': election.status,
            'entityId': str(election.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for workshop in upcoming_workshops:
        all_deadlines.append({
            'type': 'workshop',
            'id': str(workshop.id),
            'date': workshop.start_date.isoformat(),
            'title': f"Training workshop: {workshop.workshop_name}",
            'status': workshop.status,
            'entityId': None,
            'entityName': workshop.workshop_name
        })
    
    for issue in issue_deadlines:
        organization = Organization.query.get(issue.organization_id)
        all_deadlines.append({
            'type': 'issue',
            'id': str(issue.id),
            'date': issue.resolution_deadline.isoformat(),
            'title': f"Non-compliance resolution deadline for {organization.organization_name if organization else 'Unknown'}",
            'status': issue.status,
            'entityId': str(issue.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    # Sort by date
    all_deadlines.sort(key=lambda x: x['date'])
    
    return jsonify({
        'success': True,
        'data': all_deadlines,
        'message': 'Upcoming deadlines retrieved successfully'
    }), 200

# Get organization statistics
@dashboard_bp.route('/organizations/stats', methods=['GET'])
@token_required
def get_organization_stats(current_user):
    # Get organizations by type
    org_by_type = db.session.query(
        OrganizationType.type_name,
        func.count(Organization.id)
    ).join(
        Organization,
        Organization.organization_type_id == OrganizationType.id
    ).group_by(
        OrganizationType.type_name
    ).all()
    
    # Get organizations by status
    org_by_status = db.session.query(
        Organization.status,
        func.count(Organization.id)
    ).group_by(
        Organization.status
    ).all()
    
    # Get organizations by region
    org_by_region = db.session.query(
        Region.region_name,
        func.count(Organization.id)
    ).join(
        District,
        District.id == Organization.district_id
    ).join(
        Region,
        Region.id == District.region_id
    ).group_by(
        Region.region_name
    ).all()
    
    # Get organizations by compliance status
    org_by_compliance = db.session.query(
        Organization.is_compliant,
        func.count(Organization.id)
    ).group_by(
        Organization.is_compliant
    ).all()
    
    # Format results
    types_data = [{'name': t[0], 'count': t[1]} for t in org_by_type]
    status_data = [{'name': s[0], 'count': s[1]} for s in org_by_status]
    region_data = [{'name': r[0], 'count': r[1]} for r in org_by_region]
    compliance_data = [
        {'name': 'Compliant', 'count': next((c[1] for c in org_by_compliance if c[0] is True), 0)},
        {'name': 'Non-Compliant', 'count': next((c[1] for c in org_by_compliance if c[0] is False), 0)}
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'byType': types_data,
            'byStatus': status_data,
            'byRegion': region_data,
            'byCompliance': compliance_data
        },
        'message': 'Organization statistics retrieved successfully'
    }), 200

# Get agreement statistics
@dashboard_bp.route('/agreements/stats', methods=['GET'])
@token_required
def get_agreement_stats(current_user):
    # Get current date
    today = datetime.utcnow().date()
    
    # Get agreements by status
    agreements_by_status = db.session.query(
        Agreement.status,
        func.count(Agreement.id)
    ).group_by(
        Agreement.status
    ).all()
    
    # Get agreements expiring in next 30, 60, 90 days
    expiring_30 = Agreement.query.filter(
        Agreement.expiry_date.between(today, today + timedelta(days=30)),
        Agreement.status == 'active'
    ).count()
    
    expiring_60 = Agreement.query.filter(
        Agreement.expiry_date.between(today + timedelta(days=31), today + timedelta(days=60)),
        Agreement.status == 'active'
    ).count()
    
    expiring_90 = Agreement.query.filter(
        Agreement.expiry_date.between(today + timedelta(days=61), today + timedelta(days=90)),
        Agreement.status == 'active'
    ).count()
    
    # Get agreements by month (for current year)
    current_year = today.year
    agreements_by_month = []
    
    for month in range(1, 13):
        month_start = datetime(current_year, month, 1).date()
        month_end = datetime(current_year, month, calendar.monthrange(current_year, month)[1]).date()
        
        count = Agreement.query.filter(
            Agreement.effective_date.between(month_start, month_end)
        ).count()
        
        agreements_by_month.append({
            'month': calendar.month_name[month],
            'count': count
        })
    
    # Format results
    status_data = [{'name': s[0], 'count': s[1]} for s in agreements_by_status]
    expiry_data = [
        {'name': '0-30 days', 'count': expiring_30},
        {'name': '31-60 days', 'count': expiring_60},
        {'name': '61-90 days', 'count': expiring_90}
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'byStatus': status_data,
            'byExpiryPeriod': expiry_data,
            'byMonth': agreements_by_month
        },
        'message': 'Agreement statistics retrieved successfully'
    }), 200

# Get compliance statistics
@dashboard_bp.route('/compliance/stats', methods=['GET'])
@token_required
def get_compliance_stats(current_user):
    # Get current date
    today = datetime.utcnow().date()
    
    # Get compliance records by status
    compliance_by_status = db.session.query(
        ComplianceRecord.status,
        func.count(ComplianceRecord.id)
    ).group_by(
        ComplianceRecord.status
    ).all()
    
    # Get non-compliance issues by status
    issues_by_status = db.session.query(
        NonComplianceIssue.status,
        func.count(NonComplianceIssue.id)
    ).group_by(
        NonComplianceIssue.status
    ).all()
    
    # Get non-compliance issues by severity
    issues_by_severity = db.session.query(
        NonComplianceIssue.severity,
        func.count(NonComplianceIssue.id)
    ).group_by(
        NonComplianceIssue.severity
    ).all()
    
    # Get inspections by month (for current year)
    current_year = today.year
    inspections_by_month = []
    
    for month in range(1, 13):
        month_start = datetime(current_year, month, 1).date()
        month_end = datetime(current_year, month, calendar.monthrange(current_year, month)[1]).date()
        
        count = Inspection.query.filter(
            Inspection.inspection_date.between(month_start, month_end)
        ).count()
        
        inspections_by_month.append({
            'month': calendar.month_name[month],
            'count': count
        })
    
    # Format results
    compliance_status_data = [{'name': s[0], 'count': s[1]} for s in compliance_by_status]
    issues_status_data = [{'name': s[0], 'count': s[1]} for s in issues_by_status]
    issues_severity_data = [{'name': s[0], 'count': s[1]} for s in issues_by_severity]
    
    return jsonify({
        'success': True,
        'data': {
            'complianceByStatus': compliance_status_data,
            'issuesByStatus': issues_status_data,
            'issuesBySeverity': issues_severity_data,
            'inspectionsByMonth': inspections_by_month
        },
        'message': 'Compliance statistics retrieved successfully'
    }), 200

# Get training statistics
@dashboard_bp.route('/trainings/stats', methods=['GET'])
@token_required
def get_training_stats(current_user):
    # Get current date
    today = datetime.utcnow().date()
    
    # Get workshops by status
    workshops_by_status = db.session.query(
        TrainingWorkshop.status,
        func.count(TrainingWorkshop.id)
    ).group_by(
        TrainingWorkshop.status
    ).all()
    
    # Get workshops by month (for current year)
    current_year = today.year
    workshops_by_month = []
    
    for month in range(1, 13):
        month_start = datetime(current_year, month, 1).date()
        month_end = datetime(current_year, month, calendar.monthrange(current_year, month)[1]).date()
        
        count = TrainingWorkshop.query.filter(
            TrainingWorkshop.start_date.between(month_start, month_end)
        ).count()
        
        workshops_by_month.append({
            'month': calendar.month_name[month],
            'count': count
        })
    
    # Get participant statistics
    total_participants = WorkshopParticipant.query.count()
    
    attendance_stats = db.session.query(
        WorkshopParticipant.attendance_status,
        func.count(WorkshopParticipant.id)
    ).group_by(
        WorkshopParticipant.attendance_status
    ).all()
    
    # Format results
    status_data = [{'name': s[0], 'count': s[1]} for s in workshops_by_status]
    attendance_data = [{'name': a[0], 'count': a[1]} for a in attendance_stats]
    
    return jsonify({
        'success': True,
        'data': {
            'byStatus': status_data,
            'byMonth': workshops_by_month,
            'participants': {
                'total': total_participants,
                'byAttendance': attendance_data
            }
        },
        'message': 'Training statistics retrieved successfully'
    }), 200

# Get ballot election statistics
@dashboard_bp.route('/elections/stats', methods=['GET'])
@token_required
def get_election_stats(current_user):
    # Get current date
    today = datetime.utcnow().date()
    
    # Get elections by status
    elections_by_status = db.session.query(
        BallotElection.status,
        func.count(BallotElection.id)
    ).group_by(
        BallotElection.status
    ).all()
    
    # Get elections by month (for current year)
    current_year = today.year
    elections_by_month = []
    
    for month in range(1, 13):
        month_start = datetime(current_year, month, 1).date()
        month_end = datetime(current_year, month, calendar.monthrange(current_year, month)[1]).date()
        
        count = BallotElection.query.filter(
            BallotElection.election_date.between(month_start, month_end)
        ).count()
        
        elections_by_month.append({
            'month': calendar.month_name[month],
            'count': count
        })
    
    # Format results
    status_data = [{'name': s[0], 'count': s[1]} for s in elections_by_status]
    
    return jsonify({
        'success': True,
        'data': {
            'byStatus': status_data,
            'byMonth': elections_by_month
        },
        'message': 'Election statistics retrieved successfully'
    }), 200

# Get recent activities
@dashboard_bp.route('/activities', methods=['GET'])
@token_required
def get_recent_activities(current_user):
    # Get query parameters
    days = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # Calculate date range
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days)
    
    # Get recent organizations
    recent_orgs = Organization.query.filter(
        Organization.created_at >= start_date
    ).order_by(
        Organization.created_at.desc()
    ).limit(limit).all()
    
    # Get recent agreements
    recent_agreements = Agreement.query.filter(
        Agreement.created_at >= start_date
    ).order_by(
        Agreement.created_at.desc()
    ).limit(limit).all()
    
    # Get recent elections
    recent_elections = BallotElection.query.filter(
        BallotElection.created_at >= start_date
    ).order_by(
        BallotElection.created_at.desc()
    ).limit(limit).all()
    
    # Get recent workshops
    recent_workshops = TrainingWorkshop.query.filter(
        TrainingWorkshop.created_at >= start_date
    ).order_by(
        TrainingWorkshop.created_at.desc()
    ).limit(limit).all()
    
    # Get recent compliance records
    recent_compliance = ComplianceRecord.query.filter(
        ComplianceRecord.created_at >= start_date
    ).order_by(
        ComplianceRecord.created_at.desc()
    ).limit(limit).all()
    
    # Get recent inspections
    recent_inspections = Inspection.query.filter(
        Inspection.created_at >= start_date
    ).order_by(
        Inspection.created_at.desc()
    ).limit(limit).all()
    
    # Get recent non-compliance issues
    recent_issues = NonComplianceIssue.query.filter(
        NonComplianceIssue.created_at >= start_date
    ).order_by(
        NonComplianceIssue.created_at.desc()
    ).limit(limit).all()
    
    # Combine all activities
    all_activities = []
    
    for org in recent_orgs:
        all_activities.append({
            'type': 'organization',
            'id': str(org.id),
            'date': org.created_at.isoformat(),
            'title': f"New organization registered: {org.organization_name}",
            'status': org.status,
            'entityId': str(org.id),
            'entityName': org.organization_name
        })
    
    for agreement in recent_agreements:
        organization = Organization.query.get(agreement.primary_organization_id)
        all_activities.append({
            'type': 'agreement',
            'id': str(agreement.id),
            'date': agreement.created_at.isoformat(),
            'title': f"New agreement registered: {agreement.agreement_number}",
            'status': agreement.status,
            'entityId': str(agreement.primary_organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for election in recent_elections:
        organization = Organization.query.get(election.organization_id)
        all_activities.append({
            'type': 'election',
            'id': str(election.id),
            'date': election.created_at.isoformat(),
            'title': f"New ballot election scheduled for {organization.organization_name if organization else 'Unknown'}",
            'status': election.status,
            'entityId': str(election.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for workshop in recent_workshops:
        all_activities.append({
            'type': 'workshop',
            'id': str(workshop.id),
            'date': workshop.created_at.isoformat(),
            'title': f"New training workshop scheduled: {workshop.workshop_name}",
            'status': workshop.status,
            'entityId': None,
            'entityName': workshop.workshop_name
        })
    
    for record in recent_compliance:
        organization = Organization.query.get(record.organization_id)
        all_activities.append({
            'type': 'compliance',
            'id': str(record.id),
            'date': record.created_at.isoformat(),
            'title': f"New compliance record for {organization.organization_name if organization else 'Unknown'}",
            'status': record.status,
            'entityId': str(record.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for inspection in recent_inspections:
        organization = Organization.query.get(inspection.organization_id)
        all_activities.append({
            'type': 'inspection',
            'id': str(inspection.id),
            'date': inspection.created_at.isoformat(),
            'title': f"New inspection for {organization.organization_name if organization else 'Unknown'}",
            'status': inspection.status,
            'entityId': str(inspection.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    for issue in recent_issues:
        organization = Organization.query.get(issue.organization_id)
        all_activities.append({
            'type': 'issue',
            'id': str(issue.id),
            'date': issue.created_at.isoformat(),
            'title': f"New non-compliance issue for {organization.organization_name if organization else 'Unknown'}",
            'status': issue.status,
            'entityId': str(issue.organization_id),
            'entityName': organization.organization_name if organization else 'Unknown'
        })
    
    # Sort by date (newest first)
    all_activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Limit to requested number
    all_activities = all_activities[:limit]
    
    return jsonify({
        'success': True,
        'data': all_activities,
        'message': 'Recent activities retrieved successfully'
    }), 200
