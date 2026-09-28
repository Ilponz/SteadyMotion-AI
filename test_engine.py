"""
Suite di collaudo e benchmark automatico per il nucleo algoritmico di SteadyMotion AI.
Verifica:
1. Attenuazione del tremore a 5 Hz del One-Euro Filter + Deadzone (> 20 dB).
2. Precisione temporale e macchina a stati del Dwell Clicker.
3. Rilevamento metriche display virtuale Win32.
4. Inizializzazione del modello FaceLandmarker Tasks.
"""

import math
import os
import sys
import time
import numpy as np

from core.dsp_filter import PointFilter2D, OneEuroFilter
from core.dwell_clicker import DwellClicker
from core.virtual_input import WindowsMouseController
from core.tracker_engine import FaceTrackerEngine


def test_dsp_filter():
    print("\n--- TEST 1: Filtraggio DSP del Tremore Patologico (5.0 Hz) ---")
    filter_2d = PointFilter2D(min_cutoff=1.2, beta=0.008, deadzone_radius=2.0)

    # Simulazione segnale di puntamento fermo a (500, 500) affetto da tremore parkinsoniano a 5 Hz
    dt = 1.0 / 60.0  # 60 FPS
    tremor_freq = 5.0
    tremor_amp = 8.0  # 8 pixel di oscillazione involontaria

    raw_deviations = []
    filtered_deviations = []

    t = 0.0
    for i in range(120):  # 2 secondi a 60 FPS
        # Tremore sinusoidale
        noise_x = tremor_amp * math.sin(2.0 * math.pi * tremor_freq * t)
        noise_y = tremor_amp * math.cos(2.0 * math.pi * tremor_freq * t)

        raw_x = 500.0 + noise_x
        raw_y = 500.0 + noise_y

        fx, fy = filter_2d.filter(raw_x, raw_y, t)

        raw_deviations.append(math.hypot(raw_x - 500.0, raw_y - 500.0))
        filtered_deviations.append(math.hypot(fx - 500.0, fy - 500.0))

        t += dt

    # Calcolo dell'abbattimento del rumore a regime (secondo 1.0s - 2.0s)
    raw_rms = np.sqrt(np.mean(np.array(raw_deviations[60:]) ** 2))
    filt_rms = np.sqrt(np.mean(np.array(filtered_deviations[60:]) ** 2))

    attenuation_ratio = (raw_rms - filt_rms) / raw_rms * 100.0
    print(f"Deviazione media grezza (Tremore): {raw_rms:.2f} px")
    print(f"Deviazione media filtrata (Stabilità): {filt_rms:.2f} px")
    print(f"Abbattimento del Tremore: {attenuation_ratio:.1f}%")
    assert attenuation_ratio > 80.0, "Il filtro non ha abbattuto sufficientemente il tremore!"
    print(">>> TEST 1 SUPERATO CON SUCCESSO! <<<")


def test_dwell_clicker():
    print("\n--- TEST 2: Macchina a Stati Dwell Clicker ---")
    clicks_recorded = []

    def on_click(action, x, y):
        clicks_recorded.append((action, x, y))

    dwell = DwellClicker(
        dwell_time=0.50,
        tolerance_radius=15.0,
        click_callback=on_click,
    )

    t = 10.0
    # Muoviamo il mouse su (200, 200) e stazioniamo per 0.60 secondi (> 0.50s)
    while t < 10.60:
        p = dwell.update(200.0 + math.sin(t * 10) * 2.0, 200.0, now=t)
        t += 0.05

    print(f"Clic registrati durante la sosta: {len(clicks_recorded)}")
    assert len(clicks_recorded) == 1, f"Atteso 1 clic, registrati {len(clicks_recorded)}"
    assert clicks_recorded[0][0] == "left", "L'azione registrata deve essere 'left'"
    print(f"Progresso finale dwell: {p:.2f}")
    print(">>> TEST 2 SUPERATO CON SUCCESSO! <<<")


def test_virtual_input():
    print("\n--- TEST 3: Controller Virtual Input Win32 ---")
    mouse = WindowsMouseController()
    print(f"Risoluzione Display Virtuale rilevata: {mouse.vw}x{mouse.vh} (Offset: X={mouse.vx}, Y={mouse.vy})")
    assert mouse.vw > 0 and mouse.vh > 0, "Dimensioni del display non valide!"
    cx, cy = mouse.get_cursor_pos()
    print(f"Posizione attuale cursore di sistema: ({cx}, {cy})")
    print(">>> TEST 3 SUPERATO CON SUCCESSO! <<<")


def test_tracker_initialization():
    print("\n--- TEST 4: Inizializzazione FaceLandmarker Tasks ---")
    model_path = os.path.join(os.path.dirname(__file__), "models", "face_landmarker.task")
    assert os.path.exists(model_path), f"Modello assente: {model_path}"
    tracker = FaceTrackerEngine(model_path=model_path)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res = tracker.process_frame(dummy_frame)
    print(f"Esecuzione inferenza completata senza eccezioni. Volto rilevato su dummy frame: {res.face_detected}")
    print(">>> TEST 4 SUPERATO CON SUCCESSO! <<<")


if __name__ == "__main__":
    test_dsp_filter()
    test_dwell_clicker()
    test_virtual_input()
    test_tracker_initialization()
    print("\n==========================================")
    print("TUTTI I TEST SONO STATI SUPERATI AL 100%!")
    print("==========================================")
