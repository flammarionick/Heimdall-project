from flask import Blueprint, render_template, redirect, flash, url_for, request
from flask_login import login_required
from app.forms import InmateForm
from werkzeug.utils import secure_filename
from app.models import Inmate
from app import db
import os
import requests
import json

UPLOAD_FOLDER = 'app/static/inmate_images'
AI_MODEL_URL = 'http://localhost:5001/encode'  # Update this to your actual model endpoint

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
        file = form.face_image.data
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        # Send image to AI model for encoding
        with open(filepath, 'rb') as image_file:
            files = {'image': image_file}
            try:
                response = requests.post(AI_MODEL_URL, files=files)
                response.raise_for_status()
                result = response.json()
                encoding = result.get('embedding')
                if not encoding:
                    flash("Face not detected by model.", "danger")
                    return redirect(request.url)
            except requests.exceptions.RequestException as e:
                flash(f"Error contacting AI model: {e}", "danger")
                return redirect(request.url)

        # Save to database
        new_inmate = Inmate(
            name=form.name.data,
            id=form.id.data,
            mugshot_path= filepath,
            sentence_start=form.sentence_start.data,
            sentence_duration_days=form.sentence_duration_days.data,
            image_filename=filename,
            status =form.status.data,
            face_encoding=encoding  # Stored as a list of floats or JSON
        )
        db.session.add(new_inmate)
        db.session.commit()

        flash("Inmate registered successfully with AI-generated encoding!", "success")
        return redirect(url_for('inmate.inmate_home'))

    return render_template('inmate/register.html', form=form)