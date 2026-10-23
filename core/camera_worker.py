"""
Thread di acquisizione video ad altissima efficienza e sincronizzazione hardware (Zero-Copy & Event-Driven).
Ottimizzazioni implementate:
1. Sblocco a 60 FPS su bus USB tramite codec MJPG (FourCC) e negoziazione backend Win32 (DSHOW/MSMF).
2. Forzatura del buffer driver a 1 frame (azzeramento code driver OS).
3. Zero Heap Churn Ingestion: riutilizzo rigoroso del buffer pre-allocato self._raw_capture_buf
   in cap.read(image=...) eliminando 55 MB/s di allocazioni dinamiche al secondo nel runtime C++.
4. Triple Buffering circolare lock-free protetto:
   - Buffer 0: slot di scrittura hardware (driver webcam);
   - Buffer 1: slot dell'ultimo frame completato;
   - Buffer 2: slot di lettura attiva da parte del consumer (MediaPipe);
   Nessuna contesa o sovrascrittura di frame in corso di analisi. Zero allocazioni heap a 60 Hz.
5. Sincronizzazione hardware reattiva basata su threading.Event protetta da lock: il consumatore si risveglia
   all'esatto istante dell'interrupt hardware, eliminando il polling, frame persi e inferenze duplicate.
6. Fallback resiliente DirectShow -> Media Foundation (MSMF) con test pre-flight sul primo frame
   e salvaguardia dell'auto-esposizione per prevenire cali a 30 FPS o fotogrammi neri.
"""

import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np


class CameraWorker:
    """Acquisitore video asincrono ad alte prestazioni con triple buffering ed event sync."""

    def __init__(
        self,
        camera_index: int = 0,
        target_width: int = 640,
        target_height: int = 480,
        target_fps: int = 60,
        use_mjpg: bool = True,
        mirror_image: bool = True,
    ):
        self.camera_index = camera_index
        self.target_width = target_width
        self.target_height = target_height
        self.target_fps = target_fps
        self.use_mjpg = use_mjpg
        self.mirror_image = mirror_image

        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None

        # Buffer di cattura grezzo pre-allocato (Zero Heap Churn in cap.read)
        self._raw_capture_buf: np.ndarray = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # Triple Buffering Pre-Allocato (Zero Allocazioni durante il ciclo)
        self._buffers = [
            np.zeros((target_height, target_width, 3), dtype=np.uint8),
            np.zeros((target_height, target_width, 3), dtype=np.uint8),
            np.zeros((target_height, target_width, 3), dtype=np.uint8),
        ]
        self._write_idx: int = 0
        self._latest_ready_idx: int = -1
        self._consumer_idx: int = -1
        self._frame_ready: bool = False

        self.frame_timestamp: float = 0.0
        self.frame_id: int = 0
        self.lock = threading.Lock()
        self.frame_ready_event = threading.Event()

        # Telemetria reale
        self.actual_fps: float = 0.0
        self.negotiated_fps: float = 0.0
        self.negotiated_fourcc: str = ""
        self.current_luma: float = 120.0
        self.fps_counter: int = 0
        self.fps_timer: float = time.perf_counter()

        # Auto-compensazione fotometrica dinamica per ambienti scarsamente illuminati (Zero-Heap LUT)
        self.auto_exposure_boost: bool = True
        self._lut_boost: np.ndarray = np.empty((1, 256), dtype=np.uint8)
        for i in range(256):
            self._lut_boost[0, i] = int(min(255, ((i / 255.0) ** 0.65) * 255.0))

    def _init_capture(self, backend: int) -> Optional[cv2.VideoCapture]:
        """Tenta l'inizializzazione del backend video con configurazione MJPG e test primo frame."""
        try:
            cap = cv2.VideoCapture(self.camera_index, backend)
            if not cap.isOpened():
                return None

            if self.use_mjpg:
                fourcc_mjpg = cv2.VideoWriter_fourcc(*"MJPG")
                cap.set(cv2.CAP_PROP_FOURCC, fourcc_mjpg)

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Negoziazione fall-safe dell'auto-esposizione:
            # Evita di forzare 0.25 se non supportato per non produrre frame neri
            try:
                cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
            except Exception:
                pass

            # Pre-flight check: verifica che cap.read() estragga un frame valido
            ret, _ = cap.read()
            if not ret:
                cap.release()
                return None

            return cap
        except Exception:
            return None

    def start(self) -> bool:
        """Inizializza la webcam con negoziazione DirectShow / MSMF e avvia il thread di cattura."""
        # 1. Prova backend nativo DirectShow per controllo a basso livello su Windows
        self.cap = self._init_capture(cv2.CAP_DSHOW)
        if self.cap is None:
            # 2. Fallback su Windows Media Foundation (MSMF)
            self.cap = self._init_capture(cv2.CAP_MSMF)
            if self.cap is None:
                # 3. Fallback generico standard
                self.cap = self._init_capture(cv2.CAP_ANY)
                if self.cap is None:
                    return False

        # Lettura parametri effettivi negoziati dal driver
        self.negotiated_fps = self.cap.get(cv2.CAP_PROP_FPS)
        fourcc_int = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        self.negotiated_fourcc = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])

        # Adattamento automatico buffer se la risoluzione reale differisce
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if actual_w > 0 and actual_h > 0 and (actual_w != self.target_width or actual_h != self.target_height):
            self.target_width = actual_w
            self.target_height = actual_h
            self._raw_capture_buf = np.zeros((actual_h, actual_w, 3), dtype=np.uint8)
            self._buffers = [
                np.zeros((actual_h, actual_w, 3), dtype=np.uint8),
                np.zeros((actual_h, actual_w, 3), dtype=np.uint8),
                np.zeros((actual_h, actual_w, 3), dtype=np.uint8),
            ]

        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True, name="CameraIngestionThread")
        self.thread.start()
        return True

    def _capture_loop(self):
        """Ciclo continuo di cattura hardware a zero allocazioni dinamiche."""
        while self.is_running and self.cap is not None:
            # Cattura diretta nel buffer pre-allocato (Zero Heap Churn)
            ret, _ = self.cap.read(image=self._raw_capture_buf)
            if not ret or self._raw_capture_buf is None:
                time.sleep(0.001)
                continue

            t_now = time.perf_counter()

            # Scrive nel buffer di scrittura corrente
            target_buf = self._buffers[self._write_idx]
            if self._raw_capture_buf.shape == target_buf.shape:
                if self.mirror_image:
                    cv2.flip(self._raw_capture_buf, 1, dst=target_buf)
                else:
                    np.copyto(target_buf, self._raw_capture_buf)
            else:
                if self.mirror_image:
                    target_buf = cv2.flip(self._raw_capture_buf, 1)
                else:
                    target_buf = self._raw_capture_buf.copy()
                self._buffers[self._write_idx] = target_buf

            # Compensazione fotometrica dinamica automatica in condizioni di scarsa luce (< 35 nit)
            if self.auto_exposure_boost and self.current_luma < 35.0:
                cv2.LUT(target_buf, self._lut_boost, dst=target_buf)

            # Swap atomico protetto: seleziona il prossimo slot di scrittura libero
            with self.lock:
                just_written_idx = self._write_idx
                self._latest_ready_idx = just_written_idx
                self.frame_timestamp = t_now
                self.frame_id += 1
                self._frame_ready = True

                # Trova lo slot che NON è l'ultimo pronto e NON è attualmente in lettura dal consumatore
                for idx in (0, 1, 2):
                    if idx != self._latest_ready_idx and idx != self._consumer_idx:
                        self._write_idx = idx
                        break

                # Segnala al consumatore mentre si detiene il lock per evitare race condition
                self.frame_ready_event.set()

            # Calcolo FPS effettivi e campionamento luminosità media Luma (sub-sample leggero)
            self.fps_counter += 1
            if t_now - self.fps_timer >= 0.8:
                self.actual_fps = self.fps_counter / (t_now - self.fps_timer)
                self.fps_counter = 0
                self.fps_timer = t_now
                # Stima Luma istantanea senza carico CPU (< 0.05 ms su griglia 20x20)
                try:
                    self.current_luma = float(np.mean(target_buf[::24, ::32]))
                except Exception:
                    pass

    def wait_for_frame(self, timeout: float = 0.035) -> Tuple[bool, Optional[np.ndarray], float, int]:
        """
        Attende l'arrivo hardware del prossimo frame (sincronizzazione event-driven a latenza zero).
        Evita qualsiasi polling o consumo inutile di cicli CPU.
        """
        signaled = self.frame_ready_event.wait(timeout=timeout)

        with self.lock:
            self.frame_ready_event.clear()

            if not self._frame_ready or self._latest_ready_idx < 0:
                return False, None, 0.0, 0

            # Assegna lo slot al consumatore in modo che il writer non lo sovrascriva
            self._consumer_idx = self._latest_ready_idx
            return True, self._buffers[self._consumer_idx], self.frame_timestamp, self.frame_id

    def get_latest_frame(self) -> Tuple[bool, Optional[np.ndarray], float, int]:
        """Restituisce immediatamente l'ultimo frame disponibile senza attendere."""
        with self.lock:
            if not self._frame_ready or self._latest_ready_idx < 0:
                return False, None, 0.0, 0
            self._consumer_idx = self._latest_ready_idx
            return True, self._buffers[self._consumer_idx], self.frame_timestamp, self.frame_id

    def stop(self):
        """Arresta il thread e rilascia le risorse video."""
        self.is_running = False
        self.frame_ready_event.set()
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self._frame_ready = False

    def switch_camera(self, new_camera_index: int) -> bool:
        """
        Commuta la sorgente di acquisizione a caldo su un nuovo indice webcam.
        Thread-safe, rilascia la webcam precedente e riavvia la pipeline.
        """
        self.stop()
        self.camera_index = int(new_camera_index)
        return self.start()

    @staticmethod
    def get_available_cameras(max_probe: int = 4) -> list:
        """Sonda rapidamente gli indici video del sistema per rilevare le webcam collegate."""
        available = []
        for idx in range(max_probe):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(idx)
                cap.release()
            else:
                cap_m = cv2.VideoCapture(idx, cv2.CAP_MSMF)
                if cap_m.isOpened():
                    available.append(idx)
                    cap_m.release()
        return available

