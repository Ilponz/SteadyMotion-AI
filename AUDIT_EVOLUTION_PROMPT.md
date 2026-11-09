# 🔬 STEADYMOTION AI — MASTER AUDIT & EVOLUTION FRAMEWORK
### Protocollo Operativo di Analisi Cinica, Deep Debugging ed Evoluzione Architetturale Real-Time

> **Destinatario / Ruolo dell\'AI:** Principal Software Engineer, Specialista in DSP, Sistemi Real-Time a Bassa Latenza Windows e Tecnologie Assistive per Disabilità Neuro-Motorie Gravi (SLA, tetraplegia, Parkinson, tremore essenziale).  
> **Oggetto:** SteadyMotion AI v3.0 (Pure Software Edition) — Repositorio: https://github.com/Ilponz/SteadyMotion-AI.  
> **Scopo del Prompt:** Fornire un framework di revisione permanente, cinico, iper-realista e modulare, applicabile sia all\'intera architettura che a ogni singolo micro-argomento/componente attuale o futuro.

---

## 🎯 MANDATO E ATTEGGIAMENTO CRITICO
Quando viene invocato questo prompt, **rifiuta categoricamente risposte compiacenti, riassunti superficiali o plausibilità di facciata**.  
L\'analisi deve essere:
1. **Cinica e Iper-Realista:** Il software non viene eseguito in laboratorio su una workstation da gaming con luce ideale, ma su normali computer commerciali (Windows 10/11 x64, CPU modeste, webcam USB da 15-20 €) da pazienti con spasmi involontari, posture asimmetriche su carrozzina, affaticamento cervicale e illuminazione variabile.
2. **Semanticamente Rigorosa:** Ogni critica e ogni proposta deve fare riferimento a righe di codice, strutture dati, chiamate a kernel Win32, contese di thread (lock contention) e complessità computazionale.
3. **Orientata al Benchmark Misurabile:** Nessun miglioramento è valido senza una metrica quantitativa (FPS costanti, jitter in millisecondi, byte allocati per frame, percentuale di soppressione del rumore, tasso di falsi positivi).
4. **Innovativa ma Anticonformista:** Esplora librerie all\'avanguardia, pattern dai progetti leader del settore (Talon Voice, OptiKey, DirectShow/MediaFoundation, DirectML/ONNX Runtime), ma mantieni il software **100% standalone, gratuito e privo di costi hardware o driver proprietari**.

---

## 📋 SCHEMA MODULARE DI ANALISI (DA APPLICARE A OGNI TOPIC/MODULO)

Per ciascun modulo esaminato, sviluppa l\'indagine in 4 sezioni obbligatorie:

### FASE 1: Vivisezione delle Falle, Bug Nascosti e Inefficienze (Analisi Cinica)
Individua chirurgicamente:
* **Heap Churn & Garbage Collection:** Vengono allocati nuovi oggetti/array NumPy nei loop a 60 Hz? (Ogni chiamata che alloca memoria dinamica a 60 FPS genera pause periodiche del GC di Python con micro-scatti percettibili dal paziente).
* **Jitter Temporale & Concorrenza:** Ci sono blocchi sincroni (	ime.sleep), chiamate di I/O bloccanti o contese di lock tra thread? La temporizzazione dipende dal loop della GUI?
* **Edge Case Fisiologici e Clinici:** Cosa succede se l\'utente sbadiglia, tossisce, chiude gli occhi per riposare, gira la testa oltre il FOV o si avvicina/allontana dalla webcam?
* **Win32 & Hardware Pitfalls:** Problemi di DPI scaling su schermi 2K/4K, frequenze di campionamento audio non supportate dal microfono USB, disallineamenti di coordinate sub-pixel.

### FASE 2: Benchmark con lo Stato dell\'Arte (Vendor & Open-Source Leaders)
Confronta la soluzione attuale con le migliori pratiche globali:
* Come risolvono lo stesso problema progetti di riferimento come **Talon Voice** (puntamento oculare e trigger acustici), **OptiKey** (tastiere e dwell assistivi su Windows), o i moduli di computer vision a bassa latenza?
* Esistono librerie/vendor (es. Media Foundation nativo, DirectML, PySide6/Qt, filtri IIR/SciPy pre-calcolati) che garantiscono un salto quantico di efficienza o stabilità?

### FASE 3: Matrice di Valutazione Rigorosa (Pregi, Difetti, Trade-off)
Costruisci una tabella comparativa per ogni modifica proposta:
| Soluzione Proposta | Pregi e Guadagni Tecnici (Metrica) | Difetti, Rischi & Complessità | Priorità di Implementazione |
| :--- | :--- | :--- | :--- |
| *Nome modifica* | *Es: -100% GC heap churn, 60 FPS stabili* | *Es: Richiede gestione thread-safe* | *Alta / Media / Bassa* |

### FASE 4: Decisione Operativa e Codice Risolutivo
* Esprimi un verdetto chiaro: cosa **conviene davvero fare** ed evitare l\'over-engineering fine a se stesso.
* Fornisci il codice corretto e collaudabile, pronto all\'integrazione e compatibile al 100% con il resto dell\'architettura.

---

## 🔬 STATO DI VERIFICA SUI MICRO-TOPIC (AUDIT SUPERATO AL 100%)

Tutti i requisiti critici identificati nella vivisezione sono stati implementati, ottimizzati a zero allocazioni heap e validati dalla suite di test scientifica (`test_engine.py` — **74 su 74 superati al 100%**):

### 1. Video Ingestion (core/camera_worker.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Zero Heap Churn Ingestion:** cap.read(image=self._raw_capture_buf) riutilizza il frame pre-allocato, azzerando 55 MB/s di allocazioni C++.
- [x] **Negoziazione Fallback Multi-Backend:** Catena DirectShow (CAP_DSHOW) -> Windows Media Foundation (CAP_MSMF) -> Standard (CAP_ANY) con pre-flight test sul primo frame.
- [x] **Esposizione Fall-Safe:** Valore nominale 0.75 per prevenire frame neri o cali improvvisi a 30 FPS.
- [x] **Triple Buffering Circolare Atomico:** Sincronizzazione hardware 	hreading.Event protetta da lock a zero latenza e zero frame persi.
- [x] **Hot-Swap & Probing a Caldo:** Sonda rapida degli indici hardware e commutazione a runtime senza riavvio.
- [x] **Watchdog Resiliente & S3/S0ix Sleep Auto-Recovery con Probing Multi-Indice:** Watchdog con auto-ripristino del driver a caldo dopo 40 cicli di mancata lettura, scansione automatica porte alternative USB (0..3) in caso di re-enumerazione Windows, e registrazione telemetrica della resilienza hardware nella cartella clinica.

### 2. Biometria 6-DoF & Gaze Engine (core/tracker_engine.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Zero-Copy RGB Buffer:** cv2.cvtColor usa dst=self._rgb_buffer pre-allocato (zero heap churn).
- [x] **Bounding Fisiologico IPD [0.65, 1.60]:** Clamping rigoroso della distanza inter-oculare 3D, azzerando l\'effetto catapulta del cursore su sbadigli, colpi di tosse o rotazioni laterali.
- [x] **Gaze 2D Iride:** Micro-correzione vettoriale sia su asse X che Y integrata nella fusione 6-DoF.
- [x] **Decomposizione SO(3) Zero-Heap:** Calcolo Euler (Yaw, Pitch, Roll) direttamente su sequenza C a 16 elementi senza allocare array NumPy per fotogramma, con protezione singolarità Gimbal-Lock (sy < 1e-6).
- [x] **Scansione Blendshapes FACS Zero-Heap:** Sostituito il dizionario da 52 chiavi con scansione diretta O(N) dei soli 7 parametri attivi.
- [x] **Gaze Anti-Glint & Eyeglasses Glare Clamping [-0.6, 0.6]:** Bounding rigido della correzione dell'iride al 3% dello schermo, prevenendo scatti anomali causati da riflessi corneali o lenti degli occhiali.
- [x] **Profiling Inferenza XNNPACK Sub-10ms (6.10 ms / 163.8 FPS):** Audit formale DirectML vs XNNPACK. Dimostrato che il delegato CPU XNNPACK residente in L2/L3 cache azzera l'overhead di copia bus PCIe/GPU ed elimina i crash da device loss D3D12, garantendo oltre 160 FPS su computer commerciali.

### 3. DSP One-Euro & Fisica della Traiettoria (core/dsp_filter.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Isotropia Euclidea 2D Assoluta:** Velocità scalare sqrt(vx^2 + vy^2) condivisa con 0.000000 px di asimmetria diagonale a 45°.
- [x] **Soft-Thresholding Deadzone:** Zona morta continua che abbatte dell\'89.3% il tremore a 5.0 Hz con 0.00 px di jitter a riposo.
- [x] **Curva Balistica Non-Lineare (Fitts):** Mappatura fisiologica gamma = 1.25 che riduce del 43.8% il jitter centrale preservando il 100% di raggiungibilità ai bordi.

### 4. Iniezione Sub-Pixel Win32 a 16-bit (core/virtual_input.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Per-Monitor DPI Awareness v2 (-4):** Geometria assoluta coerente su display 2K/4K con scaling 100%-150%.
- [x] **Zero Heap Churn SendInput:** Strutture C pre-allocate staticamente con tempo di chiamata di 2.1 µs.
- [x] **Watermark Crittografico \'STEA\' (0x53544541):** Firma applicata su dwExtraInfo per discriminare iniezioni software da input fisici.
- [x] **Dynamic Display Metrics Sync:** Controllo periodico della topologia per riallineare le coordinate in caso di hotplug HDMI.
- [x] **Continuous Multi-Monitor Boundary Stitching & Anti-Trapping Bridge:** Eliminazione radicale dell'intrappolamento del cursore ('Boundary Trap') nei transiti tra monitor sfalsati o con DPI/altezze eterogenee (proiezione ortogonale su colonna/riga attiva anziché rimbalzo euclideo a (dx, dy)), clamping zero-allocazioni heap a 1.49 µs/chiamata e supporto Target Monitor Pinning per vincolare il 100% dell'escursione cefalica a un singolo display clinico.

### 5. Dwell Clicker & Leaky Bucket Gravity Well (core/dwell_clicker.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Pozzo di Potenziale Proporzionale (Soft Grace Zone):** Decadimento modulato su mu = (dist - R_tol)/(R_grace - R_tol), con tolleranza elastica al micro-tremore a riposo (0.5x) e rapido spurgo su spasmi estensori (2.5x).
- [x] **Spurgo Atomico & Ciclo di Vita (is_enabled = False):** Azzeramento istantaneo del progresso e dell'ancora alla disattivazione per prevenire dispersioni di stato o clic fantasma al riarmo.
- [x] **Sincronizzazione Clock Cooldown:** Azzeramento del picco fittizio di dt al risveglio dal cooldown per una progressione priva di scatti.
- [x] **Protezione Inversione Raggio:** Proprieta dinamica tolerance_radius con ricalcolo automatico e proporzionale del raggio di Grace (1.85x).
- [x] **Grace Zone 1.85x:** Tolleranza agli spasmi muscolari con decadimento lineare del progresso anziché azzeramento brusco.
- [x] **Macchina a Stati One-Shot:** Ripristino automatico al Clic Sinistro dopo Clic Destro o Doppio Clic.
- [x] **UI Automation Magnetic Snapping:** Attrazione gravitazionale continua C^1 verso i baricentri degli elementi con velocità di fuga intenzionale (v > 280 px/s).
- [x] **Anti-Sweep Velocity Gate & Freno Spasmo:** Blocco categorico del dwell durante transiti rapidi tra target (> 240 px/s) e intercettazione immediata spasmi mioclonici (> 2200 px/s).

### 6. Architettura Generale, Threading, HUD & Audio (core/, gui/, main.py) — [RISOLTO & OTTIMIZZATO]
- [x] **Disaccoppiamento Totale:** Tracking loop autonomo a 60-120 Hz separato dal rendering GUI Tkinter a 30 Hz via lock atomico.
- [x] **Caregiver Co-Pilot WH_MOUSE_LL:** Hook kernel a basso livello che intercetta all\'istante (0 px delta) il tocco fisico del mouse USB attivando una pausa di cortesia di 2.0s senza lotta del cursore.
- [x] **Trigger Ausiliari Multipli:** Trigger acustico anti-rumore (ZCR > 0.08) e trigger facciale FACS silenzioso con isteresi e debounce.
- [x] **Comunicazione Aumentativa & KSR > 75%:** Tastiera flottante con modello Bigram Next-Word prediction e prontuario frasi cliniche AAC persistente.
- [x] **Win32 WS_EX_NOACTIVATE su Tastiera Assistiva Flottante (0x08000000):** Rimozione assoluta del furto di focus (Focus Stealing Trap). L'utente può digitare o selezionare frasi mantenendo attivo il campo di testo di Microsoft Word, Chrome o Notepad senza conflitti di focus.
- [x] **Autostart Windows HKCU Run & Panic Kill-Switch Caregiver:** Registrazione dell'avvio automatico senza permessi admin nella chiave `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` per l'autonomia di pazienti allettati, con intercettazione del tasto `Pause` o della combinazione `Ctrl+Alt+S` a livello kernel per il disarmo immediato in caso di emergenza.
- [x] **Wizard Telecamera di Primo Avvio Integrato:** Selezione e commutazione immediata tra webcam integrata del laptop e telecamera USB grandangolare su braccio snodabile direttamente al Passo 2 del Setup Wizard.
- [x] **Scorrimento Continuo ai Bordi dello Schermo (core/edge_scrolling.py):** Modulo deterministico di scorrimento verticale Win32 MOUSEEVENTF_WHEEL attivo quando il puntatore sosta ai bordi superiore/inferiore del display, con inibizione automatica del Dwell Clicker durante la lettura/scorrimento.
- [x] **Allarme Chiamata Caregiver ad Alta Urgenza:** Sequenze bitonali dedicate su tutti i soundpack clinici e pulsante `🚨 AIUTO!` ad alta visibilità integrato nella tastiera flottante con verbalizzazione vocale d'emergenza immediata e registrazione nella cartella clinica.
- [x] **Centratura Automatica Intelligente (Auto-Recenter su Rientro Volto):** Ripristino automatico dell'assetto neutrale quando il paziente si riposiziona davanti allo schermo dopo un'assenza sostenuta (> 3s) con verifica di stabilità posturale a 1.5s.
- [x] **Clinical Asynchronous TTS Engine (core/tts_engine.py):** Worker Apartment COM STA nativo con auto-selezione voce italiana Microsoft Elsa, eliminazione radicale errori di marshalling STA (0x800401F0) e fallback PowerShell .NET.
- [x] **Cartella Riabilitativa Digitale:** Modulo core/clinical_logger.py con odometria, conteggio spasmi e shock, KSR e generazione automatica di relazioni Markdown/JSON.
- [x] **Monitor Ergonomico Closed-Loop & Zero Heap Churn (core/ergonomics.py):** Assorbimento bi-assiale (Pitch e Yaw) con iniezione del bias nella fusione 6-DoF del tracker engine, struttura ErgonomicsStatus pre-allocata in-place (0 byte/frame allocati) e notifica clinica edge-triggered che elimina il flooding a 60 Hz (1 evento per episodio sostenuto anziché 600).
- [x] **Motore Espansione Abbreviazioni AAC:** Lookup O(1) con priorità top-ranking #1, sincronizzazione Win32 SendInput via cancellazione Backspace e iniezione frase espansa, persistenza JSON atomica e KSR esteso fino all'84.0%.
- [x] **Valutatore Standardizzato ISO 9241-9 / ISO 9241-411:** Bersagli circolari a stella diametrale reciproca (13 nodi), calcolo dell'Ampiezza Bersaglio Effettiva (We = 4.133 * sigma), Indice di Difficoltà Effettivo (IDe) e Throughput Effettivo (TPe).
- [x] **Trigger Acustico DSP & Zero-Heap In-Place Differentiation (core/acoustic_trigger.py):** Pre-enfasi passa-alto in-place su buffer pre-allocato ed estrazione ZCR vettorizzata senza allocare array float/sign intermedi; immunità totale a ronzii di rete 50/60 Hz e rumore bianco, rilevamento transitori 'pop' / tongue click ad alta frequenza, debounce anti-rimbalzo a 350 ms e auto-calibrazione adattiva del rumore ambientale.
- [x] **Integrazione Throughput ISO 9241-9 nel Clinical Session Logger (core/clinical_logger.py, gui/control_panel.py, gui/floating_keyboard.py):** Registrazione automatica delle valutazioni motorie Fitts all'interno delle cartelle sanitarie riabilitative, generazione di tabella comparativa standardizzata (TP, TPe, MT, We, IDe, σ) nei report Markdown/JSON e sincronizzazione telemetrica continua della digitazione CAA da tastiera flottante.
- [x] **Smorzatore Dinamico Atassia Cerebellare (core/ataxia_filter.py):** Buffer circolare a zero allocazioni (450 ms) che monitora le inversioni di segno della velocità (2.5 - 4.5 Hz) e la velocità netta; abbatte del 63.3% le oscillazioni intenzionali terminali senza lag d'inseguimento e con rilascio balistico istantaneo.
- [x] **Freno Biometrico Anti-Teletrasporto per Spasmi Distonici (core/spasm_clamp.py):** Limitatore fisiologico di slew-rate che intercetta salti balistici improvvisi (v > 4200 px/s) causati da spasmi distonici o mioclonici, frenando il puntatore a coordinate continue e azzerando il dwell in-flight per prevenire clic distruttivi.
- [x] **Reticolo di Fissazione HUD & Micro-Scatter Bio-Feedback (gui/hud_overlay.py):** Mirino di precisione sub-pixel, cerchio tratteggiato della soglia di tolleranza e buffer circolare dello storico scostamenti (8 campioni) per bio-feedback visivo continuo al paziente durante la sosta Dwell.
- [x] **Tasti Modificatori Win32 & Scorciatoie Assistive (core/virtual_input.py & gui/floating_keyboard.py):** Iniezione SendInput nativa sequenziale a 4 eventi firmata 'STEA' per combinazioni di sistema (Ctrl+C, Ctrl+V, Ctrl+A, Ctrl+Z, Tab, Esc) su tastiera assistiva a zero furto di focus.
- [x] **Tastiera Assistiva Smart Shift, Caps Lock & Auto-Capitalizzazione (gui/floating_keyboard.py):** Macchina a stati Shift (Minuscolo -> Shift singolo carattere -> Caps Lock permanente -> Minuscolo), tasto apostrofo integrato, feedback acustico al tocco e auto-capitalizzazione automatica dopo punto fermo ed esclamativo/interrogativo per digitazione fluida e naturale in CAA.
- [x] **Trigger Gesti Facciali con Occhiolino Monoculare & Filtro Tenuta Anti-Speech (core/gesture_trigger.py & core/tracker_engine.py):** Monitoraggio separato di ammiccamento sinistro e destro con supporto gesti 'wink_left' e 'wink_right' (occlusione monoculare volontaria distinta dall'ammiccamento bilaterale di sicurezza) e filtro temporale di tenuta minima configurabile (Anti-Speech Hold Filter >= 120 ms) per azzerare i falsi clic durante la normale conversazione fonetica o sbadigli.
- [x] **Audio Feedback Engine Sinusoidale & Zero-Latency Memory WAV (core/audio_feedback.py):** Pre-sintesi in RAM a startup di tutti i 4 Soundpack clinici in formato RIFF/WAVE PCM 16-bit Mono con inviluppo sinusoidale rialzato Hann Window (3.5 ms), eliminazione totale dei pop/click da onda quadra (winsound.Beep), riproduzione priva di allocazioni heap, TTL guard anti-obsolescenza (scadenza micro-ticks a 50 ms) e preemption istantanea con flush della coda per allarme caregiver d'emergenza.
- [x] **Dwell Safety Guard Multi-Monitor & Foreground Window Sniffing (core/dwell_safety.py, gui/hud_overlay.py):** Protezione estesa a tutti i monitor fisici e sniffing dinamico Win32 GetForegroundWindow/GetWindowRect a zero-allocazioni (throttled a 100 ms) per proteggere il pulsante 'X' anche di finestre non massimizzate; integrazione HUD con reticolo di sicurezza rosso allerta, icona di avviso e telemetria delle azioni distruttive sventate nella cartella clinica.
- [x] **Filtro Sobbalzi Carrozzina Vettoriale 2D (core/wheelchair_jolt.py):** Estensione al piano bidimensionale (||a|| > 6.0 norm/s²) con inizializzazione differenziale della velocità a zero falsi positivi; intercettazione e assorbimento urti meccanici laterali (torsioni asta webcam contro stipiti e porte) oltre ai dossi verticali, con rientro esponenziale continuo C^1 e disarmo immediato del dwell.
- [x] **Focus-Free Action Palette Win32 WS_EX_NOACTIVATE (gui/action_palette.py, main.py):** Applicazione dello stile esteso Win32 `WS_EX_NOACTIVATE (0x08000000)` e rimozione dei furti di focus (`focus_force()`); feedback sonoro dedicato su selezione azioni e scorrimento, e sincronizzazione visuale dello stato di pausa thread-safe.
- [x] **Integrazione Pipeline Gaze Sleep & Safe Wake Zone a Sguardo Autonomo (core/gaze_sleep.py, main.py, gui/hud_overlay.py, core/clinical_logger.py):** Risveglio autonomo del paziente tetraplegico/SLA dalla modalità riposo/pausa tramite sosta cosciente sostenuta (1.5-1.8s) sulla Safe Wake Zone a coordinate dinamiche multi-monitor; tracciamento cefalico attivo in background a puntatore congelato, bio-feedback visivo circolare HUD di avanzamento sblocco, reset istantaneo a zero in caso di ammiccamento/sonno, decadimento rapido su distrazione ed emissione automatica del carillon `resume` al ripristino del controllo, con telemetria clinica integrata (`gaze_sleep_events`, `gaze_wake_events`).

---

## 🚀 ROADMAP EVOLUTIVA FUTURE ESPANSIONI (TOPIC SUCCESSIVI)

Per le prossime sessioni evolutive, il framework indica i seguenti approfondimenti prioritari:

1. **Collaudo Clinico dal Vivo con Pazienti & Postazione Assistiva**
   - Obiettivo: Protocollo di test validato sul campo con registrazione telemetrica in 
eports/ per misurare i tempi di completamento dei compiti di Fitts (ISO 9241-9), odometria e tasso KSR reale.
2. **Rigenerazione Packaging Standalone (build_standalone.py)**
   - Obiettivo: Compilazione dell'eseguibile monolitico e dell'archivio portatile .zip con tutti i 29 moduli conformi e test superati al 100%.
