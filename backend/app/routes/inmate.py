# backend/app/routes/inmate.py
from flask import Blueprint, render_template
from flask_login import login_required

inmate_bp = Blueprint('inmate', __name__, url_prefix='/inmates')

@inmate_bp.route('/')
@login_required
def inmate_home():
    return render_template('inmate/index.html', title='Inmate Management')

@inmate_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    return render_template('inmate/register.html')
