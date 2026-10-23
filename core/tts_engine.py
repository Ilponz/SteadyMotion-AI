"""
Motore di Sintesi Vocale Assistiva Asincrono (Clinical AAC Text-to-Speech Engine).
Progettato specificamente per SteadyMotion AI v3.0 / v3.1.

Caratteristiche Tecniche:
1. Thread-Safe & Zero Jitter: Elaborazione disaccoppiata in un thread worker dedicato
   con coda asincrona priva di blocchi per il core tracking loop e la GUI.
2. Inizializzazione COM nativa su Windows (pythoncom.CoInitialize() / CoUninitialize())
   che previene categoricamente gli errori di marshalling STA (0x800401F0 / CO_E_NOTINITIALIZED).
3. Selezione intelligente della voce: Rileva e seleziona automaticamente la voce italiana di sistema
   (es. 'Microsoft Elsa Desktop - Italian') o la voce predefinita dell'utente.
4. Supporto Interruzione Immediata (SVSFPurgeBeforeSpeak): Consente al paziente di interrompere
   istantaneamente frasi precedenti in caso di emergenza o correzione rapida.
5. Fallback Resiliente Windows System.Speech: Se SAPI COM non è disponibile, attiva in automatico
   il sintetizzatore .NET di Windows senza dipendenze esterne.
"""

import logging
import os
import queue
import subprocess
import threading
import time
from typing import List, Optional

logger = logging.getLogger("SteadyMotion.TTS")

# Costanti flag SAPI (Speech API)
SVSF_DEFAULT = 0
SVSF_ASYNC = 1
SVSF_PURGE_BEFORE_SPEAK = 2


class TTSEngine:
    """Motore clinico di sintesi vocale non bloccante per Comunicazione Aumentativa Alternativa (CAA)."""

    def __init__(self, rate: int = 0, volume: int = 100, auto_start: bool = True):
        self.rate = max(-10, min(10, int(rate)))
        self.volume = max(0, min(100, int(volume)))

        self._queue: queue.Queue = queue.Queue(maxsize=32)
        self._worker_thread: Optional[threading.Thread] = None
        self._is_running = False
        self._available_voices: List[str] = []
        self._selected_voice_idx: int = 0
        self._has_native_sapi = False

        if auto_start:
            self.start()

    def start(self):
        """Avvia il thread worker di sintesi vocale."""
        if self._is_running:
            return
        self._is_running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="ClinicalTTSWorker",
        )
        self._worker_thread.start()

    def _worker_loop(self):
        """Loop di elaborazione dedicato con inizializzazione rigorosa dell'Apartment COM."""
        voice = None
        has_pythoncom = False

        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            has_pythoncom = True

            voice = win32com.client.Dispatch("SAPI.SpVoice")
            self._has_native_sapi = True

            # Ricerca e registrazione delle voci installate
            voices = voice.GetVoices()
            count = voices.Count
            self._available_voices = [voices.Item(i).GetDescription() for i in range(count)]

            # Privilegia la voce italiana se disponibile
            best_idx = 0
            for i, v_name in enumerate(self._available_voices):
                if "italian" in v_name.lower() or "italia" in v_name.lower() or "elsa" in v_name.lower():
                    best_idx = i
                    break

            if count > 0:
                self._selected_voice_idx = best_idx
                voice.Voice = voices.Item(best_idx)

            del voices

        except Exception as e:
            logger.warning(f"SAPI nativo non disponibile o inizializzazione fallita: {e}. Fallback su PowerShell.")
            self._has_native_sapi = False
            voice = None

        while self._is_running:
            try:
                task = self._queue.get(timeout=0.20)
            except queue.Empty:
                continue

            if task is None:
                self._queue.task_done()
                break

            action, text, interrupt = task

            if action == "speak" and text:
                self._execute_speak(voice, text, interrupt)
            elif action == "stop":
                self._execute_stop(voice)

            self._queue.task_done()

        # Pulizia rigorosa COM prima di deallocare l'Apartment
        if voice is not None:
            del voice
        if has_pythoncom:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

    def _execute_speak(self, voice, text: str, interrupt: bool):
        """Esegue l'emissione vocale sul sintetizzatore attivo."""
        flags = SVSF_ASYNC
        if interrupt:
            flags |= SVSF_PURGE_BEFORE_SPEAK

        if voice is not None and self._has_native_sapi:
            try:
                voice.Rate = self.rate
                voice.Volume = self.volume
                voice.Speak(text, flags)
                return
            except Exception as e:
                logger.error(f"Errore emissione voce SAPI: {e}")

        # Fallback resiliente .NET PowerShell per sistemi con COM disattivato
        self._fallback_powershell_speak(text)

    def _execute_stop(self, voice):
        """Interrompe istantaneamente qualsiasi frase in riproduzione."""
        if voice is not None and self._has_native_sapi:
            try:
                voice.Speak("", SVSF_ASYNC | SVSF_PURGE_BEFORE_SPEAK)
            except Exception:
                pass

    def _fallback_powershell_speak(self, text: str):
        """Sintesi vocale di emergenza via PowerShell .NET System.Speech."""
        sanitized = text.replace("'", "''").replace('"', '""').replace("`", "")
        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {max(-10, min(10, self.rate // 2))}; "
            f"$s.Volume = {self.volume}; "
            f"$s.Speak('{sanitized}');",
        ]
        try:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def speak(self, text: str, interrupt: bool = False):
        """
        Accoda la frase da pronunciare. Chiamata non bloccante (0 µs nel core loop).
        
        Args:
            text: Testo da verbalizzare.
            interrupt: Se True, interrompe immediatamente qualsiasi frase già in corso.
        """
        clean_text = str(text).strip()
        if not clean_text or not self._is_running:
            return

        try:
            self._queue.put_nowait(("speak", clean_text, interrupt))
        except queue.Full:
            # Coda satura: svuota l'elemento più vecchio per garantire tempestività
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(("speak", clean_text, interrupt))
            except Exception:
                pass

    def stop_speaking(self):
        """Interrompe la voce corrente all'istante."""
        if not self._is_running:
            return
        try:
            self._queue.put_nowait(("stop", "", True))
        except Exception:
            pass

    def set_rate(self, rate: int):
        """Imposta la velocità di pronuncia (-10 molto lenta, +10 rapida)."""
        self.rate = max(-10, min(10, int(rate)))

    def set_volume(self, volume: int):
        """Imposta il volume di sintesi (0-100%)."""
        self.volume = max(0, min(100, int(volume)))

    def get_available_voices(self) -> List[str]:
        """Restituisce la lista delle voci di sintesi installate."""
        return list(self._available_voices)

    def stop(self):
        """Arresta e rilascia il worker di sintesi vocale."""
        if not self._is_running:
            return
        self._is_running = False
        try:
            self._queue.put_nowait(None)
        except Exception:
            pass
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.6)
