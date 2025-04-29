# backend/app/__init__.py
from flask import Flask
from dotenv import load_dotenv
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect

from app.extensions import db, login_manager, migrate
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert

csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-super-secret-key'

    # Load environment
    load_dotenv()

    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    #csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    socketio.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inmate import inmate_bp
    from app.routes.camera import camera_bp
    from app.routes.alerts import alerts_bp as alerts_api_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp
    from app.routes.api.camera_routes import api_camera
    from app.routes.admin_users import admin_users_bp
    from app.routes.admin.user_admin import admin_user_bp
    from app.routes.recognition_routes import recognition_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_user_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmate_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(alerts_api_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(recognition_bp)
    app.register_blueprint(api_camera)

    from app import socket_events  # 👈 Add this line after blueprints


    return app
