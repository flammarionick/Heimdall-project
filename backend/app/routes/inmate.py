# backend/app/routes/inmate.py
from flask import Blueprint, render_template, redirect, flash, url_for
from flask_login import login_required
from app.forms import InmateForm


inmate_bp = Blueprint('inmate', __name__, url_prefix='/inmates')

@inmate_bp.route('/')
@login_required
def inmate_home():
    return render_template('inmate/index.html', title='Inmate Management')


@inmate_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    form = InmateForm()
    if form.validate_on_submit():
        # You’ll handle saving the inmate later
        flash("Inmate registered successfully", "success")
        return redirect(url_for('inmate.inmate_home'))
    return render_template('inmate/register.html', form=form)