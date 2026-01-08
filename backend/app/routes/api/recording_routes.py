# backend/app/routes/api/recording_routes.py
"""
API routes for video recording management.
Handles upload, listing, streaming, and deletion of surveillance recordings.
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import current_user
from app.extensions import db
from app.models.recording import Recording
from app.models.camera import Camera
from app.utils.auth_helpers import login_or_jwt_required
from datetime import datetime
from werkzeug.utils import secure_filename
import os

recording_api_bp = Blueprint('recording_api', __name__, url_prefix='/recordings')

# Allowed video extensions
ALLOWED_EXTENSIONS = {'webm', 'mp4', 'mkv', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_recordings_dir():
    """Get the recordings directory path."""
    base_dir = current_app.config.get('RECORDINGS_DIR') or os.path.join(
        current_app.root_path, 'static', 'recordings'
    )
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


@recording_api_bp.route('/', methods=['GET'])
@login_or_jwt_required
def list_recordings():
    """
    List recordings with optional filters.
    Query params:
        - camera_id: Filter by camera
        - date: Filter by date (YYYY-MM-DD)
        - status: Filter by status (recording, completed, error)
        - limit: Max results (default 50)
        - offset: Pagination offset
    """
    camera_id = request.args.get('camera_id', type=int)
    date_str = request.args.get('date')
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Recording.query

    if camera_id:
        query = query.filter(Recording.camera_id == camera_id)

    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(
                db.func.date(Recording.start_time) == date
            )
        except ValueError:
            pass

    if status:
        query = query.filter(Recording.status == status)

    # Order by most recent first
    query = query.order_by(Recording.start_time.desc())

    total = query.count()
    recordings = query.offset(offset).limit(limit).all()

    return jsonify({
        'recordings': [r.to_dict() for r in recordings],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@recording_api_bp.route('/start', methods=['POST'])
@login_or_jwt_required
def start_recording():
    """
    Register a new recording session.
    Body (JSON):
        - camera_id: Camera ID or device ID (required)
        - camera_name: Camera name (optional, for auto-creating webcams)
        - latitude: GPS latitude (optional)
        - longitude: GPS longitude (optional)
        - location_name: Human-readable location (optional)
    """
    data = request.get_json() or {}

    camera_id = data.get('camera_id')
    if not camera_id:
        return jsonify({'error': 'camera_id is required'}), 400

    # Try to find existing camera by ID (integer) or device_id (string)
    camera = None
    if isinstance(camera_id, int) or (isinstance(camera_id, str) and camera_id.isdigit()):
        camera = Camera.query.get(int(camera_id))

    if not camera:
        # Try to find by device_id (for webcams)
        camera = Camera.query.filter_by(device_id=str(camera_id)).first()

    if not camera:
        # Auto-create camera for browser webcams
        camera_name = data.get('camera_name') or f"Webcam {str(camera_id)[:8]}"
        camera = Camera(
            name=camera_name,
            camera_type='webcam',
            device_id=str(camera_id),
            location=data.get('location_name') or 'Local Device',
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            status=True  # Boolean: True = active
        )
        db.session.add(camera)
        db.session.commit()

    # Create recording record
    start_time = datetime.utcnow()
    date_str = start_time.strftime('%Y-%m-%d')
    time_str = start_time.strftime('%H-%M-%S')

    # Generate filename and path using database camera ID
    filename = f"recording_{camera.id}_{time_str}.webm"
    relative_path = os.path.join(str(camera.id), date_str, filename)

    recording = Recording(
        camera_id=camera.id,
        filename=filename,
        file_path=relative_path,
        start_time=start_time,
        latitude=data.get('latitude') or camera.latitude,
        longitude=data.get('longitude') or camera.longitude,
        location_name=data.get('location_name') or camera.location,
        status='recording',
        user_id=current_user.id if current_user and hasattr(current_user, 'id') else None
    )

    db.session.add(recording)
    db.session.commit()

    return jsonify({
        'id': recording.id,
        'upload_url': f'/api/recordings/{recording.id}/upload',
        'recording': recording.to_dict()
    }), 201


@recording_api_bp.route('/<int:recording_id>/upload', methods=['POST'])
@login_or_jwt_required
def upload_recording(recording_id):
    """
    Upload the video file for a recording.
    Body (multipart/form-data):
        - video: Video file
        - duration: Duration in seconds (optional)
    """
    recording = Recording.query.get_or_404(recording_id)

    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Create directory structure
    recordings_dir = get_recordings_dir()
    full_dir = os.path.join(recordings_dir, str(recording.camera_id), recording.start_time.strftime('%Y-%m-%d'))
    os.makedirs(full_dir, exist_ok=True)

    # Save file
    full_path = os.path.join(full_dir, recording.filename)
    video_file.save(full_path)

    # Update recording metadata
    recording.file_size = os.path.getsize(full_path)
    recording.end_time = datetime.utcnow()
    recording.status = 'completed'

    # Duration from form or calculate
    duration = request.form.get('duration', type=int)
    if duration:
        recording.duration = duration
    elif recording.start_time:
        recording.duration = int((recording.end_time - recording.start_time).total_seconds())

    db.session.commit()

    return jsonify({
        'status': 'uploaded',
        'recording': recording.to_dict()
    })


@recording_api_bp.route('/<int:recording_id>/complete', methods=['POST'])
@login_or_jwt_required
def complete_recording(recording_id):
    """
    Mark a recording as complete (without upload - for external storage).
    """
    recording = Recording.query.get_or_404(recording_id)

    data = request.get_json() or {}
    recording.end_time = datetime.utcnow()
    recording.status = 'completed'
    recording.duration = data.get('duration')
    recording.file_size = data.get('file_size')

    db.session.commit()

    return jsonify({'recording': recording.to_dict()})


@recording_api_bp.route('/<int:recording_id>', methods=['GET'])
@login_or_jwt_required
def get_recording(recording_id):
    """Get recording details."""
    recording = Recording.query.get_or_404(recording_id)
    return jsonify({'recording': recording.to_dict()})


@recording_api_bp.route('/<int:recording_id>/stream', methods=['GET'])
@login_or_jwt_required
def stream_recording(recording_id):
    """Stream the video file."""
    recording = Recording.query.get_or_404(recording_id)

    if recording.status != 'completed':
        return jsonify({'error': 'Recording not complete'}), 400

    recordings_dir = get_recordings_dir()
    full_path = os.path.join(recordings_dir, recording.file_path)

    if not os.path.exists(full_path):
        return jsonify({'error': 'Recording file not found'}), 404

    return send_file(
        full_path,
        mimetype=recording.mime_type or 'video/webm',
        as_attachment=False
    )


@recording_api_bp.route('/<int:recording_id>', methods=['DELETE'])
@login_or_jwt_required
def delete_recording(recording_id):
    """Delete a recording and its file."""
    recording = Recording.query.get_or_404(recording_id)

    # Delete file if exists
    recordings_dir = get_recordings_dir()
    full_path = os.path.join(recordings_dir, recording.file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError as e:
            print(f"Error deleting file: {e}")

    # Delete database record
    db.session.delete(recording)
    db.session.commit()

    return jsonify({'status': 'deleted'})


@recording_api_bp.route('/cameras', methods=['GET'])
@login_or_jwt_required
def get_cameras_with_recordings():
    """Get list of cameras that have recordings, with recording counts."""
    cameras = db.session.query(
        Camera.id,
        Camera.name,
        Camera.location,
        db.func.count(Recording.id).label('recording_count')
    ).outerjoin(Recording).group_by(Camera.id).all()

    return jsonify({
        'cameras': [
            {
                'id': c.id,
                'name': c.name,
                'location': c.location,
                'recording_count': c.recording_count
            }
            for c in cameras
        ]
    })


@recording_api_bp.route('/dates', methods=['GET'])
@login_or_jwt_required
def get_recording_dates():
    """Get list of dates that have recordings."""
    camera_id = request.args.get('camera_id', type=int)

    query = db.session.query(
        db.func.date(Recording.start_time).label('date'),
        db.func.count(Recording.id).label('count')
    )

    if camera_id:
        query = query.filter(Recording.camera_id == camera_id)

    query = query.group_by(db.func.date(Recording.start_time))
    query = query.order_by(db.func.date(Recording.start_time).desc())

    dates = query.all()

    return jsonify({
        'dates': [
            {'date': str(d.date), 'count': d.count}
            for d in dates
        ]
    })
