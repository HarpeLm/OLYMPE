"""
Prompts partages du dispatcheur NLU.
Le prompt systeme liste chaque intent avec son schema de slots
(! = obligatoire, ? = optionnel), lus depuis la taxonomie.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
INTENTS_PATH = ROOT / "router" / "intents.yaml"


def load_taxonomy():
    with open(INTENTS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_intent_names():
    taxo = load_taxonomy()
    names = [i["name"] for i in taxo.get("deterministic_intents", [])]
    names += [i["name"] for i in taxo.get("generative_fallbacks", [])]
    return names


def build_system_prompt():
    taxo = load_taxonomy()
    signatures = []
    for i in taxo.get("deterministic_intents", []):
        slots = i.get("slots") or []
        if slots:
            schema = ", ".join(
                s["name"] + ("!" if s.get("required") else "?") for s in slots
            )
            signatures.append(f'{i["name"]}({schema})')
        else:
            signatures.append(i["name"])
    signatures.append("general_question")

    return (
        "Tu es le dispatcheur NLU d'MJ, un assistant vocal local. "
        "Analyse la requete et reponds UNIQUEMENT avec un objet JSON valide, "
        "sans aucun texte autour, au format : "
        '{"intent": "<nom>", "slots": {"<cle>": "<valeur>"}}. '
        "Intents valides avec leurs slots (! = obligatoire, ? = optionnel) : "
        + "; ".join(signatures)
        + ". Utilise EXACTEMENT ces noms d'intents et de slots. "
        'Utilise "general_question" avec slots vides si aucun intent '
        "deterministe ne correspond."
    )


def format_assistant_answer(intent, slots):
    return json.dumps(
        {"intent": intent, "slots": slots or {}},
        ensure_ascii=False,
        sort_keys=True,
    )
