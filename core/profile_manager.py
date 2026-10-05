"""
Modulo di Gestione Profili Paziente & Preset Clinici (Patient Profile Manager).
Consente di:
1. Salvare e ripristinare in modo persistente (JSON) le calibrazioni ROM asimmetriche,
   i parametri del filtro 1€, i tempi di dwell e le soglie acustiche.
2. Fornire 4 Preset Clinici Pre-configurati basati sulla patologia neuro-motoria:
   - SLA / Minimo Sforzo (Alto guadagno, raggio dwell generoso, bassa resistenza)
   - Parkinson / Tremore Forte (Forte filtraggio, deadzone estesa a 3.5 px, dwell lungo)
   - Tetraplegia / Standard (Assetto bilanciato fisiologico)
   - Distonia / Ipertono (Tolleranza allargata, smorzamento elevato)
3. Supportare profili multipli nominativi per uso ospedaliero, RSA o domiciliare condiviso.
"""

import json
import os
from typing import Any, Dict, List, Optional


class ProfileManager:
    """Gestore persistente delle impostazioni e calibrazioni cliniche del paziente."""

    DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
        "Tetraplegia (Standard)": {
            "name": "Tetraplegia (Standard)",
            "description": "Assetto bilanciato per movimento cefalico preservato e minimo tremore.",
            "gain": 2.8,
            "gain_x_left": 2.8,
            "gain_x_right": 2.8,
            "gain_y_up": 2.8,
            "gain_y_down": 2.8,
            "is_custom_rom": False,
            "deadzone": 2.0,
            "min_cutoff": 1.1,
            "beta": 0.006,
            "dwell_time": 0.65,
            "tolerance_radius": 24.0,
            "acoustic_enabled": False,
            "acoustic_threshold": 0.18,
            "ui_scale": 1.0,
            "theme": "Dark",
        },
        "SLA (Minimo Sforzo)": {
            "name": "SLA (Minimo Sforzo)",
            "description": "Guadagni elevati e dwell elastico per escursioni cervicali minime (< 5 gradi).",
            "gain": 4.2,
            "gain_x_left": 4.2,
            "gain_x_right": 4.2,
            "gain_y_up": 4.2,
            "gain_y_down": 4.2,
            "is_custom_rom": False,
            "deadzone": 1.2,
            "min_cutoff": 0.9,
            "beta": 0.009,
            "dwell_time": 0.55,
            "tolerance_radius": 32.0,
            "acoustic_enabled": False,
            "acoustic_threshold": 0.15,
            "ui_scale": 1.1,
            "theme": "Dark",
        },
        "Parkinson (Tremore Forte)": {
            "name": "Parkinson (Tremore Forte)",
            "description": "Massima attenuazione del tremore a riposo (4-6 Hz) con deadzone a 3.5 px.",
            "gain": 2.2,
            "gain_x_left": 2.2,
            "gain_x_right": 2.2,
            "gain_y_up": 2.2,
            "gain_y_down": 2.2,
            "is_custom_rom": False,
            "deadzone": 3.5,
            "min_cutoff": 1.8,
            "beta": 0.003,
            "dwell_time": 0.85,
            "tolerance_radius": 28.0,
            "acoustic_enabled": False,
            "acoustic_threshold": 0.22,
            "ui_scale": 1.0,
            "theme": "Dark",
        },
        "Distonia / Spasmi (Ipertono)": {
            "name": "Distonia / Spasmi (Ipertono)",
            "description": "Filtro pesante anti-spasmo e dwell allargato per movimenti muscolari a scatto.",
            "gain": 2.0,
            "gain_x_left": 2.0,
            "gain_x_right": 2.0,
            "gain_y_up": 2.0,
            "gain_y_down": 2.0,
            "is_custom_rom": False,
            "deadzone": 3.0,
            "min_cutoff": 1.6,
            "beta": 0.004,
            "dwell_time": 0.95,
            "tolerance_radius": 36.0,
            "acoustic_enabled": False,
            "acoustic_threshold": 0.25,
            "ui_scale": 1.0,
            "theme": "Dark",
        },
    }

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            # Cartella config relativa alla root di progetto
            self.base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
        else:
            self.base_dir = base_dir

        self.profiles_dir = os.path.join(self.base_dir, "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.active_profile_file = os.path.join(self.base_dir, "active_profile.json")

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """Restituisce una copia pulita del preset clinico richiesto."""
        if preset_name in self.DEFAULT_PRESETS:
            return dict(self.DEFAULT_PRESETS[preset_name])
        return dict(self.DEFAULT_PRESETS["Tetraplegia (Standard)"])

    def list_presets(self) -> List[str]:
        return list(self.DEFAULT_PRESETS.keys())

    def list_saved_profiles(self) -> List[str]:
        """Elenca tutti i profili utente salvati su disco (.json)."""
        if not os.path.exists(self.profiles_dir):
            return []
        files = [f[:-5] for f in os.listdir(self.profiles_dir) if f.endswith(".json")]
        return sorted(files)

    def save_profile(self, name: str, data: Dict[str, Any]) -> str:
        """Salva un profilo paziente su file JSON."""
        clean_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
        if not clean_name:
            clean_name = "Paziente_Default"

        filepath = os.path.join(self.profiles_dir, f"{clean_name}.json")
        save_payload = dict(data)
        save_payload["name"] = clean_name

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_payload, f, indent=4, ensure_ascii=False)

        # Salva come profilo attivo predefinito
        self.set_active_profile(save_payload)
        return filepath

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Carica un profilo paziente dal disco."""
        filepath = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.exists(filepath):
            # Prova a cercare tra i preset
            if name in self.DEFAULT_PRESETS:
                return self.get_preset(name)
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return None

    def set_active_profile(self, data: Dict[str, Any]):
        """Memorizza l'ultimo profilo usato per il ripristino all'avvio."""
        try:
            with open(self.active_profile_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    def get_last_active_profile(self) -> Dict[str, Any]:
        """Carica l'ultimo profilo usato o restituisce il default Standard."""
        if os.path.exists(self.active_profile_file):
            try:
                with open(self.active_profile_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return self.get_preset("Tetraplegia (Standard)")
