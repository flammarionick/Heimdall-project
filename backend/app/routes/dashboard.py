from flask import Blueprint, render_template, Response
from flask_login import login_required, current_user
import cv2

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# Use your webcam (0) or change to IP stream
camera = cv2.VideoCapture(0)

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Yield frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@dashboard_bp.route('/')
@login_required
def view_dashboard():
    return render_template('dashboard/dashboard.html')

@dashboard_bp.route('/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
