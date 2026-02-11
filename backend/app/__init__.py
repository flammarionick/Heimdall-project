# app/__init__.py
import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, url_for
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect

from app.extensions import db, login_manager, migrate

# Make these importable as: `from app import csrf, socketio`
csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    load_dotenv()

    app = Flask(__name__)

    # Disable strict slashes globally to prevent redirect issues with CORS
    app.url_map.strict_slashes = False

    # ─────────────────────────────────────────────
    # Core config
    # ─────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret")

    # Session cookies for local dev (React on 5173, Flask on 5000)
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
    app.config["REMEMBER_COOKIE_SECURE"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Load config from config.py
    try:
        from app.config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    except Exception:
        pass

    # ─────────────────────────────────────────────
    # CORS (for API endpoints called by React)
    # ─────────────────────────────────────────────
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/auth/api/*": {"origins": ["http://localhost:5173"]},
            r"/admin/api/*": {"origins": ["http://localhost:5173"]},
            r"/api/*": {"origins": ["http://localhost:5173"]},
            r"/socket.io/*": {"origins": ["http://localhost:5173"]},
        },
    )

    # ─────────────────────────────────────────────
    # Extensions
    # ─────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    socketio.init_app(app)

    # ─────────────────────────────────────────────
    # Flask-Login: API routes return JSON, not redirect
    # ─────────────────────────────────────────────
    @login_manager.unauthorized_handler
    def unauthorized():
        path = request.path or ""
        if path.startswith(("/auth/api", "/admin/api", "/api")):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(url_for("auth.login"))

    # ─────────────────────────────────────────────
    # Register blueprints
    # ─────────────────────────────────────────────

    # Auth API (JSON endpoints for React) - CSRF exempt
    from app.routes.auth_api import auth_api_bp
    csrf.exempt(auth_api_bp)
    app.register_blueprint(auth_api_bp)

    # Auth pages (server-rendered, CSRF protected)
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # Admin API (JSON endpoints) - CSRF exempt
    from app.routes.admin_api import admin_api_bp
    csrf.exempt(admin_api_bp)
    app.register_blueprint(admin_api_bp)

    # Register remaining blueprints with error handling
    blueprints_to_register = [
        ("app.routes.dashboard", "dashboard_bp", False),
        ("app.routes.inmate", "inmate_bp", False),
        ("app.routes.camera", "camera_bp", False),
        ("app.routes.settings", "settings_bp", False),
        ("app.routes.api", "api_bp", True),
        ("app.routes.api.camera_routes", "api_camera", True),
        ("app.routes.api.user_dashboard", "user_dashboard_bp", True),  # User dashboard API
        ("app.routes.admin_users", "admin_users_bp", False),
        ("app.routes.admin.user_admin", "admin_user_bp", False),
        ("app.routes.recognition", "recognition_bp", False),
        ("app.routes.recognition_api", "recognition_api_bp", True),
        ("app.routes.alerts", "alerts_api_bp", True),
        ("app.routes.alerts", "alerts_page_bp", False),
        ("app.routes.admin_dashboard", "admin_dashboard_bp", False),
        ("app.routes.api.user_routes", "user_api_bp", True),
        ("app.routes.upload_recognition", "upload_bp", True),
    ]

    for module_path, bp_name, should_exempt_csrf in blueprints_to_register:
        try:
            mod = __import__(module_path, fromlist=[bp_name])
            bp = getattr(mod, bp_name)
            if should_exempt_csrf:
                csrf.exempt(bp)
            app.register_blueprint(bp)
        except Exception as e:
            # Log but continue during development
            app.logger.warning(f"Could not register blueprint {bp_name}: {e}")

    # ─────────────────────────────────────────────
    # Socket.IO events
    # ─────────────────────────────────────────────
    try:
        from app import socket_events  # noqa: F401
    except Exception:
        pass

    # ─────────────────────────────────────────────
    # Create database tables if they don't exist
    # ─────────────────────────────────────────────
    with app.app_context():
        # Import models to ensure they're registered
        from app.models import User, Inmate, Camera, Alert, Match, FacialEmbedding  # noqa: F401

        # Create instance folder if it doesn't exist
        instance_path = os.path.join(os.path.dirname(__file__), '..', 'instance')
        os.makedirs(instance_path, exist_ok=True)

        # Create tables
        db.create_all()

    # ─────────────────────────────────────────────
    # Root route
    # ─────────────────────────────────────────────
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app
