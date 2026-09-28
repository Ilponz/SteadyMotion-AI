# SteadyMotion AI 🎯

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-emerald.svg)](https://www.python.org/)
[![Hardware Cost](https://img.shields.io/badge/Hardware_Cost-0_€-brightgreen.svg)]()
[![Tremor Reduction](https://img.shields.io/badge/Tremor_Attenuation-90.2%25-purple.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows_10%20%7C%2011-blue.svg)]()

> **Sistema di puntamento assistivo 100% software ad alte prestazioni.**  
> Trasforma qualunque comune webcam commerciale in un'interfaccia di puntamento stabile, ultra-fluida e precisa, annullando il costo di dispositivi proprietari (2.000 € – 5.000 €) ed eliminando la necessità di qualsiasi hardware o microcontrollore esterno.

---

## 🌟 Caratteristiche Principali

* **100% Software Standalone (Zero Costi Hardware):** Funziona direttamente su Windows senza bisogno di dongle, chip o microcontrollori esterni (nessun Raspberry Pi).
* **Filtraggio One-Euro + Dynamic Sub-Pixel Deadband:** Abbattimento matematico del **90.2% delle oscillazioni da tremore patologico** (Parkinson, tremore essenziale) con blocco granitico a testa ferma e zero ritardo nei movimenti rapidi.
* **EAR Palpebrale Clamping:** Rileva istantaneamente l'ammiccamento (battito di ciglia) e congela il puntatore per eliminare il tipico scatto parassita di 3–8 pixel presente nei comuni tracciatori facciali.
* **Dwell Clicker Multi-Modale (Clic a Sosta):** Esegue il clic sinistro/destro/doppio stazionando per 650 ms sul bersaglio, con un indicatore radiale trasparente a schermo interamente permeabile (*click-through* via API Win32 `WS_EX_TRANSPARENT`).
* **Trigger Acustico Ausiliario (Microfono Webcam - 0 €):** Consente agli utenti con ridotta mobilità muscolare facciale di cliccare all'istante emettendo un breve soffio d'aria (*puff*) o schiocco di lingua (*pop*) intercettato dal microfono integrato della webcam.
* **Pipeline Video Zero-Copy a 60 FPS:** Thread di acquisizione dedicato su DirectShow (`buffer=1`), sblocco FourCC `MJPG` e doppio buffer pre-allocato lock-free per azzerare il lag accumulato e annullare l'overhead del Garbage Collector.
* **Disaccoppiamento Normativo UE MDR 2017/745:** Strutturato in conformità con la linea guida **MDCG 2021-24 Sezione 3.2.1** come ausilio informatico di accessibilità digitale universale, esente da gravosi obblighi di certificazione medica CE.

---

## 🏗️ Architettura del Sistema

```
Webcam Commerciale (USB)
   │
   ▼
[ CameraWorker (DirectShow, Buffer=1, MJPG 60 FPS, Zero-Copy Ring) ]
   │
   ▼
[ FaceTrackerEngine (Google MediaPipe FaceLandmarker Tasks) ]
   ├── Matrice 6-DoF Rigid Head Pose (Yaw, Pitch, Roll)
   ├── 52 Blendshapes FACS (Blink, Jaw, Smile)
   └── EAR Blink Clamping (Δp = 0 durante l'ammiccamento)
   │
   ▼
[ PointFilter2D (One-Euro Filter Casiez CHI 2012 + Dynamic Deadband) ]
   ├── Attenuazione Tremore a 5 Hz (-20.2 dB / 90.2%)
   └── Curva di Guadagno Sigmoide (Fitts's Law Transfer Function)
   │
   ▼
[ DwellClicker + AcousticTrigger (Microfono) ]
   │
   ▼
[ WindowsMouseController (Win32 SendInput 64-bit API) ]
   └── Spazio Desktop Virtuale Multi-Monitor 4K
```

---

## 🚀 Avvio Rapido

### Prerequisiti
* Windows 10 o Windows 11 (64-bit);
* Python 3.10 o superiore;
* Una comune webcam USB integrata o esterna (720p o 1080p).

### Installazione Dipendenze Gratuite
```bash
pip install opencv-python mediapipe numpy pywin32 sounddevice python-docx
```

### Avvio dell'Applicazione
È sufficiente fare doppio clic sul file batch:
```cmd
Avvia_SteadyMotion.bat
```
Oppure eseguire via terminale:
```bash
python main.py
```

---

## ⌨️ Tasti di Scelta Rapida Globali (Hotkey)

Funzionano in qualsiasi finestra o programma aperto su Windows:
* **`F12`**: **Ricentra Calibrazione** — Imposta la posizione corrente del capo come centro esatto dello schermo.
* **`F9`**: **Pausa / Riprendi** — Mette istantaneamente in pausa il tracciamento del mouse per riposarsi o consultare lo schermo.

---

## 🧪 Validazione e Benchmark Sperimentale

Il repository include una suite di collaudo automatico per verificare la robustezza matematica:
```bash
python test_engine.py
```

### Risultati del Banco Prova:
* **Attenuazione del Tremore (5.0 Hz):** Deviazione grezza $8.00\text{ px} \to$ Deviazione filtrata **$0.79\text{ px}$** (**90.2% di soppressione**).
* **Stabilità da Fermo:** Deviazione **$0.00\text{ px}$** grazie alla Dynamic Deadzone elastica.
* **Affidabilità Dwell:** 100% di precisione temporale sulla soglia di sosta.
* **Latenza di Calcolo:** $5.8\text{–}8.2\text{ ms}$ per frame su normale CPU (pienamente conforme a 60 FPS).

---

## 👥 Autori e Riconoscimenti

* **Desogus A.A. Paolo**
* **Achir Abd El Basset**
* **Ponzin Alex**

*Sviluppato con licenza Open Source Apache 2.0 — Settembre 2026.*
