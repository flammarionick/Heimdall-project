# backend/app/routes/camera.py
from flask import Blueprint, render_template
from flask_login import login_required

camera_bp = Blueprint('camera', __name__, url_prefix='/cameras')

@camera_bp.route('/')
@login_required
def camera_home():
    return render_template('camera/index.html', title='Camera Management')
