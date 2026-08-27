"""
Pré-filtre règles/regex (~0 ms) — roadmap §4 [1]
Court-circuite le dispatcheur pour les motifs évidents.
"""
import re

RULES = [
    # Heure/date → fallback (aucun intent dédié ; le LLM + outil MCP répond)
    (r"\b(heure|quel jour|quelle date|on est le|quelle heure)\b", "fallback", "time_date"),
    # Météo → get_weather forcé (l'intent existe, le modèle se trompe)
    (r"\b(météo|temps fait-il|pleut|neige|température)\b", "get_weather", "weather"),
    # Minuteur/timer → fallback (aucun intent dédié)
    (r"\b(minuteur|timer|compte à rebours|alarme dans)\b", "fallback", "timer"),
]

def prefilter(text):
    """Retourne (intent_forcé, raison) si une règle matche, sinon (None, None)."""
    t = text.lower()
    for pattern, intent, reason in RULES:
        if re.search(pattern, t):
            return intent, reason
    return None, None
