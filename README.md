# AI-based-Driver-Eye-Monitoring-System-
AI-Based Driver Eye Monitoring and Drowsiness Detection System using Python, OpenCV, and Dlib for real-time driver safety monitoring. The system detects eye closure using Eye Aspect Ratio (EAR) and generates alerts, warning sounds, snapshots, and email notifications with live location to help prevent road accidents.
# AI-Based Driver Eye Monitoring and Drowsiness Detection System

This project is a real-time driver drowsiness detection system developed using Python, OpenCV, and Dlib. The system monitors the driver's eye movements using a webcam and detects drowsiness based on Eye Aspect Ratio (EAR).

When drowsiness is detected, the system:
- Plays warning alarm sound
- Gives voice alert
- Captures driver snapshot
- Sends email alert with live location

## Technologies Used
- Python
- OpenCV
- Dlib
- Flask
- Pyttsx3
- Pygame
- SMTP

## Features
- Real-time eye monitoring
- Drowsiness detection using EAR
- Voice and sound alerts
- Snapshot capture
- Email notification system
- Live GPS location sharing

## How to Run

1. Install required libraries
2. Download `shape_predictor_68_face_landmarks.dat`
3. Run the project:

```bash
python detect_drowsiness.py --shape-predictor shape_predictor_68_face_landmarks.dat
```

## Applications
- Driver safety systems
- Smart transportation
- Accident prevention
- AI-based vehicle monitoring
