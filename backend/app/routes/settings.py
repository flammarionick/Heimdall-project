from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models.user import User
from app import db

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        if username:
            current_user.username = username
        if email:
            current_user.email = email

        db.session.commit()
        print("New username:", current_user.username)
        print("New email:", current_user.email)

        flash("Profile updated!", "success")
        return redirect(url_for('settings.settings'))

    return render_template('settings/settings.html')

    
