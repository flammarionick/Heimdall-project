# app/__init__.py
from flask import Flask, redirect, url_for, request, jsonify
from dotenv import load_dotenv
from flask_socketio import SocketIO
from flask_wtf import CSRFProtect
from flask_cors import CORS

from app.extensions import db, login_manager, migrate

csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    app = Flask(__name__)

    # Load environment config
    load_dotenv()
    from .config import DevelopmentConfig
    app.config.from_object(DevelopmentConfig)

    # Secret key (if not already in config)
    app.config.setdefault("SECRET_KEY", "your-super-secret-key")

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # CORS: allow React dev server and send cookies
    CORS(
        app,
        resources={r"/admin/api/*": {"origins": ["http://localhost:5173"]}},
        supports_credentials=True,
    )

    # Blueprints
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
    from app.routes.admin_api import admin_api_bp  # JSON stats API

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

    # Socket.IO events
    from app import socket_events  # noqa: F401

    # Make unauthorized for API return JSON instead of redirecting to HTML
    @login_manager.unauthorized_handler
    def unauthorized():
        # If it's an API call, return JSON so React can handle it
        if request.path.startswith("/admin/api"):
            return jsonify({"error": "unauthorized"}), 401
        return redirect(url_for("auth.login"))

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app