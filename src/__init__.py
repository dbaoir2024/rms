from flask import Flask
from .extensions import db, login_manager

def create_app(config_class='config.py'):
    app = Flask(__name__)
    app.config.from_pyfile(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app