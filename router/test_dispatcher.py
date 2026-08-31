"""Testeur interactif du dispatcheur — 100 % dry-run, rien ne bouge.
Tape une phrase, il affiche l'intent comprise et l'action simulée.
'q' ou ligne vide pour quitter."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.orchestrator import orchestrate

print("=== Testeur dispatcheur (dry-run : aucune action réelle) ===")
print("Tape une phrase, Entrée pour analyser. 'q' pour quitter.\n")

while True:
    try:
        phrase = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye.")
        break
    if not phrase or phrase.lower() == "q":
        print("Bye.")
        break
    result = orchestrate(phrase, dry_run=True)
    if result["handled"]:
        print(f"   intent : {result['intent']}")
        print(f"   action : {result['result']['message']}")
    else:
        print("   -> pas d'intent : fallback vers le LLM (8B)")
    print()
