from flask import Blueprint, request, jsonify
from app import db, socketio
from app.models.camera import Camera
from app.utils.auth_helpers import login_or_jwt_required

api_camera = Blueprint('api_camera', __name__, url_prefix='/api/cameras')

# List all cameras
@api_camera.route('/', methods=['GET'])
@login_or_jwt_required
def list_cameras():
    cameras = Camera.query.all()
    return jsonify([camera.to_dict() for camera in cameras])

# Create a new camera
@api_camera.route('/', methods=['POST'])
@login_or_jwt_required
def create_camera():
    data = request.get_json()
    new_camera = Camera(
        name=data['name'],
        location=data['location'],
        status=True  # Default active
    )
    db.session.add(new_camera)
    db.session.commit()
    socketio.emit('camera_created', new_camera.to_dict())
    return jsonify({'message': 'Camera created successfully'}), 201

# Get a single camera
@api_camera.route('/<int:id>', methods=['GET'])
@login_or_jwt_required
def get_camera(id):
    camera = Camera.query.get_or_404(id)
    return jsonify(camera.to_dict())

# Update camera
@api_camera.route('/<int:id>', methods=['PUT'])
@login_or_jwt_required
def update_camera(id):
    camera = Camera.query.get_or_404(id)
    data = request.get_json()
    camera.name = data.get('name', camera.name)
    camera.location = data.get('location', camera.location)
    db.session.commit()
    socketio.emit('camera_updated', camera.to_dict())
    return jsonify({'message': 'Camera updated successfully'})

# Delete camera
@api_camera.route('/<int:id>', methods=['DELETE'])
@login_or_jwt_required
def delete_camera(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    socketio.emit('camera_deleted', {'id': id})
    return jsonify({'message': 'Camera deleted successfully'})

# Toggle camera status
@api_camera.route('/<int:id>/toggle', methods=['PATCH'])
@login_or_jwt_required
def toggle_camera_status(id):
    camera = Camera.query.get_or_404(id)
    camera.status = not camera.status
    db.session.commit()
    socketio.emit('camera_status_toggled', camera.to_dict())
    return jsonify({'message': 'Camera status toggled'})
