# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models.user import User
from app.forms import LoginForm
from werkzeug.security import check_password_hash
from app import db, login_manager

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if request.method == 'POST' and form.validate_on_submit():
        print("Form submitted and validated.")

        user = User.query.filter_by(username=form.username.data).first()
        if user:
            print(f"User found: {user.username}")
            if user.check_password(form.password.data):
                print("Password correct.")
                if user.is_suspended:
                    flash('Account suspended. Contact Admin.', 'danger')
                    return redirect(url_for('auth.login'))
                
                login_user(user)
                print("User logged in.")
                flash('Logged in successfully.', 'success')
                return redirect('/dashboard/')
            else:
                print("Password incorrect.")
        else:
            print("User not found.")

    return render_template('auth/login.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
