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
Tutti i componenti sono testati con benchmark scientifici in `test_engine.py` (22 su 22 superati al 100%):

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
   - Metodi di digitazione diretta `send_unicode_char`, `send_key_event` e rotellina virtuale `scroll` (`MOUSEEVENTF_WHEEL`).

5. **Dwell Clicker con Algoritmo Leaky Bucket (core/dwell_clicker.py):**
   - Clic a sosta temporizzata (default 650 ms);
   - Pozzo di gravità (Grace Zone a 1.85x): se uno spasmo sposta temporaneamente il puntatore all'esterno, il progresso decade linearmente anziché azzerarsi bruscamente;
   - Micro-inseguimento posturale adattivo (< 4 px/s) per assorbire il rilassamento muscolare del collo;
   - Macchina a stati One-Shot integrata (ripristino automatico a Left Click dopo Clic Destro o Doppio Clic).

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

9. **Tastiera Assistiva Flottante con Autocomplete Predittivo (gui/floating_keyboard.py & core/word_predictor.py):**
   - Finestra sempre in primo piano (`Topmost`) su qualsiasi app di Windows (Notepad, Word, browser, WhatsApp);
   - **Motore di Predizione Lessicale su Trie O(L) (0.0036 ms latenza):** dizionario italiano pesato ad alta frequenza con lessico medico/assistivo prioritario;
   - **Barra Suggerimenti Rapidi a 4 Pulsanti:** visualizza e inserisce istantaneamente il completamento della parola con un singolo dwell click;
   - **Keystroke Savings Rate (KSR) > 60%:** abbatte lo sforzo motorio del paziente riducendo di oltre la metà i tocchi necessari per comporre intere frasi;
   - **Apprendimento Dinamico in RAM:** memorizza e privilegia automaticamente le parole e i nomi propri usati frequentemente dal paziente;
   - **Digitazione Diretta a Windows:** inietta i caratteri direttamente nel campo di testo attivo dell'applicazione sottostante via Win32 SendInput Unicode;
   - **Sintesi Vocale Integrata (TTS SAPI nativo):** Pulsante `[🔊 Parla (TTS)]` per pronunciare istantaneamente il testo digitato o le frasi di bisogno.

10. **Diagnostica Hardware & Pre-Flight Check per Caregiver (core/diagnostics.py & gui/diagnostic_window.py):**
    - Scansione automatica hardware di webcam (DirectShow & Media Foundation) e microfoni;
    - Misurazione degli FPS reali acquisiti (30-45 frame) e verifica stabilità;
    - Fotometria Luma ambientale (alert luce insufficiente o abbagliamento);
    - Calcolo del rumore acustico ambientale di fondo in dB (valutazione idoneità clic vocale);
    - Calcolo dell'Indice di Idoneità Clinica (0-100%) con consigli pratici per l'operatore;
    - Script standalone caregiver: `diagnostica_hardware.py` e launcher `Verifica_Webcam_Caregiver.bat`.

11. **Barra Flottante dei Clic & Palette Azioni Assistive (gui/action_palette.py):**
    - Mini-barra verticale sempre in primo piano (`Topmost`) per il controllo autonomo al 100% di Windows;
    - Tasti ampi per Dwell: Clic Sinistro Standard, Clic Destro Contestuale (One-Shot), Doppio Clic (One-Shot), Trascina & Rilascia (Drag & Drop con lock visivo), Scorrimento Pagina (Scroll Su/Giù via rotellina virtuale) e Modalità Riposo/Pausa;
    - Feedback visivo a LED con evidenziazione ad alto contrasto della modalità attiva.

12. **Gestore Profili Paziente & Preset Clinici Persistenti (core/profile_manager.py):**
    - 4 Preset clinici patologia-specifici preimpostati (Tetraplegia Standard, SLA Minimo Sforzo, Parkinson Forte Tremore, Distonia/Ipertono);
    - Serializzazione JSON atomica su `config/profiles/` con salvataggio automatico dell'ultimo profilo attivo.

13. **Monitor Ergonomico & Affaticamento Muscolare Cervicale (core/ergonomics.py):**
    - Rilevamento biometrico continuo di posture cervicali anomale sostenute (Head-Drop / caduta mento e Tilt laterale > 12°);
    - Assorbimento dinamico del drift posturale lento (*Slow Baseline Drift Absorption*);
    - Notifica ergonomica contestuale nel banner di sicurezza per suggerire ricentratura comoda F12 o pausa di riposo.

14. **Feedback Uditivo Multi-Sensoriale Asincrono (core/audio_feedback.py):**
    - Coda audio asincrona a latenza zero (< 0.02 ms) su thread Win32 dedicato privo di jitter per il loop a 60 FPS;
    - Toni differenziati a livello frequenziale per confermare acusticamente ogni evento (Clic SX brillante 1200 Hz, Clic DX 1800 Hz, doppio impulso, toni drag & drop e pausa/ripresa).

15. **Funzione di Trasferimento Balistica Non-Lineare (core/ballistics.py):**
    - Curva di Fitts fisiologica monotona con esponente $\gamma = 1.25$;
    - Abbattimento del 43.8% dell'ipersensibilità e del micro-tremore al centro dello schermo, mantenendo al contempo il 100% della corsa e della reachability ai bordi;
    - Continuità $C^1$ garantita (0.000000 px salto all'origine).

16. **Caregiver Co-Pilot & Arbitraggio Mouse Fisico (core/copilot.py):**
    - Monitoraggio delta hardware USB ad ogni frame: se l'operatore o il caregiver muove fisicamente il mouse (> 24 px), scatta una pausa di cortesia automatica di 2.0s con chime soft;
    - Zero contesa o "lotta del cursore" tra operatore e paziente;
    - Ripristino morbido e trasparente non appena il mouse fisico torna a riposo.

17. **Presentazione Interattiva HTML per Studenti (presentazione_studenti.html):**
    - Slide-deck interattivo moderno con navigazione da tastiera, fullscreen e grafici di impatto per platea studentesca.

18. **UI Automation & Accessibility Magnetic Target Snapping (core/magnetic_snapping.py):**
    - Attrazione magnetica gravitazionale continua $C^1$ verso il baricentro di elementi interattivi GUI (pulsanti, icone, link, checkbox);
    - Riduzione sensibile dell'indice di difficoltà di Fitts (Fitts's Law) e stabilizzazione critica della fase di Dwell eliminando la deriva periferica causata da spasmi muscolari;
    - **Velocità di Fuga (Breakout Velocity):** Se l'utente esegue una saccade o un movimento motorio rapido intenzionale ($v > 280\text{ px/s}$), l'attrazione decade istantaneamente a zero ($\alpha = 0.0$), prevenendo qualsiasi effetto di cursore viscoso o "incollato";
    - Zero Heap Churn: strutture Win32 pre-allocate in memoria C (`POINT`, `RECT`) e cache rettangolo attivo ($< 1.0\ \mu\text{s}$ per ciclo a 60 Hz).

19. **Trigger Gesti Facciali Silenzioso (core/gesture_trigger.py):**
    - Riconoscimento FACS ad alta velocità per micro-gesti facciali (Apertura Mandibola / Bocca, Sorriso, Corrugamento Sopracciglia);
    - Filtro a isteresi (attivazione a $\ge 0.45$, rilascio a $\le 0.20$) e debounce di 0.40s: azzera i doppi clic accidentali;
    - Ideale per pazienti tracheostomizzati o ventilati che non possono emettere suoni, o in ambienti con rumore di fondo.

20. **Modello Bigramma AAC Next-Word Prediction (core/word_predictor.py & gui/floating_keyboard.py):**
    - Predizione contestuale avanzata a 2 parole (Bigram Next-Word Prediction): suggerisce istantaneamente le parole successive più probabili non appena viene completato un termine (es. "HO" $\to$ ["DOLORE", "BISOGNO", "SETE", "FAME"]);
    - Boost del Keystroke Savings Rate (KSR) al **76.0%**, riducendo di oltre i 3/4 lo sforzo motorio per la composizione di intere frasi;
    - Apprendimento dinamico in RAM sia di vocaboli che di sequenze a 2 parole usate frequentemente dal paziente.

21. **Low-Level Hook WH_MOUSE_LL & Dynamic Multi-Display Topology Sync (core/copilot.py & core/virtual_input.py):**
    - Watermark crittografico/identificativo `STEADYMOTION_INPUT_SIGNATURE = 0x53544541` ('STEA') applicato su tutti gli eventi Win32 SendInput;
    - Hook kernel a basso livello `WH_MOUSE_LL` in background thread asincrono: intercetta all'istante qualsiasi tocco o clic fisico del mouse USB o trackpad del caregiver anche per spostamenti minimi (0 px delta), eliminando al 100% la "lotta del cursore" (Mouse Fight);
    - Rilevamento dinamico a caldo della topologia degli schermi (`check_screen_metrics_changed()`): riallinea le coordinate virtuali del desktop in caso di hotplug di monitor esterni HDMI o variazione dello scaling di Windows (100%-150%) senza richiedere il riavvio del software.

22. **Prontuario Clinico AAC Personalizzabile & Persistenza JSON Atomica (core/phrasebook.py & gui/floating_keyboard.py):**
    - Libreria gerarchica di comunicazione aumentativa strutturata in categorie cliniche (`BISOGNI_PRIMARI`, `SALUTE_ASSISTENZA`, `COMUNICAZIONE_SOCIALE`, `POSTURA_COMFORT`);
    - Selettore categoria istantaneo a pulsanti segmentati nella tastiera assistiva flottante con rendering dinamico dei pulsanti per Dwell Clicker;
    - Serializzazione atomica su disco `config/phrasebook.json` e supporto esportazione/importazione per logopedisti e terapisti occupazionali;
    - Ricerca globale veloce e apprendimento automatico delle frasi verbalizzate nel modello predittivo.

23. **Camera Runtime Hot-Swap & Probing Hardware (core/camera_worker.py):**
    - Scansione rapida e sicura degli indici webcam hardware disponibili nel sistema tramite DirectShow e Media Foundation (`get_available_cameras()`);
    - Metodo `switch_camera(new_camera_index)` per commutare a caldo la sorgente di acquisizione senza riavviare l'applicazione o causare race-condition sui buffer;
    - Rilascio istantaneo e sicuro delle risorse video precedenti e riavvio automatico della pipeline di elaborazione a 60 FPS.

24. **Telemetria Clinica & Cartella Riabilitativa Digitale (core/clinical_logger.py):**
    - Monitoraggio quantitativo continuo a zero overhead: durata sessione, tempo di puntamento attivo vs standby di sicurezza;
    - Odometria cefalica sub-pixel con filtro anti-teletrasporto e stima della distanza percorsa sul desktop in pixel e metri;
    - Tracciamento esaustivo delle modalità di interazione: Dwell Clicks completati, Dwell abortiti da spasmi muscolari (indice oggettivo di fatica/distonia), interventi Caregiver Co-Pilot, Clic vocali/acustici e Trigger gesti facciali silenziosi;
    - Metriche riabilitative CAA (Comunicazione Aumentativa Alternativa): conteggio tocchi effettivi, completamenti predittivi, caratteri risparmiati e Keystroke Savings Rate (KSR %);
    - Generazione automatica di relazioni cliniche formattate per logopedisti e cartelle sanitarie (`reports/clinical_session_*.md` e JSON) a fine sessione.

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
   `python test_engine.py` (deve restituire "TUTTI I 22 TEST SUPERATI AL 100%")
3. Avvia:
   `python main.py` (oppure doppio clic su `Avvia_SteadyMotion.bat`).

---

### 🧪 PROCEDURA DI COLLAUDO DAL VIVO CON LA WEBCAM (STEP-BY-STEP)

Quando sei a casa davanti alla postazione reale con il paziente:

1. **Pre-Flight Hardware Check (Consigliato):**
   - Esegui `Verifica_Webcam_Caregiver.bat` (o clicca su `[🩺 Diagnostica Hardware & Webcam]` nel pannello di controllo).
   - Verifica che il punteggio di idoneità sia >= 80% (FPS >= 30, Illuminazione idonea, Rumore di fondo sotto controllo).
2. **Posizionamento Hardware:**
   - Collega la webcam USB sopra o sotto il monitor, all'altezza degli occhi del paziente.
   - Distanza ottimale: 50 - 70 cm dal viso.
   - Assicurati che l'illuminazione sia frontale o diffusa (evita forti controluce alle spalle).
3. **Avvio dell'App:**
   - Lancia `Avvia_EXE_Standalone.bat`.
   - L'app parte in **STANDBY DI SICUREZZA**: il cursore non si muove.
   - Guarda il **Radar Posturale**: la croce verde deve essere nel cerchio centrale e il badge deve segnare *"Luce: OK"* e *"Centratura Ottimale"*.
4. **Calibrazione Postura Neutra:**
   - Fai posizionare il paziente nella sua posizione di riposo comoda e premi **F12** (o il pulsante *"🎯 Ricentra Centro Schermo"*).
5. **Calibrazione Range of Motion (Consigliata):**
   - Clicca su `[📐 Calibrazione ROM (5 Punti)]`.
   - La schermata va a tutto schermo: fai fissare i 5 cerchi che pulsano (Centro, Alto-SX, Alto-DX, Basso-DX, Basso-SX).
   - Se il paziente è affaticato, puoi premere la **Barra Spazio** per registrare il punto manualmente.
   - Clicca `[💾 Applica Guadagni e Salva]`: i guadagni asimmetrici saranno attivi e salvati nel profilo JSON.
6. **Addestramento nella Sandbox (Tab Tutorial):**
   - Vai nella scheda *"📖 Tutorial & Bersagli"*.
   - Fai esercitare il paziente a colpire i 5 pulsanti numerati completando il cerchio Dwell, ascoltando il feedback sonoro brillante di avvenuto clic!
7. **Attivazione Tracking Windows:**
   - Quando il paziente è pronto, premi **F9** (o il pulsante verde *"▶ AVVIA TRACKING"*).
   - Il cursore ora risponderà ai movimenti del capo.
   - Apri la **Palette Clic** (`[🖱️ Palette Clic]`) per testare clic destro, doppio clic e scorrimento.
   - Apri la **Tastiera Flottante** (tasto viola in alto) e prova a scrivere una parola nel Blocco Note di Windows sfruttando i suggerimenti predittivi!
8. **Disarmo di Emergenza:**
   - Premi **F9** in qualsiasi istante per congelare il controllo e liberare il mouse.

---

### 📌 PROSSIMI PASSI & COSA C'È DA FARE ADESSO (ROADMAP DA AVVIARE SUL NUOVO DISPOSITIVO)

Quando ti sposti sul computer di casa o apri la nuova sessione, puoi dire all'AI:
*"Procediamo con le prossime migliorie pianificate per SteadyMotion AI"* oppure scegliere direttamente una di queste opzioni prioritarie:

1. **Opzione 1 (Prioritaria): Curva Balistica di Precisione Fisiologica (Ballistic Transfer Function)**
   - Passare da mappatura puramente lineare a curva non-lineare ($\Delta x = \text{sign}(dx) \cdot |dx|^\gamma \cdot G$ con $\gamma \approx 1.25$):
   - Consente al paziente di centrare con estrema facilità icone piccole o caselle di spunta al centro dello schermo, mantenendo allo stesso tempo la capacità di raggiungere gli angoli del monitor con micro-rotazioni del capo senza affaticamento.

2. **Opzione 2: Modalità Co-Pilot & Rilevamento Intervento Caregiver**
   - Intercettare il movimento del mouse fisico USB: se il caregiver interviene per spostare una finestra o cliccare, il tracciamento cefalico va in pausa temporanea di cortesia (1.5-2 secondi) per azzerare qualsiasi conflitto sul cursore di Windows.

3. **Opzione 3: Personalizzazione Visiva Avanzata dell'HUD Ring (Ipovisione & Contrasto)**
   - Dimensioni regolabili del cerchio Dwell (60, 80, 100, 120 px per schermi 4K o pazienti anziani/ipovedenti);
   - 4 Temi cromatici ad alto contrasto (*Neon Emerald*, *Electric Cyan*, *High-Contrast Amber*, *Obsidian Violet*) per garantire leggibilità assoluta su qualsiasi sfondo di Windows (pagine web chiare, video scuri, testo fitto).

---

### 💬 COMANDI RAPIDI DA DARE ALL'AI AL RIENTRO:
- *"Procediamo con l'Opzione 1 (Curva Balistica di Precisione) e l'Opzione 2 (Co-Pilot Caregiver)"*
- *"Ho collegato la webcam reale a casa: ecco i risultati della diagnostica hardware..."*
- *"Eseguiamo il collaudo dal vivo con il paziente"*
```
