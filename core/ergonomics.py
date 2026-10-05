"""
Modulo di Monitoraggio Ergonomico & Affaticamento Muscolare Cervicale (Ergonomics Monitor).
Progettato specificamente per pazienti con patologie neuro-muscolari (SLA, Parkinson, distonie):
1. Rileva l'affaticamento posturale progressivo del collo (Head-Drop / abbassamento mento e Tilt laterale).
2. Assorbimento Dinamico del Drift Posturale (Slow Baseline Bias Absorption):
   adatta dolcemente la linea di zero ai lenti rilassamenti posturali (< 0.2 deg/s),
   impedendo che il paziente debba forzare i muscoli estensori del collo per raggiungere lo schermo alto.
3. Genera avvisi discreti di sovraccarico ergonomico per il caregiver o il paziente (suggerimento pausa o F12).
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
    pitch_bias_compensation: float = 0.0
    session_duration_sec: float = 0.0


class ErgonomicsMonitor:
    """Monitor biometrico di postura ergonomica cervicale e affaticamento."""

    def __init__(
        self,
        head_drop_threshold_deg: float = 12.0,
        tilt_threshold_deg: float = 14.0,
        sustained_duration_sec: float = 15.0,
        baseline_absorption_rate: float = 0.015,  # Tasso di compensazione drift posturale lento
    ):
        self.head_drop_thresh = head_drop_threshold_deg
        self.tilt_thresh = tilt_threshold_deg
        self.sustained_dur = sustained_duration_sec
        self.absorption_rate = baseline_absorption_rate

        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None

        # Linea base posturale di riferimento (neutra iniziale)
        self.ref_yaw: Optional[float] = None
        self.ref_pitch: Optional[float] = None
        self.ref_roll: Optional[float] = None

        # Linea base adattiva a lungo termine (Moving Average lenta)
        self.adaptive_pitch_bias: float = 0.0

        # Timer di persistenza dell'anomalia posturale
        self.fatigue_start_time: Optional[float] = None
        self.last_recenter_prompt_time: float = 0.0

    def reset_reference(self, yaw: float = 0.0, pitch: float = 0.0, roll: float = 0.0):
        """Imposta la postura neutra di riferimento (chiamata contestualmente a F12)."""
        self.ref_yaw = yaw
        self.ref_pitch = pitch
        self.ref_roll = roll
        self.adaptive_pitch_bias = 0.0
        self.fatigue_start_time = None

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

        # 1. Assorbimento dinamico del drift lento (Head-Droop rilassamento naturale)
        # Se la velocità di rotazione del capo è bassa (< 1.5 deg/s), assorbe dolcemente il bias
        prev_p = self.prev_pitch if hasattr(self, "prev_pitch") and self.prev_pitch is not None else pitch_deg
        head_vel = abs(pitch_deg - prev_p) / dt
        self.prev_pitch = pitch_deg

        if head_vel < 1.5:
            alpha = min(0.2, self.absorption_rate * dt)
            self.adaptive_pitch_bias += (d_pitch - self.adaptive_pitch_bias) * alpha

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

        return ErgonomicsStatus(
            is_fatigued=is_fatigued,
            fatigue_reason=reason,
            pitch_drift_deg=d_pitch,
            roll_drift_deg=d_roll,
            yaw_drift_deg=d_yaw,
            should_suggest_recenter=should_recenter,
            pitch_bias_compensation=self.adaptive_pitch_bias,
            session_duration_sec=session_dur,
        )
