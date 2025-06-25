from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from app.extensions import db, login_manager, migrate
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from flask_cors import CORS  # ✅ OK to keep at top
from flask_socketio import SocketIO


csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-super-secret-key'

    # ✅ Move CORS init here after app is created
    CORS(app)  

    # Load environment
    load_dotenv()

    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    socketio.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.inmate import inmate_bp
    from app.routes.camera import camera_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp
    from app.routes.api.camera_routes import api_camera
    from app.routes.admin_users import admin_users_bp
    from app.routes.admin.user_admin import admin_user_bp
    from app.routes.recognition import recognition_bp
    from app.routes.recognition_api import recognition_api_bp
    from app.routes.alerts import alerts_api_bp, alerts_page_bp
    from app.routes.admin_dashboard import admin_dashboard_bp
    from app.routes.api_auth import api_auth_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_auth_bp)
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
    app.register_blueprint(alerts_page_bp)
    app.register_blueprint(recognition_api_bp)
    app.register_blueprint(admin_dashboard_bp)

    from app import socket_events  # Required for Socket.IO events

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app
