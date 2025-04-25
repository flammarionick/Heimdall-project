from flask import Blueprint, request, jsonify
from app import db, socketio
from app.models.camera import Camera

api_camera = Blueprint('api_camera', __name__, url_prefix='/api/cameras')

# List all cameras
@api_camera.route('/', methods=['GET'])
def list_cameras():
    cameras = Camera.query.all()
    return jsonify([camera.to_dict() for camera in cameras])

# Create a new camera
@api_camera.route('/', methods=['POST'])
def create_camera():
    data = request.get_json()
    new_camera = Camera(
        name=data['name'],
        location=data['location'],
        status=True  # By default, camera is active
    )
    db.session.add(new_camera)
    db.session.commit()
    socketio.emit('camera_created', new_camera.to_dict())
    return jsonify({'message': 'Camera created successfully'}), 201

# Get a single camera by ID
@api_camera.route('/<int:id>', methods=['GET'])
def get_camera(id):
    camera = Camera.query.get_or_404(id)
    return jsonify(camera.to_dict())

# Update a camera (name/location)
@api_camera.route('/<int:id>', methods=['PUT'])
def update_camera(id):
    camera = Camera.query.get_or_404(id)
    data = request.get_json()
    camera.name = data.get('name', camera.name)
    camera.location = data.get('location', camera.location)
    db.session.commit()
    socketio.emit('camera_updated', camera.to_dict())
    return jsonify({'message': 'Camera updated successfully'})

# Delete a camera
@api_camera.route('/<int:id>', methods=['DELETE'])
def delete_camera(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    socketio.emit('camera_deleted', {'id': id})
    return jsonify({'message': 'Camera deleted successfully'})

# Toggle camera status (on/off)
@api_camera.route('/<int:id>/toggle', methods=['PATCH'])
def toggle_camera_status(id):
    camera = Camera.query.get_or_404(id)
    camera.status = not camera.status
    db.session.commit()
    socketio.emit('camera_status_toggled', camera.to_dict())
    return jsonify({'message': 'Camera status toggled'})
