# 🛡️ ANALISI DEI RISCHI E FMEA (ISO 14971:2019)
### Failure Mode and Effects Analysis — SteadyMotion AI Software as a Medical Device (SaMD)

**Scala di Valutazione:**
* **Gravità (G):** 1 (Trascurabile) | 2 (Lieve disagio) | 3 (Interruzione attività) | 4 (Danno temporaneo/affaticamento) | 5 (Danno grave)
* **Probabilità (P):** 1 (Improbabile) | 2 (Rara) | 3 (Occasionale) | 4 (Frequente) | 5 (Molto frequente)
* **Rilevabilità (R):** 1 (Rilevazione automatica garantita) | 2 (Alta) | 3 (Moderata) | 4 (Bassa) | 5 (Non rilevabile)
* **Indice di Rischio (RPN):** $RPN = G \times P \times R$ (Accettabile se $RPN < 30$).

---

## TABELLA FMEA DEI RISCHI CLINICI & MISURE DI MITIGAZIONE

| ID Rischio | Modalità di Guasto (Failure Mode) | Causa Potenziale | Effetto Clinico sul Paziente | G | P | R | RPN Iniziale | Misura di Mitigazione Software / Hardware Implementata | G' | P' | R' | RPN Finale |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **R-01** | **Clic Accidentale "al Volo"** | Attraversamento rapido di icone desktop durante il movimento del capo | Clic involontario su cartelle o collegamenti indesiderati | 3 | 4 | 3 | **36** (Non Accettabile) | **Anti-Sweep Velocity Gate (`core/dwell_clicker.py`):** Il progresso dwell viene bloccato categoricamente a 0 se la velocità supera i 240 px/s. | 2 | 1 | 1 | **2** (Basso) |
| **R-02** | **Blocco del Clic su Spasmo Involontario** | Spasmo mioclonico o scatto estensorio improvviso da distonia | Azzeramento improvviso del dwell con frustrazione del paziente | 3 | 4 | 2 | **24** | **Pozzo di Potenziale Soft Grace Zone (1.85x raggio):** Il progresso non si azzera di colpo ma decade in modo morbido proporzionale alla distanza. | 2 | 2 | 1 | **4** (Basso) |
| **R-03** | **Blocco Totale su Schermata UAC di Windows** | Comparsa del prompt di sicurezza amministratore con isolamento UIPI | Paziente impossibilitato a interagire; cursore congelato | 4 | 3 | 4 | **48** (Critico) | **Manifest `uiAccess="true"` & Watchdog di Sistema:** Bypass dell'isolamento UIPI quando installato in cartella sicura e firmato digitalmente. | 2 | 1 | 2 | **4** (Basso) |
| **R-04** | **Perdita Tracciamento per Controluce/Buio** | Variazione della luce della stanza o finestra alle spalle | Blocco del cursore o mancato riconoscimento facciale | 3 | 3 | 3 | **27** | **Compensazione CLAHE e Luma LUT (`core/camera_worker.py`):** Equalizzazione adattiva dei contorni orbitali + Badge acustico/visivo "Luce Bassa". | 2 | 1 | 1 | **2** (Basso) |
| **R-05** | **Sovraffaticamento Muscolare Cervicale** | Puntamento prolungato con testa inclinata in basso (Head-Drop) | Contratture dolorose del collo o caduta cefalica da ipotonia | 4 | 3 | 3 | **36** (Non Accettabile) | **Monitor Ergonomico Closed-Loop (`core/ergonomics.py`):** Assorbimento adattivo bi-assiale del drift posturale lento e alert edge-triggered dopo 5s. | 2 | 1 | 1 | **2** (Basso) |
| **R-06** | **"Lotta del Mouse" (Mouse Fight)** | Intervento simultaneo del caregiver sul mouse fisico USB | Conflitto di coordinate tra SendInput e mouse fisico | 3 | 3 | 2 | **18** | **Caregiver Co-Pilot con Hook Kernel `WH_MOUSE_LL` (`core/copilot.py`):** Pausa di cortesia immediata di 2.0s con precedenza al mouse fisico. | 1 | 1 | 1 | **1** (Trascurabile) |
| **R-07** | **Clic Eseguito durante Riposo / Chiusura Occhi** | Il paziente chiude gli occhi per riposarsi ma il dwell continua | Apertura indesiderata di programmi a occhi chiusi | 3 | 3 | 2 | **18** | **Freno di Emergenza Fisiologico (Blink Clamping / Abort):** La chiusura prolungata degli occhi azzera istantaneamente qualsiasi sosta e sblocca il drag. | 1 | 1 | 1 | **1** (Trascurabile) |
| **R-08** | **Falsi Clic Vocali da Rumore Ambientale** | Televisione accesa, voci di familiari, ronzio condizionatore | Clic spuri non intenzionali su trigger microfono | 3 | 3 | 3 | **27** | **Filtro Zero-Crossing Rate (ZCR > 0.08) & Auto-Calibrazione (`core/acoustic_trigger.py`):** Soppressione rumore continuo e immunità a 50/60 Hz. | 2 | 1 | 1 | **2** (Basso) |

---

## CONCLUSIONE DELLA VALUTAZIONE DEL RISCHIO
A seguito dell'introduzione delle misure di mitigazione software e hardware, **tutti gli indici di rischio residuo (RPN Finale) risultano ampiamente inferiori alla soglia critica di 30 (range reale tra 1 e 4)**. Il profilo di rischio complessivo di SteadyMotion AI è giudicato **accettabile e conforme ai requisiti dell'Allegato I del Regolamento (UE) MDR 2017/745**.
