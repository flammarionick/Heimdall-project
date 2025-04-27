# app/routes/admin_users.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.models.user import User
from app import db

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')

def admin_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard.view_dashboard'))
        return func(*args, **kwargs)
    return decorated_view

@admin_users_bp.route('/')
@login_required
@admin_required
def list_users():
    users = User.query.all()
    return render_template('admin/users/list.html', users=users)

@admin_users_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_admin = 'is_admin' in request.form

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=is_admin
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin_users.list_users'))
    return render_template('admin/users/create.html')

@admin_users_bp.route('/suspend/<int:user_id>')
@login_required
@admin_required
def suspend_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_suspended = True
    db.session.commit()
    flash('User suspended.', 'warning')
    return redirect(url_for('admin_users.list_users'))

@admin_users_bp.route('/unsuspend/<int:user_id>')
@login_required
@admin_required
def unsuspend_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_suspended = False
    db.session.commit()
    flash('User unsuspended.', 'success')
    return redirect(url_for('admin_users.list_users'))

@admin_users_bp.route('/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'danger')
    return redirect(url_for('admin_users.list_users'))

@admin_users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users.list_users'))
    
    return render_template('admin/users/edit.html', user=user)
