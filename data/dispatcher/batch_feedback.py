"""
Test batch du dispatcheur avec feedback manuel.

Pour chaque phrase : affiche le routage (intent, confiance, action),
demande oui/non dans le terminal, logue tout dans inference_log.jsonl
avec le champ user_feedback (source: batch_feedback).

Usage :
    python data/dispatcher/batch_feedback.py              # liste par défaut
    python data/dispatcher/batch_feedback.py "phrase 1" "phrase 2"   # phrases perso
"""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from router.dispatcher import Dispatcher

LOG_PATH = ROOT / "data" / "dispatcher" / "inference_log.jsonl"

# Liste par défaut : couvre déterministe, fallback, et les 2 échecs connus
DEFAULT_PHRASES = [
    "quelle heure est-il",
    "on est quel jour aujourd'hui",
    "quel temps fait-il à Paris",
    "mets un minuteur de 10 minutes",
    "lance ma playlist détente",
    "pause la musique",
    "qu'est-ce qui suit dans mon planning",
    "mes documents récents",
    "allume le bluetooth",
    "fais une capture d'écran",
    "ouvre le dossier téléchargements",
    "explique-moi comment fonctionne un trou noir",
    "raconte-moi une blague",
    "qui était Ada Lovelace",
    "combien d'étapes a gagné Tadej Pogačar sur le Tour de France",
]


def main():
    phrases = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_PHRASES

    print("Chargement du dispatcheur...")
    dispatcher = Dispatcher()
    print("Dispatcheur prêt.\n")

    stats = {"positive": 0, "negative": 0, "unclear": 0}

    for i, phrase in enumerate(phrases, 1):
        print(f"[{i}/{len(phrases)}] « {phrase} »")
        result = dispatcher.route(phrase)
        print(
            f"    intent={result.get('intent')} | "
            f"confiance={result.get('confidence')} | "
            f"action={result.get('action')}"
        )

        answer = input("    Correct ? (o / n / s pour passer) : ").strip().lower()

        if answer in ("o", "oui", "y"):
            feedback = "positive"
        elif answer in ("n", "non"):
            feedback = "negative"
        else:
            feedback = "unclear"
        stats[feedback] += 1

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "text": phrase,
            "intent": result.get("intent"),
            "slots": result.get("slots"),
            "confidence": result.get("confidence"),
            "action": result.get("action"),
            "source": "batch_feedback",
            "user_feedback": feedback,
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        print()

    total = stats["positive"] + stats["negative"]
    print("=" * 60)
    if total:
        print(
            f"Précision : {stats['positive']}/{total} "
            f"= {stats['positive'] / total * 100:.0f}%"
        )
    print(f"Ignorées : {stats['unclear']}")
    print(f"Log : {LOG_PATH}")
    print("Ensuite : python data/dispatcher/analyze_feedback.py")


if __name__ == "__main__":
    main()
