"""Orchestrateur — Palier 4.
Décide quoi faire d'une requête après le dispatch :
  - Intent TaHoma reconnue -> exécuter directement (pas de LLM)
  - Sinon -> fallback vers LLM

v2 : mode dry_run pour les tests (n'actionne JAMAIS les volets),
et gestion propre des noms de volet inconnus (ValueError)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.dispatcher import dispatch
from integrations.tahoma import (
    list_shutters,
    open_shutter,
    close_shutter,
    set_shutter_position,
)


def execute_tahoma_action(intent: str, slots: dict, dry_run: bool = False) -> dict:
    """Exécute une action TaHoma déterministe (pas de LLM)."""
    if dry_run:
        return {"success": True, "message": f"[dry-run] {intent} {slots}"}
    try:
        if intent == "shutters.open_all":
            shutters = list_shutters()
            for s in shutters:
                open_shutter(s["name"])
            return {"success": True, "message": f"{len(shutters)} volets ouverts"}
        elif intent == "shutters.close_all":
            shutters = list_shutters()
            for s in shutters:
                close_shutter(s["name"])
            return {"success": True, "message": f"{len(shutters)} volets fermés"}
        elif intent == "shutters.open":
            return open_shutter(slots.get("name", ""))
        elif intent == "shutters.close":
            return close_shutter(slots.get("name", ""))
        elif intent == "shutters.set_position":
            percent = slots.get("percent")
            if percent is None:
                return {"success": False, "message": "Pourcentage manquant"}
            name = slots.get("name")
            if name:
                return set_shutter_position(name, percent)
            shutters = list_shutters()
            for s in shutters:
                set_shutter_position(s["name"], percent)
            return {"success": True,
                    "message": f"{len(shutters)} volets à {percent}%"}
        return {"success": False, "message": f"Intent inconnue : {intent}"}
    except ValueError as e:
        return {"success": False, "message": str(e)}


def orchestrate(text: str, dry_run: bool = False) -> dict:
    """Point d'entrée : dispatch + exécution ou fallback."""
    dispatch_result = dispatch(text)

    if dispatch_result and dispatch_result.confidence >= 0.9:
        result = execute_tahoma_action(dispatch_result.intent,
                                       dispatch_result.slots,
                                       dry_run=dry_run)
        return {"handled": True, "intent": dispatch_result.intent,
                "result": result, "fallback": False}

    return {"handled": False, "intent": None, "result": None,
            "fallback": True}


if __name__ == "__main__":
    test_phrases = [
        "Ouvre les volets",
        "Ferme la chambre de fabian",
        "Ferme la télé",
        "Quelle est la météo ?",
    ]
    for phrase in test_phrases:
        print(f"\nPhrase : '{phrase}'")
        result = orchestrate(phrase, dry_run=True)
        print(f"  Handled: {result['handled']} | Intent: {result['intent']}")
        print(f"  Result: {result['result']} | Fallback: {result['fallback']}")
