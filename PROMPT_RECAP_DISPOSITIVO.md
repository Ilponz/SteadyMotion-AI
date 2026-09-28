# 🚀 PROMPT DI HANDOVER & CONTESTO PROGETTUALE (DA COPIARE SUL NUOVO DISPOSITIVO)

> **Istruzioni:** Quando apri una nuova sessione o ti sposti sul nuovo computer, copia e incolla l'intero blocco di testo sottostante per istruire istantaneamente l'assistente AI con tutto il contesto, l'architettura aggiornata, le falle già risolte e i prossimi passi operativi.

---

```markdown
Ciao! Sto lavorando al progetto open source "SteadyMotion AI" (versione 3.0 Pure Software Edition).
Il repository ufficiale GitHub è sincronizzato e disponibile al link:
👉 https://github.com/Ilponz/SteadyMotion-AI (branch: main).

### 🎯 CHE COS'È STEADYMOTION AI
È una piattaforma assistiva 100% software, gratuita e open source (licenza Apache 2.0) per Windows, che converte una comune webcam da 15-20 € in un'interfaccia di puntamento mouse ad altissima precisione e fluidità (60 FPS stabili) per persone con gravi disabilità neuro-motorie (SLA, tetraplegia, morbo di Parkinson, tremore essenziale).
Azzeriamo qualsiasi costo hardware aggiuntivo: nessun Raspberry Pi, nessun dongle proprietario, nessun tracciatore a infrarossi da 4.000 €.

---

### 🧠 ARCHITETTURA TECNICA & OTTIMIZZAZIONI REALIZZATE
Il codice è interamente implementato in Python e Win32, testato e validato:

1. **Video Ingestion Zero-Copy (core/camera_worker.py):**
   - Backend DirectShow con buffer driver forzato a 1 (elimina i frame accumulati in coda e il lag video);
   - Codec FourCC `MJPG` a 60 FPS sbloccato su USB 2.0/3.0;
   - Doppio buffer pre-allocato e swap lock-free: zero allocazioni per frame nel loop.

2. **Biometria 6-DoF & Gaze Engine Avanzato (core/tracker_engine.py):**
   - MediaPipe Tasks FaceLandmarker in modalità `RunningMode.VIDEO` a timestamp monotonico continuo;
   - **Zero Heap Churn:** Buffer RGB pre-allocato in-place (`cv2.cvtColor(..., dst=self._rgb_buffer)`), eliminati 55 MB/s di spazzatura per il Garbage Collector;
   - **Normalizzazione alla distanza Z (IPD Scale):** Calcolo della distanza inter-oculare (IPD) 3D, rendendo la sensibilità del mouse costante se il paziente si sposta in avanti/indietro rispetto alla webcam;
   - **Gaze Micro-Correction 2D:** Offset dell'iride su asse X e asse Y;
   - **EAR Blink Clamping:** Congelamento del cursore per 150 ms durante l'ammiccamento naturale per eliminare il falso scatto parassita del mouse.

3. **DSP One-Euro & Fisica della Traiettoria (core/dsp_filter.py):**
   - Filtro One-Euro (Casiez et al., CHI 2012) a frequenza di taglio dinamica;
   - Operatore di Contrazione Prossimale (Dynamic Deadzone): **abbattimento misurato del 90.2%** sulle oscillazioni da tremore patologico a 5 Hz e blocco solido a testa ferma.

4. **Iniezione Sub-Pixel Win32 a 16-bit (core/virtual_input.py):**
   - API nativa ctypes `SendInput` a 64-bit mappata su coordinate assolute virtuali 0 - 65535;
   - Supporto nativo `Per-Monitor DPI Awareness v2` per evitare disallineamenti su monitor 2K/4K con scaling 125%/150%;
   - Mappatura sub-pixel con `round()` per azzerare il bias direzionale verso l'alto-sinistra;
   - Doppio clic asincrono non bloccante in micro-thread dedicato (zero frame persi a 60 Hz);
   - Timer kernel Windows sbloccato a 1.0 ms tramite `timeBeginPeriod(1)`.

5. **Dwell Clicker con Tolleranza Leaky Bucket (core/dwell_clicker.py):**
   - Clic a sosta temporizzata (default 650 ms);
   - Algoritmo a "Pozzo di Gravità": se uno spasmo sposta temporaneamente il puntatore nella Grace Zone, il progresso decade dolcemente senza azzerarsi a zero;
   - Cancellazione sicura senza flash di coordinate (0, 0).

6. **Architettura Real-Time Disaccoppiata & Trigger Acustico (gui/hud_overlay.py, main.py, core/acoustic_trigger.py):**
   - **Disaccoppiamento Threading:** Il Core Engine di tracciamento e iniezione (`_core_tracking_loop`) gira in un thread dedicato ad alta frequenza (60-120 Hz) completamente indipendente dal thread GUI di Tkinter (che aggiorna telemetria ed HUD a 30 FPS). Il mouse non subisce rallentamenti o cali di framerate anche se la finestra viene mossa o ridimensionata;
   - **Trigger Acustico Ausiliario Anti-Rumore:** Microfono webcam con pre-enfasi passa-alto e Zero-Crossing Rate (ZCR) per rilevare soffi e schiocchi di lingua isolandoli dalle voci e dai rumori ambientali della stanza;
   - **HUD Trasparente Click-Through:** Finestra non attivabile e permeabile al 100% via stili Win32 `WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`.

---

### 🧪 TEST E BENCHMARK MATEMATICO
Tutti i collaudi sono inclusi in `test_engine.py` e superati al 100%:
- Attenuazione tremore patologico 5.0 Hz: **90.2%** (da 8.00 px a 0.79 px);
- Deviazione da fermo (Dynamic Deadzone): **0.00 px**;
- Tolleranza e precisione temporale Dwell: **100%**;
- Controller Sub-Pixel Win32 e Tracker Video: **100%**.

---

### 🚀 COME AVVIARLO SUL NUOVO COMPUTER
1. **Clona o scarica la repository:**
   `git clone https://github.com/Ilponz/SteadyMotion-AI.git`
   `cd SteadyMotion-AI`
2. **Requisiti:** Windows 10/11 x64, Python 3.10 o 3.11.
3. **Installazione dipendenze:**
   `pip install opencv-python mediapipe numpy pywin32 sounddevice python-docx`
4. **Verifica automatica:**
   `python test_engine.py`
5. **Avvio applicazione:**
   Doppio clic su `Avvia_SteadyMotion.bat` (oppure `python main.py`).
   - Tasto **F12**: Ricentra la postura neutra comoda del paziente
   - Tasto **F9**: Mette in pausa / riprende il tracciamento

---

### 📌 PROSSIMI STEP OPERATIVI DA SVOLGERE SUL NUOVO DISPOSITIVO
Ecco le priorità su cui dobbiamo lavorare insieme:
1. **Compilazione Standalone in Eseguibile .EXE con PyInstaller:**
   Creare un pacchetto Windows `.exe` standalone che includa `models/face_landmarker.task` e le DLL necessarie, così da poter avviare SteadyMotion AI con un doppio clic su qualsiasi PC anche senza Python installato.
2. **Collaudo dal vivo con webcam reale:**
   Verificare la resa con la webcam del nuovo dispositivo, regolando i cursori di Guadagno e Deadzone in base alle condizioni di illuminazione e alla postura.
3. **Profili di calibrazione preimpostati (Preset Manager):**
   Aggiungere nel pannello i profili one-click salvabili su file JSON:
   - *Preset Parkinson*: Deadzone rinforzata (3.5 px), cutoff 0.8 Hz, dwell 0.85s;
   - *Preset SLA/ALS*: Sensibilità elevata (gain 3.8), deadzone stretta (1.2 px), trigger acustico attivo;
   - *Preset Standard*: Parametri bilanciati di default.
4. **Integrazione Tastiera Virtuale a Schermo (On-Screen Keyboard):**
   Collegamento del Dwell Clicker con la tastiera di accessibilità di Windows o con una tastiera assistiva rapida integrata.

Aiutami a iniziare subito con il primo punto (la compilazione .exe standalone o la prova dal vivo)!
```
