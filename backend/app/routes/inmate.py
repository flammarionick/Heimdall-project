# backend/app/routes/inmate.py
from flask import Blueprint, render_template
from flask_login import login_required

inmate_bp = Blueprint('inmate', __name__, url_prefix='/inmates')

@inmate_bp.route('/')
@login_required
def inmate_home():
    return "<h3>Inmate Management Coming Soon</h3>"
