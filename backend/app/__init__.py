# backend/app/__init__.py
from flask import Flask
from app.extensions import db, login_manager, migrate
from dotenv import load_dotenv
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from flask_socketio import SocketIO


import os

socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    app = Flask(__name__)
    
    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

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
    from .routes.alerts import alerts_bp as alerts_api_bp
    from .routes.settings import settings_bp
    from .routes.api import api_bp
    from app.routes.settings import settings_bp
    from app.routes.api.camera_routes import api_camera
    

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmate_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(alerts_api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_camera)
    
    socketio.init_app(app)
    return app
