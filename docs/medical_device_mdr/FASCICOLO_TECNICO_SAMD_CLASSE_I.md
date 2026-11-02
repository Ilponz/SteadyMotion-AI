# 🏥 FASCICOLO TECNICO DEL DISPOSITIVO MEDICO
### Ai sensi del Regolamento (UE) 2017/745 (MDR) — Allegati II e III
**Prodotto:** SteadyMotion AI (Versione Clinical Release 3.0 / Pro)  
**Tipologia:** Software as a Medical Device (SaMD)  
**Classificazione di Rischio:** Dispositivo Medico di Classe I (Non sterile, non di misura)  

---

## 1. DESCRIZIONE GENERALE E DESTINAZIONE D'USO

### 1.1 Denominazione e Codifica
* **Nome Commerciale:** SteadyMotion AI — Assistive Pointer & AAC Suite
* **Codice CND (Classificazione Nazionale Dispositivi Medici):** `Y2109` (Ausili per l'integrazione delle funzioni informatiche e di comunicazione)
* **GMDN Code:** `43075` (Computer-access communication device software, disability)

### 1.2 Destinazione d'Uso Clinica
SteadyMotion AI è un software assistivo e compensativo destinato a persone affette da gravi limitazioni o perdita totale della mobilità degli arti superiori derivante da patologie neurodegenerative o traumi neurologici:
* Sclerosi Laterale Amiotrofica (SLA - stadi iniziale, intermedio e avanzato);
* Tetraparesi spastica o flaccida da trauma vertebro-midollare cervicale;
* Morbo di Parkinson severo e tremore essenziale invalidante;
* Distonia cervicale e ipertono spastico.

Il software converte il flusso video di una comune webcam commerciale in coordinate di puntamento ed eventi di clic, consentendo al paziente il controllo autonomo del personal computer, la comunicazione aumentativa alternativa (CAA) e la verbalizzazione vocale dei bisogni primari.

### 1.3 Controindicazioni e Limiti d'Uso
* Pazienti con perdita totale del controllo motorio cefalico e oculare (stato di *locked-in* totale: in questo stadio è indicato un BCI elettroencefalografico);
* Ambienti completamente privi di illuminazione senza add-on a infrarossi;
* Pazienti con fotosensibilità epilettica severa (l'HUD overlay è privo di frequenze di lampeggio critiche tra 3 e 30 Hz).

---

## 2. INQUADRAMENTO NORMATIVO E REGOLA DI CLASSIFICAZIONE

Ai sensi dell'**Allegato VIII, Regola 11 del Regolamento (UE) 2017/745 (MDR)**:
* *Regola 11:* Il software destinato a fornire informazioni utilizzate per prendere decisioni con finalità diagnostiche o terapeutiche è classificato nella classe IIa o superiore.
* **Deroga Applicabile:** SteadyMotion AI **non fornisce diagnosi né somministra terapie farmacologiche o fisiche**. La sua funzione primaria è **compensativa e abilitativa della funzione comunicativa e informatica**.
* Di conseguenza, il software ricade nella:
  $$\mathbf{CLASSE\ I\ (Regola\ 11\ -\ Software\ di\ Ausilio\ e\ Compensazione)}$$
* **Procedura di Valutazione della Conformità:**
  Ai sensi dell'**Articolo 52, comma 7 del Regolamento MDR**, per i dispositivi di Classe I non sterili e non dotati di funzione di misura, il Fabbricante **dichiara la conformità dei suoi prodotti rilasciando la dichiarazione di conformità UE (Marcatura CE in Autocertificazione)** dopo aver redatto e archiviato il Fascicolo Tecnico.

---

## 3. NORME ARMONIZZATE E STANDARD DI RIFERIMENTO

| Norma Tecnica | Titolo / Ambito | Stato di Applicazione in SteadyMotion AI |
| :--- | :--- | :--- |
| **EN ISO 13485:2016** | Dispositivi medici — Sistemi di gestione per la qualità | Implementato nel ciclo di commit tracciato su Git con revisioni di codice. |
| **EN ISO 14971:2019** | Applicazione della gestione dei rischi ai dispositivi medici | FMEA completa dei rischi software/hardware (vedasi `FMEA_RISK_ANALYSIS_ISO14971.md`). |
| **CEI EN 62304:2006/A1:2015** | Software per dispositivi medici — Processi del ciclo di vita | Classe di sicurezza software A (test unitari 35/35, tracciabilità SRS). |
| **CEI EN 62366-1:2015** | Applicazione dell'ingegneria dell'usabilità ai dispositivi medici | Setup Wizard in 4 fasi, standard ergonomico Tobii e radar posturale. |
| **ISO 9241-9 / ISO 9241-411** | Ergonomia dell'interazione uomo-sistema — Valutazione dispositivi di puntamento | Modulo FittsEvaluator integrato con calcolo del Throughput $TP_e$ e ampiezza $W_e$. |

---

## 4. ARCHITETTURA TECNICA E MISURE DI RIDUZIONE DEL RISCHIO

1. **Modulo Anti-Sweep Velocity Gate:** Impedisce clic accidentali mentre il paziente sposta lo sguardo velocemente da una parte all'altra del monitor ($v > 240\text{ px/s}$).
2. **Modulo Freno di Emergenza Fisiologico (Blink Abort):** Se il paziente chiude gli occhi per riposare o per emergenza ($t > 1.5\text{ s}$), qualsiasi operazione in corso (Dwell o Drag & Drop) viene abortita istantaneamente.
3. **Modulo Caregiver Co-Pilot:** Consente all'operatore di prendere il controllo fisico immediato tramite il mouse USB, senza conflitti di puntamento.
4. **Modulo Ergonomico Cervicale:** Monitora la flessione prolungata del capo (Head-Drop $> 12^\circ$), prevenendo contratture cervicali e suggerendo pause o ricentratura comoda (F12).

---

## 5. PIANO DI POST-MARKET SURVEILLANCE (PMS)
Il software integra il modulo locale `core/clinical_logger.py` che genera report anonimi sulle prestazioni (Throughput ISO 9241-9, tasso KSR, spasmi intercettati). Tali dati possono essere consultati dal personale sanitario per verificare l'evoluzione della destrezza motoria nel tempo e monitorare eventuali anomalie operative.
