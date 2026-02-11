# backend/app/routes/api/__init__.py
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import csrf to exempt sub-blueprints (CSRF exemption doesn't cascade to nested blueprints)
try:
    from app import csrf
except ImportError:
    csrf = None

# Register sub-blueprints with error handling
try:
    from app.routes.api.auth_routes import auth_api_bp
    if csrf:
        csrf.exempt(auth_api_bp)
    api_bp.register_blueprint(auth_api_bp)
except Exception:
    pass

try:
    from app.routes.api.alert_routes import api_alert
    if csrf:
        csrf.exempt(api_alert)
    api_bp.register_blueprint(api_alert)
except Exception:
    pass

try:
    from app.routes.api.admin_stats import admin_stats_api
    if csrf:
        csrf.exempt(admin_stats_api)
    api_bp.register_blueprint(admin_stats_api)
except Exception:
    pass

try:
    from app.routes.api.recording_routes import recording_api_bp
    if csrf:
        csrf.exempt(recording_api_bp)
    api_bp.register_blueprint(recording_api_bp)
except Exception as e:
    print(f"Failed to register recording_api_bp: {e}")
    pass