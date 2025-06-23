# backend/app/routes/api/__init__.py
from flask import Blueprint
from app.routes.api.auth_routes import auth_api_bp
from app.routes.api.alert_routes import api_alert
from .admin_stats import admin_stats_api


api_bp = Blueprint('api', __name__)
api_bp.register_blueprint(auth_api_bp)
api_bp.register_blueprint(api_alert)
api_bp.register_blueprint(admin_stats_api)