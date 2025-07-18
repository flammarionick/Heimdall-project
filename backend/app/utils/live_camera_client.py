# live_camera_client.py
import cv2
from utils.recognition_client import send_frame_for_recognition

cap = cv2.VideoCapture(0)  # Change to your camera source
camera_id = "cam-001"

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Send every N seconds OR based on motion trigger
    result = send_frame_for_recognition(frame, camera_id=camera_id)
    
    # Display prediction
    if 'predicted_id' in result:
        cv2.putText(frame, f"Predicted ID: {result['predicted_id']}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    elif 'error' in result:
        print("Recognition error:", result['error'])

    cv2.imshow('Live Camera Feed', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
