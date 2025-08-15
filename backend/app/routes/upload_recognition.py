# app/routes/upload_recognition.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from app.utils.auth_helpers import login_or_jwt_required

upload_bp = Blueprint('upload_recognition', __name__, url_prefix='/api')

UPLOAD_FOLDER = 'dataset'  # or wherever you store training data
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/upload-recognition', methods=['POST'])
@login_or_jwt_required
def upload_face():
    """
    Saves a labeled face image under dataset/<inmate_name>/<inmate_name>_<timestamp>.jpg
    Returns JSON with the saved path. Emits 'face_uploaded' via Socket.IO (best-effort).
    """
    file = request.files.get('file')
    inmate_name = request.form.get('inmate_name')
    location = request.form.get('location')

    if not file or not inmate_name or not location:
        return jsonify({"error": "Missing required fields: file, inmate_name, location"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type"}), 400

    inmate_dir = os.path.join(UPLOAD_FOLDER, secure_filename(inmate_name))
    os.makedirs(inmate_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = secure_filename(f"{inmate_name}_{timestamp}.jpg")
    filepath = os.path.join(inmate_dir, filename)
    file.save(filepath)

    # Optional: emit socket event (best-effort)
    try:
        from run import socketio
        socketio.emit('face_uploaded', {
            'inmate_name': inmate_name,
            'location': location,
            'file': filename,
            'path': filepath
        })
    except Exception as e:
        print("[upload_recognition] Socket emit failed:", e)

    return jsonify({
        "message": f"Face data saved for {inmate_name}",
        "inmate_name": inmate_name,
        "location": location,
        "filename": filename,
        "path": filepath
    }), 201