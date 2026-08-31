"""Dispatcheur NLU léger — Palier 4 (v3).
Pré-filtre regex pour les intents évidentes, court-circuite le LLM.
v3 : supporte "à moitié / partiellement / entre-ouvert" et tolère
les synonymes "baie vitrée N" -> "Baie N" (vraie étiquette TaHoma)."""
import re
from typing import Optional


class DispatchResult:
    def __init__(self, intent: str, slots: dict, confidence: float):
        self.intent = intent
        self.slots = slots
        self.confidence = confidence

    def to_dict(self):
        return {"intent": self.intent, "slots": self.slots,
                "confidence": self.confidence}


ROOM_WORDS = ("chambre", "cuisine", "bureau", "baie", "panoramique",
              "salon", "fabian", "amis", "boubou")

# Synonymes à nettoyer dans le nom extrait ("baie vitrée 2" -> "baie 2")
SYNONYM_STRIP = [r"\bvitr[eé]e\b"]

# Expressions -> pourcentage
HALF_EXPRS = [r"\bà moitié\b", r"\bpartiellement\b",
              r"\bentre[- ]ouvert[s]?\b", r"\bmi[- ]partie\b"]


def _clean_name(name: str) -> str:
    name = name.lower()
    for pat in SYNONYM_STRIP:
        name = re.sub(pat, "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()


def _detect_percent(t: str) -> Optional[int]:
    """Détecte un pourcentage explicite OU 'à moitié'."""
    for pat in HALF_EXPRS:
        if re.search(pat, t):
            return 50
    m = re.search(r"\b(\d{1,3})\s*%", t)
    if m:
        return int(m.group(1))
    return None


def dispatch(text: str) -> Optional[DispatchResult]:
    t = text.lower().strip()
    is_shutter = "volet" in t or any(w in t for w in ROOM_WORDS)

    if not is_shutter:
        return None

    # 0) Action (ouvre/ferme) + position ?
    m_action = re.search(r"\b(ouvre|ouvrir|ferme|fermer|mets|mettre|baisse|monte)\b", t)
    if not m_action:
        return None
    action_word = m_action.group(1)

    # 1) Position (pourcentage ou "à moitié")
    percent = _detect_percent(t)

    if percent is not None:
        # On cherche un nom de pièce
        rest = t[m_action.end():]
        rest = re.sub(r"\b(le|la|l'|les|de|du|des)\b", " ", rest)
        rest = re.sub(r"\bvolets?\b", " ", rest)
        rest = re.sub(r"\b(à|au|à\s+)?moitié\b|\bpartiellement\b|"
                      r"\bentre[- ]ouvert[s]?\b|\bmi[- ]partie\b", " ", rest)
        rest = re.sub(r"\b\d{1,3}\s*%?\b", " ", rest)
        name = _clean_name(" ".join(rest.split()))
        if not name:
            # "mets les volets à 50%" sans nom -> tous les volets
            return DispatchResult("shutters.set_position",
                                  {"percent": percent}, 1.0)
        # Un volet + position -> set_shutter_position (nouvelle action)
        return DispatchResult("shutters.set_position",
                              {"name": name, "percent": percent}, 1.0)

    # 2) Nom de pièce présent -> volet spécifique
    room_name = None
    for w in ROOM_WORDS:
        if w in t:
            # Extraire autour du mot-clé
            idx = t.find(w)
            chunk = t[idx:idx+40]
            # Prendre le mot + éventuel numéro ou qualificatif
            m = re.match(r"([a-zéèêàûù]+(?:\s+[a-zéèêàûù0-9]+)*)", chunk)
            if m:
                room_name = _clean_name(m.group(1))
                break

    if room_name:
        action = "open" if action_word in ("ouvre", "ouvrir", "monte") else "close"
        return DispatchResult(f"shutters.{action}",
                              {"name": room_name}, 1.0)

    # 3) Pas de nom de pièce -> tous les volets
    if action_word in ("ouvre", "ouvrir", "monte"):
        return DispatchResult("shutters.open_all", {}, 1.0)
    return DispatchResult("shutters.close_all", {}, 1.0)


if __name__ == "__main__":
    test_cases = [
        "Ouvre les volets",
        "Ferme tous les volets",
        "Ouvre le volet de la cuisine",
        "Ferme la chambre de fabian",
        "Ferme baie 1",
        "Ferme la baie vitrée 2",
        "Ouvre à moitié les volets du bureau",
        "Mets les volets à 50%",
        "Baisse les volets à 30%",
        "Quelle est la météo ?",
        "Ferme la télé",
    ]
    for text in test_cases:
        result = dispatch(text)
        if result:
            print(f"✅ '{text}' -> {result.to_dict()}")
        else:
            print(f"❌ '{text}' -> pas d'intent")
