# app/__init__.py
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from app.extensions import db, login_manager, migrate
from app.models.user import User
from app.models.camera import Camera
from app.models.inmate import Inmate
from app.models.alert import Alert
from flask_cors import CORS

# single SocketIO instance (configured later)
socketio = SocketIO()

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    # Basic secret for dev - replace with secure secret in production
    app.config['SECRET_KEY'] = 'your-super-secret-key'

    # Load environment variables (optional .env)
    load_dotenv()

    # Development config object (keeps your existing pattern)
    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    # Session cookie settings to allow cross-origin cookies in dev.
    # NOTE: SESSION_COOKIE_SECURE should be True in production when using HTTPS.
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "None")
    app.config.setdefault("SESSION_COOKIE_SECURE", False)

    # CORS: allow your frontend origin and allow credentials (cookies)
    # Adjust/add origins as needed (e.g. additional dev hosts).
    FRONTEND_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    CORS(
        app,
        resources={
            r"/api/*": {"origins": FRONTEND_ORIGINS},
            r"/admin/*": {"origins": FRONTEND_ORIGINS},
            r"/auth/*": {"origins": FRONTEND_ORIGINS},
            r"/": {"origins": FRONTEND_ORIGINS},
            # Add more routes/patterns if you have other endpoints called from frontend
        },
        supports_credentials=True,
        origins=FRONTEND_ORIGINS,
    )

    # Initialize security + extensions
    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Init SocketIO and allow the frontend origin as well (for sockets)
    socketio.init_app(app, cors_allowed_origins=FRONTEND_ORIGINS)

    # Register blueprints (keep order if some depend on others)
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
    from app.routes.api.user_routes import user_api_bp
    from app.routes.upload_recognition import upload_bp
    from app.routes.admin_api import admin_api_bp

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
    app.register_blueprint(user_api_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_api_bp)

    # Ensure socket events are imported so handlers are registered
    try:
        from app import socket_events  # noqa: F401
    except Exception:
        # non-fatal in case socket_events is missing during some tests
        app.logger.warning("socket_events module missing or failed to import.")

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app