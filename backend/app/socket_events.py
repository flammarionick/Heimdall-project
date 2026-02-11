# app/socket_events.py
from flask_socketio import emit, join_room
import base64
import datetime
from flask_login import current_user
from app import socketio

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.username)
        print(f"{current_user.username} connected.")
    else:
        print("Anonymous user connected.")

@socketio.on('send_frame')
def handle_send_frame(data):
    if not current_user.is_authenticated:
        return

    frame_data = data.get('frame')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # For Admins: broadcast frames to 'admin' room (optional later)
    # For now: emit to user's personal room
    emit('receive_frame', {
        'frame': frame_data,
        'username': current_user.username,
        'timestamp': timestamp,
    }, room=current_user.username)

    # If admin, broadcast also to a "global" room
    if current_user.is_admin:
        emit('receive_frame', {
            'frame': frame_data,
            'username': current_user.username,
            'timestamp': timestamp,
        }, broadcast=True)
