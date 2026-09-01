"""Orchestrateur — Palier 4.
Décide quoi faire d'une requête après le dispatch :
  - Intent TaHoma reconnue -> exécuter directement (pas de LLM)
  - Sinon -> fallback vers LLM

v2 : mode dry_run pour les tests (n'actionne JAMAIS les volets),
et gestion propre des noms de volet inconnus (ValueError)."""
import json
import sys
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router.nlu import Dispatcher
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


ROOT = Path(__file__).resolve().parents[1]
_ROUTER = Dispatcher()


def _llm_endpoint():
    cfg = yaml.safe_load(
        (ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    srv = cfg.get("server", {})
    url = f"http://{srv.get('host', '127.0.0.1')}:{srv.get('port', 8000)}"
    return url + "/v1/chat/completions", cfg["roles"]["chat"]["repo"]


def grounded_web_answer(question):
    """web_search + résumé ancré sur les résultats (jamais de mémoire)."""
    from agent.tools import run_tool
    raw = run_tool("web_search", {"query": question})
    url, model = _llm_endpoint()
    payload = {"model": model, "max_tokens": 256, "messages": [
        {"role": "system",
         "content": "Réponds en une phrase orale en français, uniquement "
                    "d'après les résultats fournis. Si ils ne permettent "
                    "pas de répondre, dis-le simplement."},
        {"role": "user",
         "content": f"Question : {question}\nRésultats :\n{raw} /no_think"}]}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"].get("content") or "Je n'ai pas trouvé."


def orchestrate(text: str, dry_run: bool = False) -> dict:
    """Point d'entrée : routage nlu + exécution ou fallback."""
    r = _ROUTER.route(text)
    intent, action = r["intent"], r["action"]

    if action == "deterministic" and r["confidence"] >= 0.9:
        if intent == "web_search":
            return {"handled": True, "intent": intent,
                    "result": {"success": True,
                               "message": grounded_web_answer(text)},
                    "fallback": False}
        if intent.startswith("shutters."):
            result = execute_tahoma_action(intent, r["slots"],
                                           dry_run=dry_run)
            return {"handled": True, "intent": intent,
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
