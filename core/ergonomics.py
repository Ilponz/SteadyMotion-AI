"""
Modulo di Monitoraggio Ergonomico & Affaticamento Muscolare Cervicale (Ergonomics Monitor).
Progettato specificamente per pazienti con patologie neuro-muscolari (SLA, Parkinson, distonie):
1. Rileva l'affaticamento posturale progressivo del collo (Head-Drop / abbassamento mento e Tilt laterale).
2. Assorbimento Dinamico del Drift Posturale Bi-Assiale (Slow Baseline Bias Absorption):
   adatta dolcemente la linea di zero ai lenti rilassamenti posturali sia in pitch che in yaw (< 1.5 deg/s),
   impedendo che il paziente debba forzare i muscoli estensori del collo per raggiungere lo schermo alto o laterale.
3. Notifiche Edge-Triggered & Zero Churn: genera alert clinici transizionali privi di duplicazioni a 60 Hz
   e mantiene una struttura pre-allocata in memoria per azzerare il sovraccarico del Garbage Collector.
"""

from dataclasses import dataclass
import math
import time
from typing import Optional


@dataclass
class ErgonomicsStatus:
    is_fatigued: bool = False
    fatigue_reason: str = "Nessuna"
    pitch_drift_deg: float = 0.0
    roll_drift_deg: float = 0.0
    yaw_drift_deg: float = 0.0
    should_suggest_recenter: bool = False
    is_new_fatigue_alert: bool = False
    pitch_bias_compensation: float = 0.0
    yaw_bias_compensation: float = 0.0
    session_duration_sec: float = 0.0


class ErgonomicsMonitor:
    """Monitor biometrico di postura ergonomica cervicale e affaticamento a zero allocazioni heap."""

    def __init__(
        self,
        head_drop_threshold_deg: float = 12.0,
        tilt_threshold_deg: float = 14.0,
        sustained_duration_sec: float = 15.0,
        baseline_absorption_rate: float = 0.015,  # Tasso di compensazione drift posturale lento
    ):
        self.head_drop_thresh = float(head_drop_threshold_deg)
        self.tilt_thresh = float(tilt_threshold_deg)
        self.sustained_dur = float(sustained_duration_sec)
        self.absorption_rate = float(baseline_absorption_rate)

        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None

        # Linea base posturale di riferimento (neutra iniziale)
        self.ref_yaw: Optional[float] = None
        self.ref_pitch: Optional[float] = None
        self.ref_roll: Optional[float] = None

        # Linea base adattiva a lungo termine (Moving Average lenta)
        self.adaptive_pitch_bias: float = 0.0
        self.adaptive_yaw_bias: float = 0.0

        # Tracciamento velocità angolare per discriminare movimenti volontari da drift lento
        self._prev_pitch: Optional[float] = None
        self._prev_yaw: Optional[float] = None

        # Timer di persistenza dell'anomalia posturale
        self.fatigue_start_time: Optional[float] = None
        self.last_recenter_prompt_time: float = 0.0
        self._prev_is_fatigued: bool = False

        # Struttura dati pre-allocata per Zero Heap Churn a 60 Hz
        self._status = ErgonomicsStatus()

    def reset_reference(self, yaw: float = 0.0, pitch: float = 0.0, roll: float = 0.0):
        """Imposta la postura neutra di riferimento (chiamata contestualmente a F12)."""
        self.ref_yaw = float(yaw)
        self.ref_pitch = float(pitch)
        self.ref_roll = float(roll)
        self.adaptive_pitch_bias = 0.0
        self.adaptive_yaw_bias = 0.0
        self._prev_pitch = None
        self._prev_yaw = None
        self.fatigue_start_time = None
        self._prev_is_fatigued = False

    def update(
        self,
        yaw_deg: float,
        pitch_deg: float,
        roll_deg: float,
        now: Optional[float] = None,
    ) -> ErgonomicsStatus:
        if now is None:
            now = time.perf_counter()

        if self.start_time is None:
            self.start_time = now

        if self.ref_yaw is None:
            self.reset_reference(yaw_deg, pitch_deg, roll_deg)

        dt = 0.016 if self.last_update_time is None else max(0.001, min(0.2, now - self.last_update_time))
        self.last_update_time = now

        session_dur = now - self.start_time

        # Deviazione rispetto alla postura neutra iniziale
        d_yaw = yaw_deg - self.ref_yaw
        d_pitch = pitch_deg - self.ref_pitch
        d_roll = roll_deg - self.ref_roll

        # 1. Assorbimento dinamico del drift lento (Head-Drop / Rilassamento naturale)
        # Se la velocità di rotazione del capo è bassa (< 1.5 deg/s), assorbe dolcemente il bias
        prev_p = self._prev_pitch if self._prev_pitch is not None else pitch_deg
        prev_y = self._prev_yaw if self._prev_yaw is not None else yaw_deg
        head_pitch_vel = abs(pitch_deg - prev_p) / dt
        head_yaw_vel = abs(yaw_deg - prev_y) / dt
        self._prev_pitch = pitch_deg
        self._prev_yaw = yaw_deg

        if head_pitch_vel < 1.5:
            alpha_pitch = min(0.2, self.absorption_rate * dt)
            self.adaptive_pitch_bias += (d_pitch - self.adaptive_pitch_bias) * alpha_pitch

        if head_yaw_vel < 1.5:
            alpha_yaw = min(0.2, self.absorption_rate * dt)
            self.adaptive_yaw_bias += (d_yaw - self.adaptive_yaw_bias) * alpha_yaw

        # 2. Rilevamento della fatica cervicale persistente
        # d_pitch negativo = testa abbassata (mento verso il petto / Head-Drop)
        is_head_dropped = (d_pitch < -self.head_drop_thresh)
        is_tilted = (abs(d_roll) > self.tilt_thresh)

        is_currently_anomalous = is_head_dropped or is_tilted

        reason = "Nessuna"
        if is_head_dropped and is_tilted:
            reason = "Caduta Cefalica + Inclinazione Laterale"
        elif is_head_dropped:
            reason = "Caduta Cefalica Anteriore (Head-Drop)"
        elif is_tilted:
            reason = "Inclinazione Laterale Eccessiva (Tilt)"

        is_fatigued = False
        should_recenter = False

        if is_currently_anomalous:
            if self.fatigue_start_time is None:
                self.fatigue_start_time = now
            elif (now - self.fatigue_start_time) >= self.sustained_dur:
                is_fatigued = True
                if (now - self.last_recenter_prompt_time) > 30.0:
                    should_recenter = True
                    self.last_recenter_prompt_time = now
        else:
            self.fatigue_start_time = None

        # Rilevamento edge-triggered dell'alert (solo al fronte di salita o prompt periodico)
        is_new_fatigue_alert = (is_fatigued and not self._prev_is_fatigued) or should_recenter
        self._prev_is_fatigued = is_fatigued

        # Aggiornamento in-place della struttura pre-allocata (Zero Heap Churn)
        st = self._status
        st.is_fatigued = is_fatigued
        st.fatigue_reason = reason
        st.pitch_drift_deg = d_pitch
        st.roll_drift_deg = d_roll
        st.yaw_drift_deg = d_yaw
        st.should_suggest_recenter = should_recenter
        st.is_new_fatigue_alert = is_new_fatigue_alert
        st.pitch_bias_compensation = self.adaptive_pitch_bias
        st.yaw_bias_compensation = self.adaptive_yaw_bias
        st.session_duration_sec = session_dur

        return st
