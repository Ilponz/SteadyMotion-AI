"""
Strumento di Generazione Chiavi di Licenza SteadyMotion AI Pro / SaMD.
Utilizzo:
    python tools/generate_license.py --machine SM-C531-405A
    python tools/generate_license.py --universal
    python tools/generate_license.py --tier CLINICAL --machine SM-C531-405A
"""

import argparse
import sys
import os

# Aggiunge root al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import generate_license_key, get_system_machine_id


def main():
    parser = argparse.ArgumentParser(description="Generatore Licenze Ufficiali SteadyMotion AI")
    parser.add_argument("--machine", "-m", type=str, default="", help="Machine ID del cliente (es. SM-C531-405A)")
    parser.add_argument("--tier", "-t", type=str, default="PRO", choices=["PRO", "HOME", "CLINICAL"], help="Tier di licenza")
    parser.add_argument("--universal", "-u", action="store_true", help="Genera una licenza Universale (valida su qualsiasi PC)")
    parser.add_argument("--current", "-c", action="store_true", help="Usa il Machine ID di questo computer")

    args = parser.parse_args()

    if args.universal:
        target = "UNIV2026"
        target_desc = "UNIVERSALE (Tutti i PC / Multi-Postazione)"
    elif args.current:
        target = get_system_machine_id()
        target_desc = f"Macchina Locale ({target})"
    elif args.machine:
        target = args.machine.strip().upper()
        target_desc = f"Macchina Cliente ({target})"
    else:
        current_id = get_system_machine_id()
        print("\n=======================================================")
        print("  Generatore Licenze Ufficiali SteadyMotion AI         ")
        print("=======================================================")
        print(f"Machine ID di questo computer: {current_id}")
        print("\nNessun parametro specificato. Esempi di utilizzo:")
        print(f"  python tools/generate_license.py --machine {current_id}")
        print("  python tools/generate_license.py --universal")
        print("=======================================================\n")
        return

    key = generate_license_key(target_id=target, tier=args.tier)

    print("\n" + "=" * 62)
    print(f"  STEADYMOTION AI - CHIAVE DI LICENZA GENERATA ({args.tier})")
    print("=" * 62)
    print(f"Destinazione:   {target_desc}")
    print(f"Tier Licenza:   {args.tier}")
    print(f"CHIAVE SERIALE: {key}")
    print("=" * 62)
    print("\nInviare questa stringa al cliente per sbloccare la versione Pro.\n")


if __name__ == "__main__":
    main()
