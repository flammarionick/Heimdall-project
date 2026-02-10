# app/routes/auth.py
"""
Server-rendered authentication pages (for CSRF-protected form logins).
This is a fallback for traditional server-rendered auth if needed.
The React frontend uses the JSON API in auth_api.py instead.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Server-rendered login page (fallback)."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard.admin_home"))
        return redirect(url_for("dashboard.dashboard_home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_suspended:
                flash("Your account has been suspended.", "error")
                return redirect(url_for("auth.login"))

            login_user(user)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.is_admin:
                return redirect(url_for("admin_dashboard.admin_home"))
            return redirect(url_for("dashboard.dashboard_home"))

        flash("Invalid username or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout and redirect to login page."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
