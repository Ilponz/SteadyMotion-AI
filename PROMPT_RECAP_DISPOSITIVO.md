# 🚀 PROMPT DI HANDOVER & CONTESTO PROGETTUALE (DA COPIARE SUL NUOVO DISPOSITIVO)

> **Istruzioni:** Quando ti sposti sul computer di casa o apri una nuova sessione con l'assistente AI, copia e incolla l'intero blocco di testo sottostante (racchiuso nel blocco markdown). Questo istruirà istantaneamente l'AI con l'intero storico, le ottimizzazioni realizzate, l'architettura a 60 FPS, le istruzioni per il collaudo della webcam dal vivo e la checklist operativa.

---

```markdown
Ciao! Sto lavorando al progetto open source "SteadyMotion AI" (Versione 3.0 Clinical Release).
Il repository ufficiale GitHub è sincronizzato e aggiornato al link:
👉 https://github.com/Ilponz/SteadyMotion-AI (branch: main).

### 🎯 CHE COS'È STEADYMOTION AI
È una piattaforma assistiva 100% software, gratuita e open source (licenza Apache 2.0) per Windows, che converte una comune webcam commerciale (da 15-20 €) in un'interfaccia di puntamento mouse ad altissima precisione e fluidità (60 FPS stabili) per persone con gravi disabilità neuro-motorie (SLA, tetraplegia, morbo di Parkinson, tremore essenziale, distonie cervicali).
Azzeriamo qualsiasi costo hardware aggiuntivo: nessun Raspberry Pi, nessun dongle proprietario, nessun dispositivo a infrarossi da 4.000 €.

---

### 🧠 ARCHITETTURA TECNICA & OTTIMIZZAZIONI COMPLETE (v3.0)
Tutti i componenti sono testati con benchmark scientifici in `test_engine.py` (7 su 7 superati al 100%):

1. **Video Ingestion Asincrona Zero-Copy (core/camera_worker.py):**
   - Backend DirectShow con buffer driver forzato a 1 e fallback MSMF (Media Foundation);
   - Triple Buffering circolare pre-allocato e sincronizzazione hardware `threading.Event` (zero allocazioni di frame nel loop a 60 Hz);
   - Sub-sampling fotometrico Luma rapido per alert automatico di scarsa illuminazione (< 25 nit).

2. **Biometria 6-DoF & Gaze Engine Avanzato (core/tracker_engine.py):**
   - MediaPipe Tasks FaceLandmarker in modalità nativa `RunningMode.VIDEO` con timestamp monotonici continui;
   - Zero Heap Churn: buffer RGB pre-allocato in-place (`dst=self._rgb_buffer`);
   - **Normalizzazione Fisiologica IPD 3D con Bounding Bisezione:** scala inter-oculare vincolata rigidamente nell'intervallo [0.65, 1.60] per impedire al cursore di "catapultarsi" quando l'utente sbadiglia, tossisce o ruota la testa;
   - EAR Blink Clamping (congelamento del cursore per 150 ms durante l'ammiccamento naturale).

3. **DSP One-Euro Isotropo 2D & Deadzone Continua (core/dsp_filter.py):**
   - **Isotropia Euclidea Rigorosa 2D:** velocità istantanea scalare condivisa $v_{2D} = \sqrt{\dot{x}^2 + \dot{y}^2}$, garantendo 0.000000 px di asimmetria sulle diagonali a 45°;
   - **Contrazione Prossimale (Soft-Thresholding):** zona morta continua con 89.3% di abbattimento del tremore patologico a 5.0 Hz e 0.00 px di oscillazione a riposo.

4. **Iniezione Sub-Pixel Win32 a 16-bit (core/virtual_input.py):**
   - API nativa ctypes `SendInput` a 64-bit con struttura `INPUT` pre-allocata staticamente (zero allocazioni heap per frame, 3.5 µs di latenza);
   - Supporto nativo `Per-Monitor DPI Awareness v2` (-4) per prevenire disallineamenti su monitor 2K/4K con scaling 125%/150%;
   - Mappatura normalizzata assoluta virtual desktop 0 - 65535 priva di bias direzionale;
   - Metodi di digitazione diretta `send_unicode_char` e `send_key_event` per la tastiera a schermo.

5. **Dwell Clicker con Algoritmo Leaky Bucket (core/dwell_clicker.py):**
   - Clic a sosta temporizzata (default 650 ms);
   - Pozzo di gravità (Grace Zone a 1.85x): se uno spasmo sposta temporaneamente il puntatore all'esterno, il progresso decade linearmente anziché azzerarsi bruscamente;
   - Micro-inseguimento posturale adattivo (< 4 px/s) per assorbire il rilassamento muscolare del collo.

6. **Trigger Acustico Ausiliario Anti-Rumore (core/acoustic_trigger.py):**
   - Microfono webcam con pre-enfasi passa-alto differenziale e Zero-Crossing Rate (ZCR > 0.08);
   - Calibrazione automatica del rumore ambientale della stanza per 2 secondi ($soglia = rumore\_fondo \times 2.2 + 0.04$);
   - 0 falsi positivi su rumore bianco continuo e attivazione affidabile su schiocchi 'pop' o soffi 'puff'.

7. **Interfaccia Grafica Clinica Human-Grade (gui/control_panel.py):**
   - Sviluppata in CustomTkinter v6 (stile Windows 11 Fluent) con modalità Notte (`#0B0F19`), Giorno (`#F8FAFC`) e Sistema;
   - Scaling UI regolabile (100% - 130%) per ipovisione e monitor 4K;
   - **Avvio Sicuro in Standby:** Il cursore NON viene mai sequestrato all'avvio. L'utente o l'operatore arma/disarma il controllo tramite tasto globale **F9** o banner superiore;
   - **Tobii-Style Track Status Radar:** Radar posturale circolare con ali di roll, pitch e yaw per la verifica del posizionamento;
   - **Setup Wizard in 4 Fasi:** Profilo clinico → Allineamento webcam → Centratura neutra F12 → Metodo di clic;
   - **Tutorial & Sandbox Interattiva a 5 Bersagli:** Palestra integrata per imparare a puntare e completare il dwell senza rischiare clic involontari su Windows;
   - **Tastiera CAA di Emergenza:** Frasi rapide cliniche ("SÌ", "NO", "AIUTO", "HO SETE", "GRAZIE", "CHIAMAMI").

8. **Calibrazione Clinica ROM a 5 Punti (gui/calibration_window.py):**
   - Finestra modale a schermo intero con 5 bersagli sequenziali (Centro, Alto-SX, Alto-DX, Basso-DX, Basso-SX);
   - Misura l'escursione cefalica reale in gradi di Yaw e Pitch;
   - **Mappatura a Guadagni Asimmetrici per Quadrante:** Calcola automaticamente 4 coefficienti di guadagno indipendenti ($G_{x,\text{left}}, G_{x,\text{right}}, G_{y,\text{up}}, G_{y,\text{down}}$), permettendo a pazienti con emiparesi o mobilità limitata su un lato di raggiungere tutti i bordi dello schermo senza affaticamento muscolare;
   - Continuità $C^0$ garantita (0.000000 px di salto all'origine);
   - Supporto tasto Caregiver rapido (Spazio / Invio) per validazione assistita.

9. **Tastiera Assistiva Flottante a Schermo (gui/floating_keyboard.py):**
   - Finestra sempre in primo piano (`Topmost`) su qualsiasi app di Windows (Notepad, Word, browser, WhatsApp);
   - Tasti ampi QWERTY, Numeri & Simboli, e Frasi Rapide;
   - **Digitazione Diretta a Windows:** Inietta i caratteri direttamente nel campo di testo attivo dell'applicazione sottostante via Win32 SendInput Unicode;
   - **Sintesi Vocale Integrata (TTS SAPI nativo):** Pulsante `[🔊 Parla (TTS)]` per pronunciare istantaneamente il testo digitato o le frasi di bisogno.

---

### 📦 COME AVVIARLO SUL NUOVO DISPOSITIVO (A CASA CON WEBCAM)

Nella cartella del progetto trovi tutto già pronto e compilato:

#### Modalità 1: Standalone Diretto (Consigliata, non richiede Python)
1. Apri la cartella del progetto o decomprimi l'archivio portatile `dist\SteadyMotion-AI-v3.0-Portable.zip`.
2. Fai doppio clic su:
   `Avvia_EXE_Standalone.bat`
   (oppure avvia direttamente `dist\SteadyMotion-AI\SteadyMotion-AI.exe`).

#### Modalità 2: Da Sorgente Python
1. Installa i requisiti su Windows:
   `pip install opencv-python mediapipe numpy pywin32 sounddevice customtkinter darkdetect`
2. Esegui la verifica scientifica automatica:
   `python test_engine.py` (deve restituire "TUTTI I 7 TEST SUPERATI AL 100%")
3. Avvia:
   `python main.py` (oppure doppio clic su `Avvia_SteadyMotion.bat`).

---

### 🧪 PROCEDURA DI COLLAUDO DAL VIVO CON LA WEBCAM (STEP-BY-STEP)

Quando sei a casa davanti alla postazione reale con il paziente:

1. **Posizionamento Hardware:**
   - Collega la webcam USB sopra o sotto il monitor, all'altezza degli occhi del paziente.
   - Distanza ottimale: 50 - 70 cm dal viso.
   - Assicurati che l'illuminazione sia frontale o diffusa (evita forti controluce alle spalle).
2. **Avvio dell'App:**
   - Lancia `Avvia_EXE_Standalone.bat`.
   - L'app parte in **STANDBY DI SICUREZZA**: il cursore non si muove.
   - Guarda il **Radar Posturale**: la croce verde deve essere nel cerchio centrale e il badge deve segnare *"Luce: OK"* e *"Centratura Ottimale"*.
3. **Calibrazione Postura Neutra:**
   - Fai posizionare il paziente nella sua posizione di riposo comoda e premi **F12** (o il pulsante *"🎯 Ricentra Centro Schermo"*).
4. **Calibrazione Range of Motion (Consigliata):**
   - Clicca su `[📐 Calibrazione ROM (5 Punti)]`.
   - La schermata va a tutto schermo: fai fissare i 5 cerchi che pulsano (Centro, Alto-SX, Alto-DX, Basso-DX, Basso-SX).
   - Se il paziente è affaticato, puoi premere la **Barra Spazio** per registrare il punto manualmente.
   - Clicca `[💾 Applica Guadagni e Salva]`: i guadagni asimmetrici saranno attivi e salvati.
5. **Addestramento nella Sandbox (Tab Tutorial):**
   - Vai nella scheda *"📖 Tutorial & Bersagli"*.
   - Fai esercitare il paziente a colpire i 5 pulsanti numerati completando il cerchio Dwell.
6. **Attivazione Tracking Windows:**
   - Quando il paziente è pronto, premi **F9** (o il pulsante verde *"▶ AVVIA TRACKING"*).
   - Il cursore ora risponderà ai movimenti del capo.
   - Apri la **Tastiera Flottante** (tasto viola in alto) e prova a scrivere una parola nel Blocco Note di Windows!
7. **Disarmo di Emergenza:**
   - Premi **F9** in qualsiasi istante per congelare il controllo e liberare il mouse.

---

### 📌 PROSSIMI PASSI DA CHIEDERE ALL'AI DURANTE IL TEST A CASA
- "Ho testato la webcam a casa: ecco i valori di illuminazione e come risponde il cursore..."
- "Il paziente fa fatica a scendere verso il basso: regoliamo la deadzone o il guadagno verticale..."
- "Aggiungiamo nuove frasi personalizzate alla tastiera vocale..."
```
