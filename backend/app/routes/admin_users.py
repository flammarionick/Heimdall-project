# app/routes/admin_users.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.models.user import User
from app import db
from app.forms import UserForm

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
    form = UserForm()

    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data,
            password_hash=generate_password_hash(form.password.data)
        )
        db.session.add(new_user)
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin_users.list_users'))

    return render_template('admin/users/create.html', form=form)

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
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users.list_users'))

    return render_template('admin/users/edit.html', form=form)