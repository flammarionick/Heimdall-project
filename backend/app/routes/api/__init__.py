from flask import Blueprint
from .alert_routes import api_alert


api_bp = Blueprint('api', __name__)
api_bp.register_blueprint(api_alert)



# Import all your route modules so they register with this blueprint
from . import camera_routes  # Add other route modules like alert_routes here if needed
