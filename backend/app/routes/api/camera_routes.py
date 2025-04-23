from flask import Blueprint, jsonify, request, abort
from app import db
from app.models.camera import Camera

api_camera = Blueprint('api_camera', __name__)

@api_camera.route('/api/cameras', methods=['GET'])
def list_cameras():
    cameras = Camera.query.all()
    return jsonify([c.to_dict() for c in cameras])

@api_camera.route('/api/cameras/<int:id>', methods=['GET'])
def get_camera(id):
    camera = Camera.query.get_or_404(id)
    return jsonify(camera.to_dict())

@api_camera.route('/api/cameras', methods=['POST'])
def create_camera():
    data = request.json
    if not data or 'name' not in data:
        abort(400, description="Camera name is required.")
    
    new_camera = Camera(
        name=data['name'],
        location=data.get('location'),
        stream_url=data.get('stream_url')
    )
    db.session.add(new_camera)
    db.session.commit()
    return jsonify(new_camera.to_dict()), 201

@api_camera.route('/api/cameras/<int:id>', methods=['PUT'])
def update_camera(id):
    camera = Camera.query.get_or_404(id)
    data = request.json

    camera.name = data.get('name', camera.name)
    camera.location = data.get('location', camera.location)
    camera.stream_url = data.get('stream_url', camera.stream_url)

    db.session.commit()
    return jsonify(camera.to_dict())

@api_camera.route('/api/cameras/<int:id>/toggle', methods=['PATCH'])
def toggle_camera_status(id):
    camera = Camera.query.get_or_404(id)
    camera.is_active = not camera.is_active
    db.session.commit()
    return jsonify({"id": camera.id, "is_active": camera.is_active})

@api_camera.route('/api/cameras/<int:id>', methods=['DELETE'])
def delete_camera(id):
    camera = Camera.query.get_or_404(id)
    db.session.delete(camera)
    db.session.commit()
    return jsonify({"message": f"Camera {id} deleted."}), 204
