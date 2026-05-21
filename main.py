# USAGE
# python detect_drowsiness.py --shape-predictor shape_predictor_68_face_landmarks.dat

from scipy.spatial import distance as dist
from imutils.video import VideoStream
from imutils import face_utils
import argparse
import imutils
import time
import dlib
import cv2
import pyttsx3
import threading
import smtplib, ssl, os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, request
import webbrowser
import pygame


def speak_message(message):
    """Simple TTS for calibration instructions."""
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say(message)
    engine.runAndWait()


def calibrate_threshold(vs, detector, predictor, lStart, lEnd, rStart, rEnd, duration=5):
    print("[INFO] Starting calibration... Please keep your eyes OPEN.")
    speak_message("Calibration starting. Please keep your eyes open.")
    start_time = time.time()
    open_ear_values = []

    # Collect EAR with eyes open
    while time.time() - start_time < duration:
        frame = vs.read()
        frame = imutils.resize(frame, width=450)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = detector(gray, 0)

        for rect in rects:
            shape = predictor(gray, rect)
            shape = face_utils.shape_to_np(shape)

            leftEye = shape[lStart:lEnd]
            rightEye = shape[rStart:rEnd]
            ear = (eye_aspect_ratio(leftEye) + eye_aspect_ratio(rightEye)) / 2.0
            open_ear_values.append(ear)

        cv2.putText(frame, "Keep eyes OPEN", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow("Calibration", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    avg_open = sum(open_ear_values) / len(open_ear_values)
    print(f"[INFO] Avg EAR (open eyes): {avg_open:.3f}")

    # Closed eyes calibration
    print("[INFO] Now close your eyes for calibration...")
    speak_message("Now please close your eyes.")
    time.sleep(2)
    start_time = time.time()
    closed_ear_values = []

    while time.time() - start_time < duration:
        frame = vs.read()
        frame = imutils.resize(frame, width=450)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = detector(gray, 0)

        for rect in rects:
            shape = predictor(gray, rect)
            shape = face_utils.shape_to_np(shape)

            leftEye = shape[lStart:lEnd]
            rightEye = shape[rStart:rEnd]
            ear = (eye_aspect_ratio(leftEye) + eye_aspect_ratio(rightEye)) / 2.0
            closed_ear_values.append(ear)

        cv2.putText(frame, "Keep eyes CLOSED", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("Calibration", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    avg_closed = sum(closed_ear_values) / len(closed_ear_values)
    print(f"[INFO] Avg EAR (closed eyes): {avg_closed:.3f}")

    cv2.destroyWindow("Calibration")

    # Final threshold
    threshold = (avg_open + avg_closed) / 2.0
    print(f"[INFO] Calibrated EAR threshold = {threshold:.3f}")

    speak_message("Calibration complete. Starting AI based Driver Eye Monitoring System.")
    return threshold


# --------------------------- CONFIG ---------------------------
EYE_AR_THRESH = 0.2
EYE_AR_CONSEC_FRAMES = 20
WARNING_DISPLAY_FRAMES = 30  # show alert message for these many frames

SENDER_EMAIL = "alertcollege00@gmail.com"
SENDER_PASS = "hfyh kjfe lbme tkel"   # <-- replace with Gmail App password
RECIPIENTS = ["payalshinde191203@gmail.com","shaikfa66@gmail.com"]  # add multiple if needed

VEHICLE_NUMBER = "KA 03 JF 9987"

# ---------------------- STATE VARIABLES -----------------------
COUNTER = 0
warning_counter = 0
tts_lock = threading.Lock()

# -------------------- Location Data --------------------------
location_data = {"lat": None, "lng": None}

def run_location_server():
    """Run Flask server in background to fetch live laptop GPS location."""
    app = Flask(__name__)

    @app.route('/')
    def index():
        return open("location.html").read()

    @app.route('/location', methods=['POST'])
    def receive_location():
        global location_data
        location_data = request.json
        print("📍 Location received:", location_data)
        return 'OK'

    webbrowser.open("http://localhost:5000")  # open browser automatically
    app.run(port=5000, use_reloader=False)

# Start server in background thread
threading.Thread(target=run_location_server, daemon=True).start()

# ----------------------- EAR Calculation ----------------------
def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

# ----------------------- TTS Alert Thread ---------------------
def speak_warning(message):
    with tts_lock:
        try:
            # Initialize pygame mixer (only once)
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # Load and play the warning sound
            pygame.mixer.music.load("warning.mp3")
            pygame.mixer.music.play()

            # Let it play for 2 seconds
            time.sleep(2)

            # Stop playback (optional, if mp3 is longer)
            pygame.mixer.music.stop()

        except Exception as e:
            print("❌ Error playing mp3:", e)

        # Now do TTS
        engine = pyttsx3.init()
        engine.setProperty('rate', 145)
        engine.say(message)
        engine.runAndWait()
# ----------------------- Email Sending ------------------------
def send_email_alert(snapshot_path, lat, lon):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(RECIPIENTS)
        msg["Subject"] = "🚨 Eye Monitoring System Alert Detected!"

        # Google Maps link
        if lat and lon:
            maps_link = f"https://maps.google.com/?q={lat},{lon}"
        else:
            maps_link = "Location not available"

        body = f"""
        ALERT: Possible drowsiness detected!

        Vehicle Number: {VEHICLE_NUMBER}

        📍 Location: {maps_link}
        """

        msg.attach(MIMEText(body, "plain"))

        # Attach snapshot if available
        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(snapshot_path)}")
            msg.attach(part)

        # Send mail
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASS)
            server.sendmail(SENDER_EMAIL, RECIPIENTS, msg.as_string())

        print("✅ Email alert sent successfully!")

    except Exception as e:
        print("❌ Failed to send email:", e)

# -------------------- Argument Parsing ------------------------
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--shape-predictor", required=True,
                help="path to facial landmark predictor")
args = vars(ap.parse_args())

# ------------------- Load Dlib Models -------------------------
print("[INFO] Loading facial landmark predictor...")
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(args["shape_predictor"])
(lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
(rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]

# ------------------ Start Video Stream ------------------------
print("[INFO] Starting video stream...")
vs = VideoStream(src=0).start()
time.sleep(2.0)

EYE_AR_THRESH = calibrate_threshold(vs, detector, predictor, lStart, lEnd, rStart, rEnd)
# --------------------- Main Processing Loop -------------------


while True:


    frame = vs.read()
    if frame is None:
        continue

    frame = imutils.resize(frame, width=450)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = detector(gray, 0)

    if len(rects) == 0:
        cv2.putText(frame, "No face detected", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    else:
        for rect in rects:
            shape = predictor(gray, rect)
            shape = face_utils.shape_to_np(shape)

            leftEye = shape[lStart:lEnd]
            rightEye = shape[rStart:rEnd]
            leftEAR = eye_aspect_ratio(leftEye)
            rightEAR = eye_aspect_ratio(rightEye)
            ear = (leftEAR + rightEAR) / 2.0

            # Draw contours
            cv2.drawContours(frame, [cv2.convexHull(leftEye)], -1, (0, 255, 0), 1)
            cv2.drawContours(frame, [cv2.convexHull(rightEye)], -1, (0, 255, 0), 1)

            # EAR check
            if ear < EYE_AR_THRESH:
                COUNTER += 1
                if COUNTER >= EYE_AR_CONSEC_FRAMES and warning_counter == 0:
                    warning_counter = WARNING_DISPLAY_FRAMES

                    # Save snapshot
                    snapshot_path = "alert_snapshot.jpg"
                    cv2.imwrite(snapshot_path, frame)

                    # Get latest location
                    lat = location_data.get("lat")
                    lon = location_data.get("lng")

                    # Email alert
                    alert_thread = threading.Thread(
                        target=send_email_alert, args=(snapshot_path, lat, lon)
                    )
                    alert_thread.daemon = True
                    alert_thread.start()

                    # TTS alert
                    tts_thread = threading.Thread(
                        target=speak_warning, args=("WARNING: Please stay alert!",)
                    )
                    tts_thread.daemon = True
                    tts_thread.start()

                    COUNTER = 0
            else:
                COUNTER = 0

            cv2.putText(frame, f"EAR: {ear:.2f}", (300, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    if warning_counter > 0:
        cv2.putText(frame, "WARNING: Please Stay Alert!", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        warning_counter -= 1

    cv2.imshow("Eye Monitoring", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ----------------------- Cleanup ------------------------------
cv2.destroyAllWindows()
vs.stop()
