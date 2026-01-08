from flask import Blueprint, request, jsonify
from flask_login import current_user
from app import db, socketio
from app.models.camera import Camera
from app.utils.auth_helpers import login_or_jwt_required

api_camera = Blueprint('api_camera', __name__, url_prefix='/api/cameras')
api_camera.strict_slashes = False  # Allow both /api/cameras and /api/cameras/

# List cameras for current user
@api_camera.route('', methods=['GET'])
@api_camera.route('/', methods=['GET'])
@login_or_jwt_required
def list_cameras():
    # Filter cameras by current user
    cameras = Camera.query.filter_by(user_id=current_user.id).all()
    return jsonify({'cameras': [camera.to_dict() for camera in cameras]})

# Create a new camera for current user
@api_camera.route('', methods=['POST'])
@api_camera.route('/', methods=['POST'])
@login_or_jwt_required
def create_camera():
    data = request.get_json()
    new_camera = Camera(
        name=data.get('name', 'Webcam'),
        location=data.get('location', 'Local Device'),
        status=True,
        camera_type=data.get('camera_type', 'webcam'),
        stream_url=data.get('stream_url'),
        device_id=data.get('device_id'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        user_id=current_user.id  # Associate with current user
    )
    db.session.add(new_camera)
    db.session.commit()
    socketio.emit('camera_created', new_camera.to_dict())
    return jsonify({'message': 'Camera created successfully', 'camera': new_camera.to_dict()}), 201

# Get a single camera (must belong to current user)
@api_camera.route('/<int:id>', methods=['GET'])
@login_or_jwt_required
def get_camera(id):
    camera = Camera.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify(camera.to_dict())

# Update camera (must belong to current user)
@api_camera.route('/<int:id>', methods=['PUT'])
@login_or_jwt_required
def update_camera(id):
    camera = Camera.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    camera.name = data.get('name', camera.name)
    camera.location = data.get('location', camera.location)
    camera.camera_type = data.get('camera_type', camera.camera_type)
    camera.stream_url = data.get('stream_url', camera.stream_url)
    camera.device_id = data.get('device_id', camera.device_id)
    # Update coordinates if provided
    if 'latitude' in data:
        camera.latitude = data.get('latitude')
    if 'longitude' in data:
        camera.longitude = data.get('longitude')
    db.session.commit()
    socketio.emit('camera_updated', camera.to_dict())
    return jsonify({'message': 'Camera updated successfully', 'camera': camera.to_dict()})

# Delete camera (must belong to current user)
@api_camera.route('/<int:id>', methods=['DELETE'])
@login_or_jwt_required
def delete_camera(id):
    camera = Camera.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(camera)
    db.session.commit()
    socketio.emit('camera_deleted', {'id': id})
    return jsonify({'message': 'Camera deleted successfully'})

# Toggle camera status (must belong to current user)
@api_camera.route('/<int:id>/toggle', methods=['POST', 'PATCH'])
@login_or_jwt_required
def toggle_camera_status(id):
    camera = Camera.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    camera.status = not camera.status
    db.session.commit()
    socketio.emit('camera_status_toggled', camera.to_dict())
    return jsonify({'message': 'Camera status toggled', 'camera': camera.to_dict()})
