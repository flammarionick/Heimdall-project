# backend/run.py
from flask_socketio import SocketIO
from app import create_app

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")  # allows frontend connection

if __name__ == '__main__':
    print("Starting server on port 5002...")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)


