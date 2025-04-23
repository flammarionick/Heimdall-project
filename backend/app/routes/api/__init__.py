from flask import Blueprint

# Create the API blueprint
api_bp = Blueprint('api', __name__)

# Import all your route modules so they register with this blueprint
from . import camera_routes  # Add other route modules like alert_routes here if needed
