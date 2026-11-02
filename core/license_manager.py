"""
Modulo Gestione Licenze & Attivazione Commerciale Offline per SteadyMotion AI.
Conforme al modello Open-Core SaMD Medical Device (Classe I).

Architettura del Sistema di Licenza:
1. Identificativo Unico Macchina (Hardware Machine ID):
   - Derivato crittograficamente da MachineGuid del registro di sistema di Windows.
   - Formato breve ad alta leggibilità per il paziente/caregiver: 'SM-XXXX-YYYY'.
2. Modalità di Funzionamento:
   - TRIAL_ACTIVE (14 Giorni di Prova Completa): Accesso al 100% delle funzionalità.
   - PRO_ACTIVE (Licenza Commerciale a Vita / Annuale): Sblocco permanente autenticato.
   - TRIAL_EXPIRED (Community Edition Base): Funzionalità di puntamento mouse e clic base
     operative gratuitamente, mentre le funzioni cliniche avanzate (esportazione relazioni
     mediche ISO 9241-9, sintesi vocale neurale, bypass UAC/UIPI) richiedono l'attivazione.
3. Crittografia e Protezione Offline (Zero Server Downtime):
   - Convalida basata su firma HMAC-SHA256 con seed proprietario embedded.
   - Nessuna necessità di connessione internet continua o server DRM cloud remoti.
   - Supporto chiavi Node-Locked (legate alla macchina) e Universal (cliniche/multi-postazione).
4. Protezione Anti-Tampering su Clock di Sistema:
   - Rilevamento automatico di alterazioni a ritroso dell'orologio di sistema di Windows.
"""

import hashlib
import hmac
import json
import os
import platform
import time
from typing import Any, Dict, Optional, Tuple
import uuid

try:
    import winreg
except ImportError:
    winreg = None

SECRET_SALT = b"SteadyMotion_SaMD_Clinical_Master_Key_2026_Salt_#99"
TRIAL_DURATION_SEC = 14 * 86400.0  # 14 Giorni di prova


class LicenseStatus:
    TRIAL_ACTIVE = "TRIAL_ACTIVE"
    TRIAL_EXPIRED = "TRIAL_EXPIRED"
    PRO_ACTIVE = "PRO_ACTIVE"


def get_system_machine_id() -> str:
    """
    Estrae l'identificativo univoco della macchina Windows in formato compatto 'SM-XXXX-YYYY'.
    Usa MachineGuid dal registro o fallback su MAC/Hardware UUID.
    """
    raw_id = ""
    if winreg is not None:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            raw_id, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
        except Exception:
            raw_id = ""

    if not raw_id:
        raw_id = f"{uuid.getnode()}-{platform.node()}"

    h = hashlib.sha256(raw_id.encode("utf-8")).hexdigest().upper()
    return f"SM-{h[:4]}-{h[4:8]}"


def generate_license_key(target_id: str, tier: str = "PRO") -> str:
    """
    Genera un codice di licenza crittograficamente firmato.
    target_id: 'SM-XXXX-YYYY' oppure 'UNIV2026' per licenze universali.
    """
    clean_target = target_id.upper().replace("SM-", "").replace("-", "").replace(" ", "")
    clean_target = clean_target[:8].ljust(8, "0")
    payload = f"{tier}:{clean_target}".encode("utf-8")
    sig = hmac.new(SECRET_SALT, payload, hashlib.sha256).hexdigest().upper()
    return f"SM-{tier}-{clean_target}-{sig[:4]}-{sig[4:8]}"


def verify_license_key(key_str: str, machine_id: str) -> Tuple[bool, str, str]:
    """
    Verifica la validità crittografica di una chiave di licenza rispetto alla macchina corrente.
    Restituisce: (is_valid, tier_o_errore, messaggio)
    """
    if not key_str or not isinstance(key_str, str):
        return False, "", "Codice di licenza vuoto."

    parts = key_str.strip().upper().split("-")
    if len(parts) != 5 or parts[0] != "SM":
        return False, "", "Formato codice licenza non valido. Atteso: SM-PRO-XXXXXXXX-XXXX-XXXX"

    tier = parts[1]
    target_part = parts[2]
    expected_sig = parts[3] + parts[4]

    clean_local = machine_id.upper().replace("SM-", "").replace("-", "").replace(" ", "")[:8]

    if target_part == "UNIV2026":
        payload = f"{tier}:UNIV2026".encode("utf-8")
    elif target_part == clean_local:
        payload = f"{tier}:{clean_local}".encode("utf-8")
    else:
        return False, "", "Questa chiave di licenza è registrata per un altro computer."

    sig = hmac.new(SECRET_SALT, payload, hashlib.sha256).hexdigest().upper()[:8]
    if sig != expected_sig:
        return False, "", "Codice di licenza non valido o firma contraffatta."

    return True, tier, f"Licenza SteadyMotion {tier} attivata con successo!"


class LicenseManager:
    """
    Gestore dello stato di licenza, trial anti-tampering e persistenza locale protetta.
    """

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.state_file = os.path.join(self.config_dir, "license_state.json")
        self.machine_id = get_system_machine_id()
        self._state: Dict[str, Any] = {}
        self.load_state()

    def load_state(self):
        """Carica lo stato persistito o inizializza il periodo di prova di 14 giorni."""
        now = time.time()
        os.makedirs(self.config_dir, exist_ok=True)

        loaded = False
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                    loaded = True
            except Exception:
                loaded = False

        if not loaded or not isinstance(self._state, dict):
            # Inizializzazione primo avvio trial
            self._state = {
                "machine_id": self.machine_id,
                "first_run_time": now,
                "last_seen_time": now,
                "status": LicenseStatus.TRIAL_ACTIVE,
                "license_key": None,
                "tier": "TRIAL",
                "activated_on": None,
                "clock_tampered": False,
            }
            self.save_state()
            return

        # Verifica di integrità e anti-tampering clock
        last_seen = float(self._state.get("last_seen_time", now))
        # Se l'orologio è stato portato indietro di oltre 1 ora (3600s), rileva manomissione
        if now < last_seen - 3600.0:
            self._state["clock_tampered"] = True

        self._state["last_seen_time"] = max(now, last_seen)

        # Se è già attivo un codice licenza valido, riverifica la firma
        if self._state.get("status") == LicenseStatus.PRO_ACTIVE:
            key = self._state.get("license_key")
            ok, tier, _ = verify_license_key(key, self.machine_id)
            if not ok:
                # Chiave non più valida (es. file clonato su altro PC)
                self._state["status"] = LicenseStatus.TRIAL_EXPIRED
                self._state["license_key"] = None
        elif self._state.get("status") == LicenseStatus.TRIAL_ACTIVE:
            # Controllo scadenza periodo di prova
            if self._state.get("clock_tampered", False):
                self._state["status"] = LicenseStatus.TRIAL_EXPIRED
            else:
                first_run = float(self._state.get("first_run_time", now))
                elapsed = now - first_run
                if elapsed >= TRIAL_DURATION_SEC:
                    self._state["status"] = LicenseStatus.TRIAL_EXPIRED

        self.save_state()

    def save_state(self):
        """Salva atomicamente lo stato della licenza su file JSON locale."""
        try:
            tmp_path = self.state_file + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.state_file)
        except Exception:
            pass

    @property
    def status(self) -> str:
        return self._state.get("status", LicenseStatus.TRIAL_EXPIRED)

    @property
    def is_pro_active(self) -> bool:
        """Restituisce True se l'utente ha accesso alle funzionalità Pro (Trial attivo o Licenza Pro)."""
        return self.status in (LicenseStatus.PRO_ACTIVE, LicenseStatus.TRIAL_ACTIVE)

    @property
    def is_fully_licensed(self) -> bool:
        """Restituisce True solo se la copia è sbloccata permanentemente con regolare licenza."""
        return self.status == LicenseStatus.PRO_ACTIVE

    @property
    def remaining_trial_days(self) -> int:
        """Calcola i giorni solari rimanenti del periodo di prova."""
        if self.status != LicenseStatus.TRIAL_ACTIVE:
            return 0
        now = time.time()
        first_run = float(self._state.get("first_run_time", now))
        remaining_sec = max(0.0, TRIAL_DURATION_SEC - (now - first_run))
        return int(remaining_sec // 86400) + (1 if remaining_sec % 86400 > 0 else 0)

    def get_status_display(self) -> Tuple[str, str, str]:
        """
        Restituisce una tupla informativa per la GUI:
        (etichetta_stato, descrizione_dettagliata, colore_hex)
        """
        if self.status == LicenseStatus.PRO_ACTIVE:
            tier = self._state.get("tier", "PRO")
            act_date = self._state.get("activated_on", "Data registrata")
            return (
                f"STEADYMOTION {tier} ATTIVO",
                f"Licenza commerciale ufficiale convalidata a vita ({act_date}).",
                "#10B981",  # Verde smeraldo
            )
        elif self.status == LicenseStatus.TRIAL_ACTIVE:
            days = self.remaining_trial_days
            return (
                f"VERSIONE DI PROVA ({days} GIORNI RIMASTI)",
                "Tutte le funzionalità cliniche avanzate sono attive per valutazione.",
                "#F59E0B",  # Ambra / Giallo
            )
        else:
            tampered = self._state.get("clock_tampered", False)
            reason = "Orologio di sistema alterato" if tampered else "Periodo di 14 giorni terminato"
            return (
                "PROVA SCADUTA (MODALITÀ COMMUNITY)",
                f"{reason}. Tracciamento mouse base gratuito attivo. Inserisci il codice Pro per le funzioni cliniche.",
                "#EF4444",  # Rosso
            )

    def activate_key(self, key_str: str) -> Tuple[bool, str]:
        """
        Tenta l'attivazione della licenza tramite codice fornito dall'utente.
        """
        ok, tier, msg = verify_license_key(key_str, self.machine_id)
        if not ok:
            return False, msg

        self._state["status"] = LicenseStatus.PRO_ACTIVE
        self._state["license_key"] = key_str.strip().upper()
        self._state["tier"] = tier
        self._state["activated_on"] = time.strftime("%d/%m/%Y %H:%M")
        self._state["clock_tampered"] = False
        self.save_state()
        return True, msg

    def reset_for_testing(self, expire_trial: bool = False):
        """Ripristina lo stato a scopo di test e verifica automatica."""
        now = time.time()
        self._state = {
            "machine_id": self.machine_id,
            "first_run_time": (now - TRIAL_DURATION_SEC - 100.0) if expire_trial else now,
            "last_seen_time": now,
            "status": LicenseStatus.TRIAL_EXPIRED if expire_trial else LicenseStatus.TRIAL_ACTIVE,
            "license_key": None,
            "tier": "TRIAL",
            "activated_on": None,
            "clock_tampered": False,
        }
        self.save_state()
