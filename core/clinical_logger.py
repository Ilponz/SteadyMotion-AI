"""
Modulo di Telemetria Clinica & Cartella Riabilitativa Digitale (Clinical Session Logger).
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico & Sanitario:
Fornire a logopedisti, terapisti occupazionali e neurofisiatri metriche quantitative e oggettive
per documentare l'efficacia dell'ausilio, l'evoluzione del controllo motorio cefalico,
il tasso di risparmio di sforzo (KSR) e i pattern di affaticamento per le cartelle cliniche
e le relazioni di prescrizione/collaudo (ASL / SSN / NHS).

Caratteristiche:
1. Zero Overhead a 60 FPS: contatori atomici in RAM, nessun I/O su disco nel loop real-time.
2. Metriche Motorie: Clic Dwell completati, Dwell abortiti da spasmi, distanza percorsa dal puntatore.
3. Metriche di Comunicazione Aumentativa (CAA): Caratteri digitati, suggerimenti predittivi impiegati,
   Keystroke Savings Rate (KSR %).
4. Metriche Ergonomiche & Affaticamento: Eventi di Head-Drop (caduta cefalica) e Tilt laterale severo.
5. Generazione automatica di Report Clinico formattato in Markdown e JSON.
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class ClinicalSessionLogger:
    """Gestore della telemetria clinica e generatore di relazioni riabilitative."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = reports_dir
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_timestamp = time.time()
        self.start_time_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Gestione tempo di tracciamento vs standby
        self._last_state_time = self.start_timestamp
        self.is_tracking_active = False
        self.active_tracking_sec = 0.0
        self.standby_sec = 0.0

        # Metriche Motorie
        self.dwell_clicks_completed: int = 0
        self.dwell_aborted_spasms: int = 0
        self.spasm_shock_events: int = 0
        self.copilot_overrides: int = 0
        self.acoustic_clicks: int = 0
        self.gesture_clicks: int = 0
        self.total_cursor_distance_px: float = 0.0
        self._last_cursor_pos: Optional[Tuple[float, float]] = None

        # Metriche Comunicazione Aumentativa (CAA)
        self.keyboard_raw_keystrokes: int = 0
        self.keyboard_words_predicted: int = 0
        self.keyboard_chars_saved: int = 0

        # Metriche Ergonomia
        self.head_drop_alerts: int = 0
        self.lateral_tilt_alerts: int = 0

        # Valutazioni Standardizzate ISO 9241-9 (Legge di Fitts & Throughput)
        self.fitts_assessments: List[Dict[str, Any]] = []

    def set_tracking_state(self, is_active: bool, now: Optional[float] = None):
        """Aggiorna lo stato di tracciamento attivo vs standby accumulando i tempi trascorsi."""
        t_now = now or time.time()
        dt = max(0.0, t_now - self._last_state_time)
        if self.is_tracking_active:
            self.active_tracking_sec += dt
        else:
            self.standby_sec += dt

        self.is_tracking_active = is_active
        self._last_state_time = t_now

    def record_cursor_movement(self, x: float, y: float):
        """Registra la distanza euclidea sub-pixel percorsa dal cursore (odometria cefalica)."""
        if not self.is_tracking_active:
            return
        if self._last_cursor_pos is not None:
            dx = x - self._last_cursor_pos[0]
            dy = y - self._last_cursor_pos[1]
            dist = (dx * dx + dy * dy) ** 0.5
            # Filtro anti-teletrasporto (salto di ricentratura > 500 px non viene contato)
            if dist < 500.0:
                self.total_cursor_distance_px += dist
        self._last_cursor_pos = (x, y)

    def record_dwell_click(self, action: str = "left"):
        """Registra un clic a sosta (Dwell) completato con successo."""
        self.dwell_clicks_completed += 1

    def record_dwell_aborted(self):
        """Registra un dwell interrotto da spasmo o tremore (progress decrescente)."""
        self.dwell_aborted_spasms += 1

    def record_spasm_shock(self):
        """Registra un picco di spasmo mioclonico o scatto acuto involontario ad alta velocità."""
        self.spasm_shock_events += 1

    def record_copilot_override(self):
        """Registra un intervento del caregiver con mouse fisico."""
        self.copilot_overrides += 1

    def record_acoustic_click(self):
        """Registra un clic ausiliario ad attivazione vocale/respiratoria."""
        self.acoustic_clicks += 1

    def record_gesture_click(self, gesture: str):
        """Registra un clic azionato da gesto facciale (jaw_open / smile / brow)."""
        self.gesture_clicks += 1

    def record_typing(self, raw_chars: int = 1):
        """Registra caratteri digitati individualmente sulla tastiera."""
        self.keyboard_raw_keystrokes += max(1, raw_chars)

    def record_prediction_used(self, full_word: str, prefix_len: int = 0):
        """
        Registra l'uso di un completamento predittivo rapido.
        Calcola i caratteri risparmiati rispetto alla digitazione completa + spazio.
        """
        self.keyboard_words_predicted += 1
        word_len = len(full_word) + 1  # include spazio automatico
        # Caratteri risparmiati = lunghezza totale parola - prefisso già digitato - 1 tocco selezione
        saved = max(0, word_len - prefix_len - 1)
        self.keyboard_chars_saved += saved

    def record_ergonomic_alert(self, reason: str):
        """Registra un'anomalia posturale cervicale sostenuta."""
        if "Head-Drop" in reason or "Caduta" in reason:
            self.head_drop_alerts += 1
        elif "Tilt" in reason or "Inclinazione" in reason:
            self.lateral_tilt_alerts += 1

    def record_fitts_assessment(self, fitts_summary: Dict[str, Any]):
        """
        Registra una valutazione standardizzata ISO 9241-9 / Legge di Fitts.
        Include throughput (bit/s), MT (s), errore % ed efficacia (TPe).
        """
        if isinstance(fitts_summary, dict) and fitts_summary:
            self.fitts_assessments.append(dict(fitts_summary))

    def get_ksr(self) -> float:
        """
        Calcola il Keystroke Savings Rate (KSR %):
        KSR = (Caratteri Risparmiati / Caratteri Totali Equivalenti) * 100
        """
        total_keystrokes_needed = self.keyboard_raw_keystrokes + self.keyboard_chars_saved
        if total_keystrokes_needed <= 0:
            return 0.0
        return (self.keyboard_chars_saved / total_keystrokes_needed) * 100.0

    def get_session_summary(self, now: Optional[float] = None) -> Dict[str, Any]:
        """Restituisce il riepilogo clinico strutturato della sessione corrente."""
        t_now = now or time.time()
        # Flush temporale dello stato attuale
        dt = max(0.0, t_now - self._last_state_time)
        active = self.active_tracking_sec + (dt if self.is_tracking_active else 0.0)
        standby = self.standby_sec + (dt if not self.is_tracking_active else 0.0)
        total_dur = active + standby

        total_clicks = (
            self.dwell_clicks_completed
            + self.acoustic_clicks
            + self.gesture_clicks
        )

        dwell_success_rate = 0.0
        total_dwell_attempts = self.dwell_clicks_completed + self.dwell_aborted_spasms
        if total_dwell_attempts > 0:
            dwell_success_rate = (self.dwell_clicks_completed / total_dwell_attempts) * 100.0

        return {
            "session_id": self.session_id,
            "start_time": self.start_time_iso,
            "duration_total_sec": round(total_dur, 1),
            "duration_active_sec": round(active, 1),
            "duration_standby_sec": round(standby, 1),
            "active_ratio_pct": round((active / total_dur * 100.0) if total_dur > 0 else 0.0, 1),
            "motor_metrics": {
                "total_clicks": total_clicks,
                "dwell_clicks": self.dwell_clicks_completed,
                "dwell_aborted_spasms": self.dwell_aborted_spasms,
                "spasm_shock_events": self.spasm_shock_events,
                "dwell_success_rate_pct": round(dwell_success_rate, 1),
                "cursor_distance_px": round(self.total_cursor_distance_px, 1),
                "cursor_distance_meters_approx": round(self.total_cursor_distance_px * 0.000264583, 2),  # ~96 DPI
                "copilot_caregiver_interventions": self.copilot_overrides,
                "acoustic_clicks": self.acoustic_clicks,
                "gesture_clicks": self.gesture_clicks,
            },
            "aac_metrics": {
                "raw_keystrokes": self.keyboard_raw_keystrokes,
                "words_predicted": self.keyboard_words_predicted,
                "chars_saved": self.keyboard_chars_saved,
                "ksr_pct": round(self.get_ksr(), 1),
            },
            "ergonomic_metrics": {
                "head_drop_alerts": self.head_drop_alerts,
                "lateral_tilt_alerts": self.lateral_tilt_alerts,
                "total_posture_warnings": self.head_drop_alerts + self.lateral_tilt_alerts,
            },
            "fitts_assessment": {
                "assessments_count": len(self.fitts_assessments),
                "latest": self.fitts_assessments[-1] if self.fitts_assessments else None,
                "best_throughput_bps": round(max([a.get("mean_throughput_bps", 0.0) for a in self.fitts_assessments]), 2) if self.fitts_assessments else 0.0,
                "best_effective_throughput_tpe": round(max([a.get("effective_throughput_tpe", 0.0) for a in self.fitts_assessments]), 2) if self.fitts_assessments else 0.0,
                "mean_overall_throughput_bps": round(sum([a.get("mean_throughput_bps", 0.0) for a in self.fitts_assessments]) / len(self.fitts_assessments), 2) if self.fitts_assessments else 0.0,
            } if self.fitts_assessments else None,
        }

    def generate_markdown_report(self, patient_id: str = "Paziente-Anonimo", notes: str = "") -> str:
        """Genera un report formattato in Markdown per logopedisti e cartella clinica."""
        s = self.get_session_summary()
        m = s["motor_metrics"]
        a = s["aac_metrics"]
        e = s["ergonomic_metrics"]
        f_data = s.get("fitts_assessment")

        fitts_section = ""
        if f_data and f_data.get("latest"):
            f = f_data["latest"]
            fitts_section = f"""
---

### 4. 📐 Valutazione Ergonomica Standardizzata ISO 9241-9 (Legge di Fitts)
| Parametro Standardizzato ISO 9241-9 | Valore Rilevato | Valutazione / Riferimento Clinico |
| :--- | :--- | :--- |
| **Throughput Nominale (TP)** | **{f.get('mean_throughput_bps', 0.0)} bit/s** | Capacità del canale informativo motorio |
| **Throughput Effettivo (TPe)** | **{f.get('effective_throughput_tpe', 0.0)} bit/s** | Corretto con dispersione spaziale (We = 4.133 · σ) |
| **Tempo Medio di Movimento (MT)** | {f.get('mean_movement_time_sec', 0.0)} s | Latenza motoria tra bersagli |
| **Ampiezza Bersaglio Effettiva (We)** | {f.get('effective_target_width_we', 0.0)} px | Precisione spaziale (target 4% error rate) |
| **Indice di Difficoltà Nominale (ID)** | {f.get('mean_index_of_difficulty', 0.0)} bit | Difficoltà del compito visuo-motorio |
| **Indice di Difficoltà Effettivo (IDe)** | {f.get('effective_index_of_difficulty_ide', 0.0)} bit | Difficoltà effettiva percepita dal paziente |
| **Tasso di Errore** | {f.get('error_rate_pct', 0.0)}% | Clic fuori bersaglio o interruzioni da spasmo |
| **Dispersione Endpoint (σ)** | {f.get('endpoint_dispersion_sigma_px', 0.0)} px | Deviazione standard dei punti di arresto |
| **Conformità Normativa** | {f.get('iso_conformance', 'ISO 9241-9 / ISO 9241-411')} | Standard internazionale non-keyboard input |
"""

        md = f"""# 🏥 STEADYMOTION AI — RELAZIONE CLINICA DI SESSIONE

**Identificativo Sessione:** `{s['session_id']}`  
**Data e Ora Inizio:** {s['start_time']}  
**Identificativo Paziente:** `{patient_id}`  
**Durata Totale Sessione:** {s['duration_total_sec']} s ({round(s['duration_total_sec'] / 60.0, 1)} min)  
**Tempo Tracciamento Attivo:** {s['duration_active_sec']} s ({s['active_ratio_pct']}% del tempo)  

---

### 1. 🎯 Efficienza Motoria & Controllo Cefalico
| Parametro Motorio | Valore Rilevato | Valutazione Clinica |
| :--- | :--- | :--- |
| **Clic Totali Eseguiti** | **{m['total_clicks']}** | Interazioni confermate con successo |
| **Clic Dwell a Sosta** | {m['dwell_clicks']} | Metodo primario di puntamento |
| **Dwell Interrotti da Spasmi** | {m['dwell_aborted_spasms']} | Indice di tremore o distonia transitoria |
| **Scatti Spasmodici Acuti (Shock)** | {m['spasm_shock_events']} | Spasmi mioclonici a picco di velocità |
| **Tasso Successo Dwell** | **{m['dwell_success_rate_pct']}%** | Stabilità di mantenimento della mira |
| **Distanza Percorsa Cursore** | {m['cursor_distance_px']:.0f} px (~{m['cursor_distance_meters_approx']} m) | Escursione motoria complessiva |
| **Interventi Co-Pilot Caregiver** | {m['copilot_caregiver_interventions']} | Assistenza fisica dell'operatore |
| **Clic Vocali / Acustici** | {m['acoustic_clicks']} | Trigger 'pop'/'puff' |
| **Clic Gesti Facciali Silenziosi** | {m['gesture_clicks']} | FACS blendshapes (mandibola/sorriso) |

---

### 2. 💬 Comunicazione Aumentativa & Risparmio Fatica (CAA)
| Parametro Digitazione & CAA | Valore | Note Riabilitative |
| :--- | :--- | :--- |
| **Tocchi Tastiera Effettivi** | {a['raw_keystrokes']} tocchi | Digitazione singola lettera |
| **Parole Completate da Suggerimento** | {a['words_predicted']} parole | Selezione diretta predittore lessicale |
| **Caratteri Risparmiati** | **{a['chars_saved']}** caratteri | Sforzo motorio evitato |
| **Keystroke Savings Rate (KSR)** | **{a['ksr_pct']}%** | **Abbattimento percentuale dello sforzo** |

---

### 3. 🧘 Monitor Ergonomico & Postura Cervicale
| Parametro Ergonomico | Eventi Rilevati | Azione Suggerita |
| :--- | :--- | :--- |
| **Cadute Cefaliche (Head-Drop)** | {e['head_drop_alerts']} | Possibile cedimento estensori del collo |
| **Inclinazioni Laterali Eccessive (Tilt > 12°)** | {e['lateral_tilt_alerts']} | Asimmetria posturale o scivolamento |
| **Allarmi Ergonomici Totali** | **{e['total_posture_warnings']}** | Indice complessivo di affaticamento |
{fitts_section}
---

### 📝 Note Cliniche & Osservazioni del Terapista:
_{notes or 'Nessuna osservazione particolare registrata per questa sessione.'}_

---
*Report generato automaticamente da SteadyMotion AI v3.0 Master Clinical Edition.*
"""
        return md

    def save_report(self, patient_id: str = "Paziente-Anonimo", notes: str = "") -> Tuple[str, str]:
        """Salva il report su disco sia in formato Markdown che JSON nella cartella 'reports/'."""
        os.makedirs(self.reports_dir, exist_ok=True)
        md_content = self.generate_markdown_report(patient_id=patient_id, notes=notes)
        summary = self.get_session_summary()

        md_path = os.path.join(self.reports_dir, f"clinical_session_{self.session_id}.md")
        json_path = os.path.join(self.reports_dir, f"clinical_session_{self.session_id}.json")

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return md_path, json_path
