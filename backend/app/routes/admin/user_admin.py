from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models.user import User
from app import db
from flask_login import login_required, current_user
from app.utils.auth_helpers import login_or_jwt_required


admin_user_bp = Blueprint('admin_user', __name__, url_prefix='/admin/users')

@admin_user_bp.route('/')
@login_or_jwt_required
def list_users():
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('dashboard.view_dashboard'))
    users = User.query.all()
    return render_template('admin/users/list.html', users=users)

@admin_user_bp.route('/create', methods=['GET', 'POST'])
@login_or_jwt_required
def create_user():
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('dashboard.view_dashboard'))
    if request.method == 'POST':
        # get data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        # create user
        user = User(username=username, email=email, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('User created successfully!')
        return redirect(url_for('admin_user.list_users'))
    return render_template('admin/users/create.html')

@admin_user_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_or_jwt_required
def edit_user(id):
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('dashboard.view_dashboard'))
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        user.suspended = bool(request.form.get('suspended'))

        db.session.commit()
        flash('User updated successfully.')
        return redirect(url_for('admin_user.list_users'))
    return render_template('admin/users/edit.html', user=user)

@admin_user_bp.route('/<int:id>/toggle-suspend', methods=['POST'])
@login_or_jwt_required
def toggle_suspend_user(id):
    if not current_user.is_admin():
        flash('Access denied.')
        return redirect(url_for('dashboard.view_dashboard'))
    user = User.query.get_or_404(id)
    user.suspended = not user.suspended
    db.session.commit()
    flash('User suspension toggled.')
    return redirect(url_for('admin_user.list_users'))
