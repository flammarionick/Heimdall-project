# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.models import Inmate
from app.forms import UploadFaceForm

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

from app.forms import UploadFaceForm  # make sure this is defined correctly

@recognition_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recognition():
    form = UploadFaceForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            file = form.file.data
            if not file:
                flash('No file uploaded.', 'danger')
                return redirect(request.url)

            # TODO: Call your recognition logic here

            matched_inmate = None  # Placeholder

            if matched_inmate:
                flash(f'Match found: {matched_inmate.full_name}', 'success')
            else:
                flash('No match found.', 'warning')

            return redirect(url_for('recognition.upload_recognition'))

    return render_template('recognition/upload.html', form=form)

@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')

