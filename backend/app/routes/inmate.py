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

# Where to save uploaded images so they can be served by Flask static
UPLOAD_FOLDER = os.path.join('app', 'static', 'inmate_images')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Your local embedding microservice (embedding.py)
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
        if not form.validate_on_submit():
            # Helpful debug
            print("Form errors:", form.errors)
            flash('Please fix the errors in the form.', 'danger')
            return render_template('inmate/register.html', form=form)

        try:
            # Save image
            file = form.face_image.data
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(save_path)

            # Send base64 image to embedding server as JSON
            with open(save_path, 'rb') as f:
                b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode('utf-8')

            # embedding.py expects JSON {"image": "<dataurl>"}
            resp = requests.post(AI_MODEL_URL, json={"image": b64}, timeout=40)
            resp.raise_for_status()
            result = resp.json()
            embedding = result.get('embedding')

            if not embedding:
                flash("Face not detected by model.", "danger")
                return render_template('inmate/register.html', form=form)

            # Create inmate record (align with your Inmate model fields)
            inmate = Inmate(
                full_name=form.full_name.data,
                prison_id=form.prison_id.data,
                duration_months=form.duration_months.data,
                image_url=f"/static/inmate_images/{filename}"
            )
            db.session.add(inmate)
            db.session.flush()  # get inmate.id

            # Optional: if you have a FacialEmbedding model, save it here
            # from app.models.embedding import FacialEmbedding
            # fe = FacialEmbedding(inmate_id=inmate.id, embedding=embedding)
            # db.session.add(fe)

            db.session.commit()
            flash("Inmate registered successfully with AI-generated encoding!", "success")
            return redirect(url_for('inmate.inmate_home'))

        except requests.RequestException as e:
            print("Error contacting AI model:", e)
            flash(f"Error contacting AI model: {e}", "danger")
        except Exception as e:
            print("Registration error:", e)
            flash("Registration failed. Check server logs.", "danger")

    return render_template('inmate/register.html', form=form)