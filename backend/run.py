# backend/run.py
from flask_socketio import SocketIO
from app import create_app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")  # allows frontend connection

if __name__ == '__main__':
    socketio.run(app, debug=True)


