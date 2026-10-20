"""
Modulo Gestore Prontuario Frasi Personalizzabile AAC (Clinical Phrasebook Manager).
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Fornire a caregiver, logopedisti e pazienti una libreria gerarchica di comunicazione aumentativa
rapida, strutturata in categorie cliniche e salvata in formato JSON persistente.

Funzionalità Principali:
1. Categorie cliniche predefinite (Bisogni Primari, Salute & Assistenza, Comunicazione, Postura & Comfort).
2. Aggiunta, modifica, cancellazione e riordinamento di frasi personalizzate a runtime.
3. Serializzazione atomica su disco in 'config/phrasebook.json'.
4. Esportazione e importazione per condivisione tra postazioni cliniche e domiciliari.
5. Ricerca istantanea su tutte le categorie.
"""

import json
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Tuple

DEFAULT_PHRASEBOOK: Dict[str, List[str]] = {
    "BISOGNI_PRIMARI": [
        "HO SETE",
        "HO FAME",
        "HO FREDDO",
        "HO CALDO",
        "HO DOLORE",
        "AIUTO",
        "BAGNO SUBITO",
    ],
    "SALUTE_ASSISTENZA": [
        "CHIAMA IL DOTTORE",
        "CHIAMA L'INFERMIERE",
        "HO BISOGNO DELLA MEDICINA",
        "SERVE L'ASPIRATORE",
        "METTI IL COLLIRIO",
        "PULISCI GLI OCCHIALI",
    ],
    "COMUNICAZIONE_SOCIALE": [
        "SÌ",
        "NO",
        "GRAZIE MILLE",
        "PER FAVORE",
        "COME STAI?",
        "TI VOGLIO BENE",
        "ARRIVEDERCI",
    ],
    "POSTURA_COMFORT": [
        "SPOSTAMI IL CUSCINO",
        "RUOTAMI A DESTRA",
        "RUOTAMI A SINISTRA",
        "ALZA LO SCHIENALE",
        "ABBASSA LO SCHIENALE",
        "GRATTAMI IL COLLO",
    ],
}


class PhrasebookManager:
    """Gestore del prontuario frasi cliniche e personalizzate AAC."""

    def __init__(self, config_path: str = "config/phrasebook.json"):
        self.config_path = config_path
        self.categories: Dict[str, List[str]] = {}
        self.load()

    def load(self, path: Optional[str] = None):
        """Carica il prontuario da file JSON, o inizializza con i default clinici."""
        target_path = path or self.config_path
        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.categories = {k: list(v) for k, v in data.items() if isinstance(v, list)}
                        return
            except Exception:
                pass

        # Fallback su prontuario clinico predefinito
        self.categories = {k: list(v) for k, v in DEFAULT_PHRASEBOOK.items()}
        self.save()

    def save(self, path: Optional[str] = None):
        """Salva atomicamente il prontuario su file JSON."""
        target_path = path or self.config_path
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

        dir_name = os.path.dirname(os.path.abspath(target_path))
        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            json.dump(self.categories, tf, indent=2, ensure_ascii=False)
            temp_name = tf.name

        shutil.move(temp_name, target_path)

    def get_categories(self) -> List[str]:
        """Restituisce l'elenco delle categorie disponibili."""
        return list(self.categories.keys())

    def get_phrases(self, category: str) -> List[str]:
        """Restituisce le frasi appartenenti a una categoria."""
        return list(self.categories.get(category, []))

    def add_category(self, category: str) -> bool:
        """Crea una nuova categoria."""
        cat_clean = category.strip().upper()
        if not cat_clean or cat_clean in self.categories:
            return False
        self.categories[cat_clean] = []
        self.save()
        return True

    def remove_category(self, category: str) -> bool:
        """Rimuove una categoria e tutte le sue frasi."""
        if category in self.categories:
            del self.categories[category]
            self.save()
            return True
        return False

    def add_phrase(self, category: str, phrase: str) -> bool:
        """Aggiunge una nuova frase alla categoria specificata."""
        p_clean = phrase.strip().upper()
        if not p_clean:
            return False
        if category not in self.categories:
            self.categories[category] = []
        if p_clean not in self.categories[category]:
            self.categories[category].append(p_clean)
            self.save()
            return True
        return False

    def remove_phrase(self, category: str, phrase: str) -> bool:
        """Rimuove una frase dalla categoria."""
        p_clean = phrase.strip().upper()
        if category in self.categories and p_clean in self.categories[category]:
            self.categories[category].remove(p_clean)
            self.save()
            return True
        return False

    def search_phrases(self, query: str) -> List[Tuple[str, str]]:
        """Cerca frasi in tutte le categorie che contengono la stringa di query."""
        q_clean = query.strip().upper()
        if not q_clean:
            return []
        matches = []
        for cat, phrases in self.categories.items():
            for p in phrases:
                if q_clean in p:
                    matches.append((cat, p))
        return matches

    def export_to_json(self, export_path: str):
        """Esporta il prontuario corrente su un file JSON esterno."""
        self.save(export_path)

    def import_from_json(self, import_path: str) -> bool:
        """Importa un prontuario da un file esterno unendolo o sovrascrivendolo."""
        if not os.path.exists(import_path):
            return False
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            if k not in self.categories:
                                self.categories[k] = []
                            for p in v:
                                if p not in self.categories[k]:
                                    self.categories[k].append(str(p).upper())
                    self.save()
                    return True
        except Exception:
            return False
        return False
