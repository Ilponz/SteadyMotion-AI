"""
Motore biometrico avanzato basato su Google MediaPipe Face Landmarker Tasks.
Estrae:
1. Matrice di trasformazione rigida 4x4 (Head Pose Euler: Yaw, Pitch, Roll).
2. Landmark cranici 3D (Naso, Sellion, Occhi, Iride).
3. 52 Facial Blendshapes native FACS (Blink, Jaw Open, Smile, Brow).
4. EAR & Blink Clamping per sopprimere i falsi scatti da battito palpebrale.
"""

import math
import os
from typing import Dict, List, NamedTuple, Optional, Tuple
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np


class TrackerResult(NamedTuple):
    face_detected: bool
    # Coordinate normalizzate del punto di mira (naso / posa combinata) [0.0, 1.0]
    cursor_raw_x: float
    cursor_raw_y: float
    # Angoli Euler del capo (in gradi)
    yaw: float
    pitch: float
    roll: float
    # Clamping ammiccamento
    is_blinking: bool
    blink_score: float
    # Blendshapes per comandi ausiliari
    jaw_open_score: float
    smile_score: float
    brow_down_score: float
    # Offset iride per micro-correzione sguardo
    iris_dx: float
    iris_dy: float


class FaceTrackerEngine:
    """Motore di tracciamento facciale e posa 6-DoF."""

    # Indici chiave della mesh MediaPipe 478
    NOSE_TIP = 1
    FOREHEAD = 10
    CHIN = 152
    LEFT_EYE_INNER = 133
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263
    LEFT_IRIS = 468
    RIGHT_IRIS = 473

    def __init__(self, model_path: str = "models/face_landmarker.task"):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modello non trovato in: {model_path}")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
            running_mode=vision.RunningMode.IMAGE,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

        # Calibrazione e offset di riposo
        self.neutral_yaw: float = 0.0
        self.neutral_pitch: float = 0.0
        self.neutral_nose_x: float = 0.5
        self.neutral_nose_y: float = 0.5
        self.is_calibrated: bool = False

    def calibrate_center(self, yaw: float, pitch: float, nose_x: float, nose_y: float):
        """Imposta la posizione di riposo neutrale del paziente (zero del cursore)."""
        self.neutral_yaw = yaw
        self.neutral_pitch = pitch
        self.neutral_nose_x = nose_x
        self.neutral_nose_y = nose_y
        self.is_calibrated = True

    def _extract_euler_angles(self, matrix_4x4: np.ndarray) -> Tuple[float, float, float]:
        """
        Estrae gli angoli di Eulero (Yaw, Pitch, Roll in gradi)
        dalla matrice di rotazione rigida 3x3 di MediaPipe.
        """
        r = matrix_4x4[:3, :3]

        # Decomposizione rotazione (ordine Tait-Bryan ZYX o standard computer vision)
        sy = math.sqrt(r[0, 0] * r[0, 0] + r[1, 0] * r[1, 0])
        singular = sy < 1e-6

        if not singular:
            pitch = math.atan2(r[2, 1], r[2, 2])
            yaw = math.atan2(-r[2, 0], sy)
            roll = math.atan2(r[1, 0], r[0, 0])
        else:
            pitch = math.atan2(-r[1, 2], r[1, 1])
            yaw = math.atan2(-r[2, 0], sy)
            roll = 0.0

        return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)

    def process_frame(self, frame_bgr: np.ndarray) -> TrackerResult:
        """Elabora un frame video ed estrae posa, blendshapes e coordinate di puntamento."""
        h, w = frame_bgr.shape[:2]
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        result = self.detector.detect(mp_image)

        if not result.face_landmarks or len(result.face_landmarks) == 0:
            return TrackerResult(
                face_detected=False,
                cursor_raw_x=0.5,
                cursor_raw_y=0.5,
                yaw=0.0,
                pitch=0.0,
                roll=0.0,
                is_blinking=False,
                blink_score=0.0,
                jaw_open_score=0.0,
                smile_score=0.0,
                brow_down_score=0.0,
                iris_dx=0.0,
                iris_dy=0.0,
            )

        landmarks = result.face_landmarks[0]

        # 1. Calcolo Posa Cranica 3D dalla Matrice Nativa
        yaw, pitch, roll = 0.0, 0.0, 0.0
        if result.facial_transformation_matrixes and len(result.facial_transformation_matrixes) > 0:
            mat = np.array(result.facial_transformation_matrixes[0])
            yaw, pitch, roll = self._extract_euler_angles(mat)

        # 2. Punto di mira anatomico (Punta del Naso Landmark #1)
        nose = landmarks[self.NOSE_TIP]
        nose_x = nose.x
        nose_y = nose.y

        if not self.is_calibrated:
            self.calibrate_center(yaw, pitch, nose_x, nose_y)

        # 3. Analisi Blendshapes FACS native di Google MediaPipe
        blend_dict: Dict[str, float] = {}
        if result.face_blendshapes and len(result.face_blendshapes) > 0:
            for category in result.face_blendshapes[0]:
                blend_dict[category.category_name] = category.score

        blink_l = blend_dict.get("eyeBlinkLeft", 0.0)
        blink_r = blend_dict.get("eyeBlinkRight", 0.0)
        blink_score = max(blink_l, blink_r)
        # Clamping battito palpebrale naturale (se entrambe chiuse o ammiccamento significativo)
        is_blinking = (blink_l > 0.40 and blink_r > 0.40) or blink_score > 0.60

        jaw_open = blend_dict.get("jawOpen", 0.0)
        smile = max(blend_dict.get("mouthSmileLeft", 0.0), blend_dict.get("mouthSmileRight", 0.0))
        brow_down = max(blend_dict.get("browDownLeft", 0.0), blend_dict.get("browDownRight", 0.0))

        # 4. Calcolo Micro-Offset Iride (Gaze fine adjustment)
        iris_dx, iris_dy = 0.0, 0.0
        if len(landmarks) > self.RIGHT_IRIS:
            # Centro iride sinistra rispetto all'occhio sinistro
            l_iris = landmarks[self.LEFT_IRIS]
            l_inner = landmarks[self.LEFT_EYE_INNER]
            l_outer = landmarks[self.LEFT_EYE_OUTER]
            eye_width = abs(l_inner.x - l_outer.x) + 1e-6
            iris_dx = (l_iris.x - (l_inner.x + l_outer.x) * 0.5) / eye_width

        # Coordinate grezze relative al centro calibrato
        delta_x = nose_x - self.neutral_nose_x
        delta_y = nose_y - self.neutral_nose_y

        cursor_x = 0.5 + delta_x
        cursor_y = 0.5 + delta_y

        return TrackerResult(
            face_detected=True,
            cursor_raw_x=cursor_x,
            cursor_raw_y=cursor_y,
            yaw=yaw - self.neutral_yaw,
            pitch=pitch - self.neutral_pitch,
            roll=roll,
            is_blinking=is_blinking,
            blink_score=blink_score,
            jaw_open_score=jaw_open,
            smile_score=smile,
            brow_down_score=brow_down,
            iris_dx=iris_dx,
            iris_dy=iris_dy,
        )
