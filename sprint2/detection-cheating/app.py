import streamlit as st
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import time
import os
import urllib.request

st.set_page_config(page_title="Head Pose Cheating Detection", layout="wide")

st.title("Head Pose Cheating Detection System")

MODEL_PATH = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

def ensure_model():
    if not os.path.exists(MODEL_PATH):
        with st.spinner("Downloading face landmark model..."):
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

with st.sidebar:
    st.header("Settings")
    YAW_THRESHOLD = st.slider("Yaw Threshold (degrees)", 5, 45, 20)
    PITCH_THRESHOLD = st.slider("Pitch Threshold (degrees)", 5, 45, 20)
    CHEATING_TIME_THRESHOLD = st.slider("Sustained Time to Flag (seconds)", 0.5, 5.0, 1.5)
    run = st.checkbox("Start Camera", value=False)

col1, col2 = st.columns([3, 1])
frame_placeholder = col1.empty()
status_placeholder = col2.empty()
log_placeholder = col2.empty()

FACE_LANDMARK_IDS = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_left_corner": 33,
    "right_eye_right_corner": 263,
    "mouth_left_corner": 61,
    "mouth_right_corner": 291
}

MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -63.6, -12.5),
    (-43.3, 32.7, -26.0),
    (43.3, 32.7, -26.0),
    (-28.9, -28.9, -24.1),
    (28.9, -28.9, -24.1)
], dtype=np.float64)

def build_landmarker():
    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_faces=1
    )
    return mp_vision.FaceLandmarker.create_from_options(options)

def get_head_pose(landmarks, frame_shape):
    h, w = frame_shape[:2]

    def pt(idx):
        lm = landmarks[idx]
        return (lm.x * w, lm.y * h)

    image_points = np.array([
        pt(FACE_LANDMARK_IDS["nose_tip"]),
        pt(FACE_LANDMARK_IDS["chin"]),
        pt(FACE_LANDMARK_IDS["left_eye_left_corner"]),
        pt(FACE_LANDMARK_IDS["right_eye_right_corner"]),
        pt(FACE_LANDMARK_IDS["mouth_left_corner"]),
        pt(FACE_LANDMARK_IDS["mouth_right_corner"])
    ], dtype=np.float64)

    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)

    dist_coeffs = np.zeros((4, 1))

    success, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
    )

    if not success:
        return None, None, None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    pose_matrix = cv2.hconcat((rotation_matrix, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_matrix)

    pitch, yaw, roll = euler_angles.flatten()

    if pitch > 90:
        pitch -= 180
    elif pitch < -90:
        pitch += 180

    return pitch, yaw, roll

def main():
    if "cheating_start_time" not in st.session_state:
        st.session_state.cheating_start_time = None
    if "cheating_events" not in st.session_state:
        st.session_state.cheating_events = []
    if "is_cheating" not in st.session_state:
        st.session_state.is_cheating = False

    if not run:
        status_placeholder.info("Camera is stopped. Enable 'Start Camera' in the sidebar.")
        return

    ensure_model()
    landmarker = build_landmarker()
    cap = cv2.VideoCapture(0)

    frame_index = 0
    start_time_ms = int(time.time() * 1000)

    while run and cap.isOpened():
        success, frame = cap.read()
        if not success:
            status_placeholder.error("Failed to access camera")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int(time.time() * 1000) - start_time_ms
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        label = "No Face Detected"
        color = (128, 128, 128)

        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            pitch, yaw, roll = get_head_pose(landmarks, frame.shape)

            if pitch is not None:
                is_looking_away = abs(yaw) > YAW_THRESHOLD or abs(pitch) > PITCH_THRESHOLD

                if is_looking_away:
                    if st.session_state.cheating_start_time is None:
                        st.session_state.cheating_start_time = time.time()

                    elapsed = time.time() - st.session_state.cheating_start_time

                    if elapsed >= CHEATING_TIME_THRESHOLD:
                        label = "CHEATING DETECTED"
                        color = (0, 0, 255)
                        if not st.session_state.is_cheating:
                            st.session_state.is_cheating = True
                            st.session_state.cheating_events.append(time.strftime("%H:%M:%S"))
                    else:
                        label = "Looking Away"
                        color = (0, 165, 255)
                else:
                    st.session_state.cheating_start_time = None
                    st.session_state.is_cheating = False
                    label = "Focused"
                    color = (0, 255, 0)

                cv2.putText(frame, f"Yaw: {yaw:.1f}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Pitch: {pitch:.1f}", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(frame, label, (20, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB")

        if label == "CHEATING DETECTED":
            status_placeholder.error(label)
        elif label == "Looking Away":
            status_placeholder.warning(label)
        elif label == "Focused":
            status_placeholder.success(label)
        else:
            status_placeholder.info(label)

        if st.session_state.cheating_events:
            log_placeholder.write("Cheating Events Log")
            for event_time in st.session_state.cheating_events[-10:]:
                log_placeholder.write(event_time)

        frame_index += 1

    cap.release()
    landmarker.close()

if __name__ == "__main__":
    main()