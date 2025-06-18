import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!
from src import create_app
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import datetime
import uuid
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import Flask
from flask_migrate import Migrate
from src.extensions import db





from dotenv import load_dotenv
load_dotenv()


# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USERNAME', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'oirrms')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key')
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(days=1)

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Add this line

# Import models and routes
from src.models.user import User
from src.models.organization import Organization, OrganizationType
from src.models.agreement import Agreement, AgreementType
from src.models.ballot import BallotElection, BallotPosition, BallotCandidate, BallotResult
from src.models.training import TrainingWorkshop, TrainingType, WorkshopParticipant
from src.models.compliance import ComplianceRequirement, ComplianceRecord, Inspection, NonComplianceIssue
from src.models.document import Document, DocumentType
from src.models.notification import Notification, UserNotification
from src.models.region import Region, District

# Import routes
from src.routes.auth import auth_bp
from src.routes.dashboard import dashboard_bp
from src.routes.organizations import organizations_bp
from src.routes.agreements import agreements_bp
from src.routes.ballots import ballots_bp
from src.routes.trainings import trainings_bp
from src.routes.compliance import compliance_bp
from src.routes.documents import documents_bp
from src.routes.users import user_bp      # Assuming users_bp might be in users.py or needs creation
from src.routes.settings import settings_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(organizations_bp, url_prefix='/api/organizations')
app.register_blueprint(agreements_bp, url_prefix='/api/agreements')
app.register_blueprint(ballots_bp, url_prefix='/api/ballots')
app.register_blueprint(trainings_bp, url_prefix='/api/trainings')
app.register_blueprint(compliance_bp, url_prefix='/api/compliance')
app.register_blueprint(documents_bp, url_prefix='/api/documents')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(settings_bp, url_prefix='/api/settings')

# Root route
@app.route('/')
def index():
    return jsonify({
        'message': 'Welcome to the OIR Dashboard API',
        'version': '1.0.0',
        'status': 'running'
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': 'The server could not understand the request'
    }), 400

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(host='0.0.0.0', port=5000, debug=True)
