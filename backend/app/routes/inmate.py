from flask import Blueprint, render_template, redirect, flash, url_for, request
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.forms import InmateForm
from app.models.inmate import Inmate
from app import db
import os
import base64
import requests

inmate_bp = Blueprint('inmate', __name__, url_prefix='/inmates')

# Where to save uploaded images
UPLOAD_FOLDER = os.path.join('app', 'static', 'inmate_images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Embedding service
AI_MODEL_URL = os.getenv('EMBEDDING_SERVICE_URL', 'http://127.0.0.1:5001/encode')

@inmate_bp.route('/', methods=['GET'])
@login_required
def inmate_home():
    return render_template('inmate/index.html', title='Inmate Management')

@inmate_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    form = InmateForm()

    if request.method == 'POST':
        # If the form fails validation, show errors
        if not form.validate_on_submit():
            print("[Inmate Register] Form errors:", form.errors)
            flash('Please fix the errors in the form.', 'danger')
            return render_template('inmate/register.html', form=form)

        try:
            # --- Save the uploaded face image ---
            file = form.face_image.data
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            # --- Call embedding microservice (expects JSON: {"image": "data:image/...;base64,..."}) ---
            with open(save_path, 'rb') as f:
                b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('utf-8')

            print("[Inmate Register] Sending image to embedding service:", AI_MODEL_URL)
            resp = requests.post(AI_MODEL_URL, json={"image": b64}, timeout=40)
            # If the service returns a non-200, raise
            resp.raise_for_status()
            payload = resp.json()
            embedding = payload.get('embedding')
            if not embedding:
                flash("Face not detected by model.", "danger")
                return render_template('inmate/register.html', form=form)

            # --- Create the Inmate record ---
            inmate = Inmate()

            # Name: prefer 'full_name', fallback to 'name'
            full_name_value = form.full_name.data
            if hasattr(inmate, 'full_name'):
                inmate.full_name = full_name_value
            elif hasattr(inmate, 'name'):
                inmate.name = full_name_value

            # Prison ID: prefer 'prison_id', fallback to 'reference_number'
            prison_id_value = form.prison_id.data
            if hasattr(inmate, 'prison_id'):
                inmate.prison_id = prison_id_value
            elif hasattr(inmate, 'reference_number'):
                inmate.reference_number = prison_id_value

            # Duration: prefer 'duration_months', fallback map to 'sentence_duration_days'
            duration_months_val = form.duration_months.data
            if hasattr(inmate, 'duration_months'):
                inmate.duration_months = duration_months_val
            elif hasattr(inmate, 'sentence_duration_days'):
                inmate.sentence_duration_days = int(duration_months_val) * 30

            # Image path: prefer 'image_url', fallback to 'mugshot_path' or 'image_filename'
            rel_path = f"/static/inmate_images/{filename}"
            if hasattr(inmate, 'image_url'):
                inmate.image_url = rel_path
            elif hasattr(inmate, 'mugshot_path'):
                inmate.mugshot_path = rel_path
            elif hasattr(inmate, 'image_filename'):
                inmate.image_filename = filename

            # Optional: if your Inmate model has a JSON/ARRAY field for the embedding
            if hasattr(inmate, 'face_encoding'):
                inmate.face_encoding = embedding  # JSON-serializable list of floats

            db.session.add(inmate)
            db.session.commit()

            flash("Inmate registered successfully with AI-generated encoding!", "success")
            return redirect(url_for('inmate.inmate_home'))

        except requests.RequestException as e:
            print("[Inmate Register] Error contacting AI model:", e)
            flash(f"Error contacting AI model: {e}", "danger")
            return render_template('inmate/register.html', form=form)
        except Exception as e:
            print("[Inmate Register] Registration error:", e)
            flash("Registration failed. Check server logs.", "danger")
            return render_template('inmate/register.html', form=form)

    # GET
    return render_template('inmate/register.html', form=form)