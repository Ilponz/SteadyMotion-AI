# 💻 PROCESSI DEL CICLO DI VITA DEL SOFTWARE (CEI EN 62304:2006/A1:2015)
### SteadyMotion AI — Software as a Medical Device (SaMD)

---

## 1. CLASSIFICAZIONE DELLA SICUREZZA DEL SOFTWARE
Ai sensi del paragrafo 4.3 della norma EN 62304:
* SteadyMotion AI è classificato come **Classe di Sicurezza A**:
  * *Motivazione:* Il software non può contribuire a una situazione pericolosa in grado di causare lesioni o danni fisici alla salute del paziente o dell'operatore. Il software agisce unicamente come interfaccia di emulazione periferica di puntamento (Human Interface Device).

---

## 2. MODELLO DI SVILUPPO E CONTROLLO CONFIGURAZIONE
* **VCS (Version Control System):** Git con cronologia completa di commit semantici (`feat`, `fix`, `test`, `chore`, `docs`).
* **Repository Istituzionale:** `https://github.com/Ilponz/SteadyMotion-AI`
* **Automazione dei Test (CI/CD Locale):** Esecuzione della suite scientifica `test_engine.py` (35 test unitari e matematici rigorosi).
* **Gestione dei Rilasci:** Branch `main` protetto e tag di versione (es. `v3.0.0-clinical`).

---

## 3. MATRICE DI TRACCIABILITÀ REQUISITI - TEST (V&V MATRIX)

| ID Requisito (SRS) | Descrizione della Funzione Medica | Modulo Software | Test Unitario di Validazione (`test_engine.py`) | Esito |
| :--- | :--- | :--- | :--- | :---: |
| **REQ-DSP-01** | Filtro 1€ isotropo 2D con abbattimento tremore patologico $\ge 85\%$ a 5 Hz | `core/dsp_filter.py` | `test_point_filter_2d()` (Test 1) | **100% PASS** (89.3% misurato) |
| **REQ-DSP-02** | Isotropia Euclidea 2D: zero asimmetria su traiettorie diagonali a 45° | `core/dsp_filter.py` | `test_euclidean_isotropy_45deg()` (Test 2) | **100% PASS** (0.000000 px scarto) |
| **REQ-DWL-01** | Dwell Clicker con tolleranza elastica (Soft Grace Zone 1.85x) | `core/dwell_clicker.py` | `test_dwell_clicker_leaky_bucket()` (Test 3) | **100% PASS** |
| **REQ-DWL-02** | Anti-Sweep Gate ($v > 240$ px/s) e Freno Spasmo Mioclonico ($v > 2200$ px/s) | `core/dwell_clicker.py` | `test_dwell_anti_sweep_gate_and_spasm_shock()` (Test 28) | **100% PASS** |
| **REQ-WIN-01** | Iniezione sub-pixel Win32 a 16-bit con watermark extra-info (`0x53544541`) | `core/virtual_input.py` | `test_virtual_input_controller()` (Test 4) | **100% PASS** (4.0 µs latenza) |
| **REQ-BIO-01** | Tracciamento cefalico 6-DoF con salvaguardia singolarità Gimbal-Lock ($sy < 10^{-6}$) | `core/tracker_engine.py` | `test_tracker_engine_and_so3_decomposition()` (Test 5) | **100% PASS** |
| **REQ-CAM-01** | Triple buffering asincrono e sincronizzazione hardware Event-Driven | `core/camera_worker.py` | `test_camera_worker_buffers()` (Test 6) | **100% PASS** |
| **REQ-ROM-01** | Calibrazione ROM asimmetrica a 5 punti per mobilità ridotta | `gui/calibration_window.py` | `test_calibration_and_gain_mapping()` (Test 7) | **100% PASS** ($C^0$ continuo) |
| **REQ-AAC-01** | Autocomplete predittivo con Keystroke Savings Rate (KSR) $\ge 60\%$ | `core/word_predictor.py` | `test_word_predictor_and_ksr()` (Test 8) | **100% PASS** (60.7% Trie / 84% Bigram) |
| **REQ-AAC-02** | Espansione istantanea abbreviazioni cliniche salvavita | `core/word_predictor.py` | `test_aac_abbreviation_expansion_and_keystroke_amplification()` (Test 32) | **100% PASS** |
| **REQ-COP-01** | Arbitraggio Caregiver Co-Pilot con precedenza assoluta mouse USB | `core/copilot.py` | `test_caregiver_copilot()` (Test 14) | **100% PASS** (Zero lotta) |
| **REQ-ERG-01** | Monitoraggio ergonomico postura cefalica con assorbimento drift e alert | `core/ergonomics.py` | `test_ergonomics_monitor()` (Test 11 e 31) | **100% PASS** (Edge-triggered) |
| **REQ-FIT-01** | Valutatore standardizzato Fitts ISO 9241-9 a bersagli circolari | `core/fitts_evaluator.py` | `test_fitts_evaluator_iso_9241_9()` (Test 16 e 33) | **100% PASS** |
| **REQ-LOG-01** | Cartella riabilitativa digitale e report di sessione Markdown/JSON | `core/clinical_logger.py` | `test_clinical_session_logger_and_report_generation()` (Test 17 e 35) | **100% PASS** |

---

## 4. PIANO DI MANUTENZIONE E GESTIONE DELLE MODIFICHE
Ogni release software deve essere accompagnata dall'esecuzione automatizzata dell'intera suite `test_engine.py`. Eventuali bug o segnalazioni post-commercializzazione vengono registrati con ticket su GitHub, analizzati secondo la procedura FMEA (ISO 14971) e risolti con test di regressione dedicati prima del rilascio dell'aggiornamento.
