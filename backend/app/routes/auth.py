# app/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models.user import User
from app import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user:
            if user.is_suspended:
                flash('Your account has been suspended. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.suspended'))

            if check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard.view_dashboard'))
            else:
                flash('Invalid password. Please try again.', 'danger')
        else:
            flash('Email not found.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/suspended')
def suspended():
    return render_template('auth/suspended.html')
