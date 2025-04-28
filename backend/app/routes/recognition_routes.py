from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
import os
from werkzeug.utils import secure_filename

recognition_bp = Blueprint('recognition', __name__, url_prefix='/recognition')

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@recognition_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_recognition():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file.', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(upload_path)

            # 📸 Here you would run the recognition model
            # result = recognize_face(upload_path)
            result = {"match": False, "inmate": None}  # 🔥 Placeholder for now

            return render_template('recognition/upload_result.html', result=result)

    return render_template('recognition/upload.html')

@recognition_bp.route('/live')
@login_required
def live_recognition():
    return render_template('recognition/live.html')

