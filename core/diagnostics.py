"""
Modulo di Diagnostica Hardware Pre-Collaudo per Caregiver e Clinici.
Verifica lo stato e le prestazioni reali di:
1. Sensore Video (Webcam USB):
   - Negoziazione codec FourCC (MJPG vs YUY2)
   - Risoluzione effettiva
   - Benchmark FPS reali erogati (campionamento dinamico)
   - Analisi fotometrica della stanza (Luma medio e contrasto)
2. Dispositivi Audio (Microfono):
   - Verifica disponibilità e frequenze supportate
   - Stima dell'RMS del rumore di fondo della stanza
3. Score di Idoneità Clinica (0 - 100%) con consigli pratici per il caregiver.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np

try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except Exception:
    pass

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


def scan_cameras(max_tested: int = 3) -> List[Dict[str, Any]]:
    """Esegue la scansione degli indici webcam disponibili provando backend DirectShow e MSMF."""
    available = []
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "MediaFoundation"),
    ]

    for idx in range(max_tested):
        found = False
        for backend_id, backend_name in backends:
            try:
                cap = cv2.VideoCapture(idx, backend_id)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.shape[0] > 0:
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        available.append({
                            "index": idx,
                            "backend_id": backend_id,
                            "backend_name": backend_name,
                            "width": w,
                            "height": h,
                            "reported_fps": fps,
                        })
                        found = True
                        cap.release()
                        break
                    cap.release()
            except Exception:
                pass
        if not found:
            # Prova apertura generica come ultimo fallback
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        available.append({
                            "index": idx,
                            "backend_id": cv2.CAP_ANY,
                            "backend_name": "Standard Auto",
                            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                            "reported_fps": cap.get(cv2.CAP_PROP_FPS),
                        })
                    cap.release()
            except Exception:
                pass

    return available


def benchmark_webcam(camera_idx: int = 0, backend_id: int = cv2.CAP_DSHOW, target_frames: int = 40) -> Dict[str, Any]:
    """
    Esegue il benchmark approfondito della webcam:
    tenta lo sblocco a 60 FPS con codec MJPG e misura il framerate reale erogato.
    """
    res = {
        "success": False,
        "index": camera_idx,
        "width": 0,
        "height": 0,
        "actual_fps": 0.0,
        "mjpg_unlocked": False,
        "luma_mean": 0.0,
        "luma_status": "N/A",
        "error": None,
    }

    try:
        cap = cv2.VideoCapture(camera_idx, backend_id)
        if not cap.isOpened():
            # Fallback su backend generico
            cap = cv2.VideoCapture(camera_idx)
            if not cap.isOpened():
                res["error"] = f"Impossibile aprire la fotocamera all'indice {camera_idx}"
                return res

        # Tenta configurazione ottimale: 640x480 a 60 FPS con FourCC MJPG
        fourcc_mjpg = cv2.VideoWriter_fourcc(*"MJPG")
        cap.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 60)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Warmup (5 frame scartati per stabilizzare l'esposizione automatica)
        for _ in range(5):
            cap.read()

        # Benchmark framerate su target_frames
        timestamps = []
        luma_samples = []

        t_start = time.perf_counter()
        frames_read = 0

        for _ in range(target_frames):
            ret, frame = cap.read()
            t_frame = time.perf_counter()
            if ret and frame is not None:
                frames_read += 1
                timestamps.append(t_frame)
                # Calcolo Luma sub-sampled (luminanza Y = 0.299R + 0.587G + 0.114B)
                gray_sample = cv2.cvtColor(frame[::8, ::8], cv2.COLOR_BGR2GRAY)
                luma_samples.append(float(np.mean(gray_sample)))

        t_end = time.perf_counter()
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        total_time = t_end - t_start
        if frames_read > 5 and total_time > 0:
            actual_fps = round((frames_read - 1) / (timestamps[-1] - timestamps[0]), 1)
        else:
            actual_fps = 0.0

        mean_luma = round(float(np.mean(luma_samples)), 1) if luma_samples else 0.0

        if mean_luma < 25.0:
            luma_status = "Bassa Luminosità (Rischio dimezzamento FPS)"
        elif mean_luma > 215.0:
            luma_status = "Sovraesposizione / Controluce Eccessivo"
        else:
            luma_status = "Ottimale (Illuminazione Ideale)"

        res["success"] = True
        res["width"] = actual_width
        res["height"] = actual_height
        res["actual_fps"] = actual_fps
        res["mjpg_unlocked"] = actual_fps >= 45.0
        res["luma_mean"] = mean_luma
        res["luma_status"] = luma_status

    except Exception as e:
        res["error"] = str(e)

    return res


def benchmark_audio(duration: float = 0.5) -> Dict[str, Any]:
    """Analizza i dispositivi di input audio e misura il rumore ambientale di fondo in RMS/dB."""
    res = {
        "available": False,
        "input_devices_count": 0,
        "default_device_name": "Nessun dispositivo",
        "default_sample_rate": 0,
        "ambient_noise_rms": 0.0,
        "noise_db": -99.0,
        "status": "Non disponibile",
    }

    if not HAS_SOUNDDEVICE:
        return res

    try:
        devices = sd.query_devices()
        input_devs = [d for d in devices if d.get("max_input_channels", 0) > 0]
        res["input_devices_count"] = len(input_devs)

        default_in = sd.query_devices(kind="input")
        if default_in:
            res["available"] = True
            res["default_device_name"] = default_in.get("name", "Microfono Default")
            sr = int(default_in.get("default_samplerate", 16000))
            res["default_sample_rate"] = sr

            # Campionamento breve per misurare il rumore ambientale reale
            recording = sd.rec(int(duration * sr), samplerate=sr, channels=1, dtype="float32")
            sd.wait()

            if recording.size > 0:
                rms = float(np.sqrt(np.mean(recording**2)))
                res["ambient_noise_rms"] = round(rms, 4)
                db = 20.0 * np.log10(max(1e-5, rms))
                res["noise_db"] = round(float(db), 1)

                if rms < 0.005:
                    res["status"] = "Molto Silenzioso (Perfetto per trigger vocale/soffio)"
                elif rms < 0.060:
                    res["status"] = "Normale / Moderato (Idoneo)"
                else:
                    res["status"] = "Ambiente Rumoroso (Consigliata calibrazione audio 2s)"
    except Exception as e:
        res["status"] = f"Errore: {e}"

    return res


def run_full_diagnostics() -> Dict[str, Any]:
    """Esegue la suite diagnostica completa e calcola il punteggio clinico."""
    t_start = time.perf_counter()

    cams = scan_cameras(max_tested=3)
    cam_bench = None
    if cams:
        best_cam = cams[0]
        cam_bench = benchmark_webcam(best_cam["index"], best_cam["backend_id"])
    else:
        cam_bench = {
            "success": False,
            "index": -1,
            "actual_fps": 0.0,
            "width": 0,
            "height": 0,
            "mjpg_unlocked": False,
            "luma_mean": 0.0,
            "luma_status": "Fotocamera non rilevata",
            "error": "Nessuna webcam USB rilevata sul computer",
        }

    audio_bench = benchmark_audio(duration=0.4)

    # Calcolo Score Clinico (0 - 100)
    score = 0
    recommendations: List[str] = []

    # 1. Punteggio Video (Max 65 punti)
    if cam_bench["success"]:
        fps = cam_bench["actual_fps"]
        if fps >= 55.0:
            score += 45
        elif fps >= 28.0:
            score += 30
            recommendations.append("La webcam eroga ~30 FPS invece di 60 FPS: prova a collegarla a una porta USB 3.0 posteriore diretta.")
        elif fps >= 15.0:
            score += 15
            recommendations.append("Framerate molto basso (< 25 FPS): aumenta la luce frontale nella stanza per disattivare l'auto-esposizione prolungata.")
        else:
            score += 5
            recommendations.append("Framerate critico (< 15 FPS): verificare driver della fotocamera o cavo USB.")

        # Valutazione Luce (Max 20 punti)
        luma = cam_bench["luma_mean"]
        if 40.0 <= luma <= 180.0:
            score += 20
        elif luma < 40.0:
            score += 5
            recommendations.append("Ambiente buio (Luma < 40): posiziona una lampada da tavolo o luce diffusa di fronte al viso del paziente.")
        else:
            score += 8
            recommendations.append("Forte riflesso o controluce (Luma > 180): evita finestre aperte o lampade alle spalle del paziente.")
    else:
        recommendations.append("Nessuna webcam rilevata: collega la webcam USB e riavvia il test. In assenza di camera, l'app avvierà la modalità Demo.")

    # 2. Punteggio Audio (Max 25 punti)
    if audio_bench["available"]:
        score += 15
        if audio_bench["ambient_noise_rms"] < 0.06:
            score += 10
        else:
            score += 4
            recommendations.append("Rumore ambientale elevato: se usi il trigger vocale/soffio, esegui l'Auto-Calibrazione 2s nel pannello.")
    else:
        recommendations.append("Nessun microfono attivo rilevato: il trigger vocale/soffio sarà disabilitato (il Dwell Clicker rimane pienamente funzionante).")

    # 3. Punteggio Piattaforma Win32 (Max 10 punti bonus)
    score += 10
    score = min(100, max(0, score))

    if score >= 80:
        verdict = "OTTIMALE (Esperienza Fluida a 60 FPS)"
        badge_color = "#10B981"
    elif score >= 50:
        verdict = "ACCETTABILE (Utilizzabile con Accorgimenti)"
        badge_color = "#F59E0B"
    else:
        verdict = "CRITICO / CONFIGURAZIONE RICHIESTA"
        badge_color = "#EF4444"

    if not recommendations:
        recommendations.append("Tutti i parametri hardware e ambientali sono perfetti per il collaudo clinico.")

    duration_ms = round((time.perf_counter() - t_start) * 1000.0, 1)

    return {
        "score": score,
        "verdict": verdict,
        "badge_color": badge_color,
        "duration_ms": duration_ms,
        "cameras_detected": len(cams),
        "active_camera": cam_bench,
        "audio": audio_bench,
        "recommendations": recommendations,
    }


def format_diagnostic_report_text(diag: Dict[str, Any]) -> str:
    """Formatta i risultati in un report di testo chiaro e compatibile con tutti i terminali Windows."""
    lines = [
        "=" * 68,
        "  STEADYMOTION AI v3.0 -- REPORT DIAGNOSTICO HARDWARE & AMBIENTE",
        "=" * 68,
        f"Data/Ora: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Durata Analisi: {diag['duration_ms']} ms",
        f"VERDETTO FINALE: {diag['verdict']} (Punteggio: {diag['score']} / 100)",
        "-" * 68,
        "",
        "1. ANALISI SENSORE VIDEO (WEBCAM):",
    ]

    cam = diag["active_camera"]
    if cam["success"]:
        lines.extend([
            f"   * Stato: Rilevata e Funzionante (Indice: {cam['index']})",
            f"   * Risoluzione: {cam['width']} x {cam['height']} px",
            f"   * Framerate Reale Misurato: {cam['actual_fps']} FPS",
            f"   * Codec MJPG 60 Hz Sbloccato: {'SI [OK]' if cam['mjpg_unlocked'] else 'NO [!]'}",
            f"   * Luminanza Media (Luma): {cam['luma_mean']} nit",
            f"   * Valutazione Luce: {cam['luma_status']}",
        ])
    else:
        lines.extend([
            f"   * Stato: NON RILEVATA [ASSENTE]",
            f"   * Errore: {cam.get('error', 'Nessun flusso video')}",
            f"   * Modalita Fallback: Simulazione Demo Sintetica a 60 FPS attiva",
        ])

    lines.extend([
        "",
        "2. ANALISI DISPOSITIVI AUDIO (MICROFONO):",
    ])
    aud = diag["audio"]
    if aud["available"]:
        lines.extend([
            f"   * Dispositivo Predefinito: {aud['default_device_name']}",
            f"   * Frequenza di Campionamento: {aud['default_sample_rate']} Hz",
            f"   * Livello Rumore di Fondo: {aud['noise_db']} dB (RMS: {aud['ambient_noise_rms']})",
            f"   * Valutazione Rumore: {aud['status']}",
        ])
    else:
        lines.extend([
            "   * Stato: Nessun microfono attivo rilevato",
        ])

    lines.extend([
        "",
        "3. CONSIGLI PRATICI PER IL CAREGIVER:",
    ])
    for rec in diag["recommendations"]:
        lines.append(f"   -> {rec}")

    lines.extend([
        "",
        "=" * 68,
        "  Report pronto per assistenza tecnica o collaudo clinico",
        "=" * 68,
    ])

    return "\n".join(lines)
