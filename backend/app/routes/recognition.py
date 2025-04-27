# app/routes/recognition.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app.models import Inmate

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

@recognition_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recognition():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)
        
        # TODO: Call the facial recognition function here with file
        matched_inmate = None  # Placeholder (later integrate real model)
        
        if matched_inmate:
            flash(f'Match found: {matched_inmate.full_name}', 'success')
        else:
            flash('No match found.', 'warning')
        
        return redirect(url_for('recognition.upload_recognition'))

    return render_template('recognition/upload.html')

@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')

