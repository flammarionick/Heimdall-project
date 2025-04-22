# backend/app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    load_dotenv()
    app = Flask(__name__)
    
    # Load configuration
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        from .config import ProductionConfig as Config
    else:
        from .config import DevelopmentConfig as Config
    
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.inmate import inmate_bp
    from .routes.camera import camera_bp
    from .routes.alerts import alerts_bp
    from .routes.settings import settings_bp
    from .routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmate_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)

    return app
