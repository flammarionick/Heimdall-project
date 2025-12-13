# app/__init__.py

import os
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, jsonify, request
from flask_wtf import CSRFProtect
from flask_socketio import SocketIO
from flask_cors import CORS

from app.extensions import db, login_manager, migrate

csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your-super-secret-key")

    # Config object
    from .config import DevelopmentConfig

    app.config.from_object(DevelopmentConfig)

    # For local dev, make cookies usable from the React app
    # (adjust these for production / HTTPS)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    # If you later decide to do true cross-site cookies, you can move to:
    #   SESSION_COOKIE_SAMESITE = "None"
    #   SESSION_COOKIE_SECURE = True   (with HTTPS)

    # Allow React frontend to call Flask API with cookies
    CORS(
        app,
        supports_credentials=True,
        resources={
            # API auth endpoints used by React: /auth/api/login, /auth/api/me, /auth/api/logout
            r"/auth/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"]
            },
            # Admin JSON API for dashboard + user management
            r"/admin/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"]
            },
            # Any other JSON APIs you expose under /api/...
            r"/api/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"]
            },
        },
    )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    socketio.init_app(app)

    # Return JSON 401 for API calls instead of redirecting the frontend
    @login_manager.unauthorized_handler
    def unauthorized():
        path = request.path or ""

        # For XHR / fetch calls, return JSON
        if path.startswith("/auth/api") or path.startswith("/admin/api") or path.startswith(
            "/api"
        ):
            return jsonify({"error": "Unauthorized"}), 401

        # For normal page views, keep redirect behaviour
        return redirect(url_for("auth.login"))

    # ---- Register Blueprints ----
    from app.routes.auth import auth_bp
    from app.routes.api_auth import api_auth_bp
    from app.routes.admin_api import admin_api_bp
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
    from app.routes.api.user_routes import user_api_bp
    from app.routes.upload_recognition import upload_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_auth_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(admin_user_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inmate_bp)
    app.register_blueprint(camera_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_camera)
    app.register_blueprint(recognition_bp)
    app.register_blueprint(recognition_api_bp)
    app.register_blueprint(alerts_api_bp)
    app.register_blueprint(alerts_page_bp)
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(user_api_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(admin_api_bp)

    # Load Socket.IO handlers
    from app import socket_events  # noqa

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app