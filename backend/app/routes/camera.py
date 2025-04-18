from flask import Blueprint
from flask_login import login_required

camera_bp = Blueprint('camera', __name__, url_prefix='/cameras')

@camera_bp.route('/')
@login_required
def camera_home():
    return "<h3>Camera Management Coming Soon</h3>"