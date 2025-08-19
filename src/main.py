import os
import logging
from datetime import timedelta, datetime
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_migrate import Migrate
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = ["DB_USERNAME", "DB_PASSWORD", "DB_HOST", "DB_NAME", "SECRET_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        logger.error(f"Missing required environment variable: {var}")
        raise ValueError(f"Missing required environment variable: {var}")


# Configuration Class
class Config:
    SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    ALLOWED_ORIGINS = [x.strip() for x in
                       os.getenv("ALLOWED_ORIGINS",
                                 "http://localhost:5175,http://127.0.0.1:5175,http://localhost:3000").split(",") if
                       x.strip()]
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "200 per day;50 per hour")
    RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5 per minute")
    RATE_LIMIT_STORAGE_URI = os.getenv("REDIS_URL", "memory://")
    RATE_LIMIT_STORAGE_OPTIONS = {
        "socket_timeout": float(os.getenv("REDIS_TIMEOUT", "0.5")),
        "health_check_interval": 30
    }
    RATE_LIMIT_STRATEGY = "fixed-window"
    # Add explicit configuration for CORS
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_EXPOSE_HEADERS = ["Content-Disposition"]
    CORS_MAX_AGE = 600


def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions from extensions.py
    from src.extensions import db, login_manager, migrate, limiter, cors, talisman

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Enhanced CORS configuration
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": app.config["ALLOWED_ORIGINS"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "X-CSRF-Token"],
                "supports_credentials": True,
                "expose_headers": app.config["CORS_EXPOSE_HEADERS"],
                "max_age": app.config["CORS_MAX_AGE"],
                "vary_header": True
            }
        },
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"]
    )

    # Configure Talisman with more flexible CSP for development
    csp = {
        "default-src": "'self'",
        "connect-src": "'self' " + ' '.join(app.config["ALLOWED_ORIGINS"] + ["ws://localhost:*", "wss://localhost:*"]),
        "img-src": "'self' data: blob:",
        "style-src": "'self' 'unsafe-inline'",
        "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",
        "font-src": "'self' data:"
    }

    force_https_enabled = os.getenv('FLASK_ENV') == 'production'

    talisman.init_app(
        app,
        content_security_policy=csp,
        force_https=force_https_enabled,
        strict_transport_security=force_https_enabled,
        session_cookie_secure=force_https_enabled,
        frame_options='SAMEORIGIN'
    )

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Import models after db initialization
    from src.models.user import User
    from src.models.organization import Organization, OrganizationType
    from src.models.agreement import Agreement, AgreementType
    from src.models.ballot import BallotElection, BallotPosition, BallotCandidate, BallotResult
    from src.models.training import TrainingWorkshop, TrainingType, WorkshopParticipant
    from src.models.compliance import ComplianceRequirement, ComplianceRecord, Inspection, NonComplianceIssue
    from src.models.document import Document, DocumentType
    from src.models.notification import Notification, UserNotification
    from src.models.region import Region, District

    # Import and register blueprints
    from src.routes.auth import auth_bp
    from src.routes.dashboard import dashboard_bp
    from src.routes.organizations import organizations_bp
    from src.routes.agreements import agreements_bp
    from src.routes.ballots import ballots_bp
    from src.routes.trainings_enhanced import trainings_enhanced_bp
    from src.routes.compliance import compliance_bp
    from src.routes.documents import documents_bp
    from src.routes.users_enhanced import users_enhanced_bp
    from src.routes.settings_enhanced import settings_enhanced_bp
    from src.routes.dashboard_extensions import dashboard_ext_bp

    blueprints = [
        (auth_bp, "/api/auth"),
        (dashboard_bp, "/api/dashboard"),
        (dashboard_ext_bp, "/api/dashboard"),
        (organizations_bp, "/api/organizations"),
        (agreements_bp, "/api/agreements"),
        (ballots_bp, "/api/ballots"),
        (trainings_enhanced_bp, "/api/trainings"),
        (compliance_bp, "/api/compliance"),
        (documents_bp, "/api/documents"),
        (users_enhanced_bp, "/api/users"),
        (settings_enhanced_bp, "/api/settings")
    ]

    # Register blueprints
    for bp, url_prefix in blueprints:
        app.register_blueprint(bp, url_prefix=url_prefix)

    # Apply rate limits to auth blueprint
    limiter.limit(app.config["RATE_LIMIT_AUTH"])(auth_bp)

    # Create database tables within application context
    with app.app_context():
        db.create_all()



    @app.route("/")
    def index():
        return jsonify({
            "message": "Welcome to the OIR Dashboard API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv("FLASK_ENV", "development"),
            "allowed_origins": app.config["ALLOWED_ORIGINS"],
            "cors_enabled": True
        })

    @app.route("/api/health")
    def health_check():
        try:
            db.session.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            logger.error(f"Database connection check failed: {str(e)}")
            db_status = "disconnected"

        return jsonify({
            "status": "healthy",
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "database_connection": db_status,
                "active_blueprints": [bp.name for bp in app.blueprints.values()],
                "environment": os.getenv("FLASK_ENV", "development"),
                "cors_enabled": True,
                "allowed_origins": app.config["ALLOWED_ORIGINS"],
                "rate_limits": {
                    "default": app.config["RATE_LIMIT_DEFAULT"],
                    "auth": app.config["RATE_LIMIT_AUTH"]
                }
            }
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 Not Found: {error}")
        return jsonify({
            "success": False,
            "error": "Not found",
            "message": "The requested resource was not found",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.path
        }), 404

    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"400 Bad Request: {error}")
        return jsonify({
            "success": False,
            "error": "Bad request",
            "message": "The server could not understand the request",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.path
        }), 400

    @app.errorhandler(429)
    def ratelimit_error(error):
        logger.warning(f"429 Rate Limit Exceeded: {error}")
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded",
            "message": "Too many requests",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.path
        }), 429

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"500 Server Error: {error}")
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.path
        }), 500

    @app.cli.command("init-db")
    def init_db():
        """Initialize the database."""
        with app.app_context():
            db.create_all()
        logger.info("Database tables created")

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    logger.info(f"Starting server on port {port} (debug={debug})")
    logger.info(f"Allowed CORS origins: {app.config['ALLOWED_ORIGINS']}")
    logger.info(
        f"Rate limit settings: Default={app.config['RATE_LIMIT_DEFAULT']}, Auth={app.config['RATE_LIMIT_AUTH']}")
    app.run(host="0.0.0.0", port=port, debug=debug)