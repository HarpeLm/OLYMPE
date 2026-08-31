"""Dispatcheur NLU léger — Palier 4 (v5).
v5 : corrige 3 bugs (nom de pièce trop court, chiffres sans %, fausses détections)."""
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
              "salon", "fabian", "amis", "boubou", "g\u00e9")

SYNONYM_STRIP = [r"\bvitr[eé]e\b"]

# Nombres en lettres -> chiffres (français, 0-100)
WORD_TO_NUM = {
    "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
    "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
    "quinze": 15, "seize": 16, "dix-sept": 17, "dix-huit": 18,
    "dix-neuf": 19, "vingt": 20, "trente": 30, "quarante": 40,
    "cinquante": 50, "soixante": 60, "soixante-dix": 70,
    "septante": 70, "quatre-vingts": 80, "quatre-vingt": 80,
    "huitante": 80, "quatre-vingt-dix": 90, "nonante": 90,
    "cent": 100,
    "moitie": 50, "moiti\u00e9": 50,
}


def _clean_name(name: str) -> str:
    name = name.lower()
    for pat in SYNONYM_STRIP:
        name = re.sub(pat, "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()


def _parse_percent(t: str):
    """Détecte un pourcentage : exige % ou 'pour cent' (pas juste un chiffre)."""
    # Nombres en lettres + "pour cent" / "pourcent" / "%"
    m = re.search(r"\b([a-z\u00e9\u00e8\u00ea\u00e0\u00fb\u00f9-]+)\s*(?:pour\s*cent|pourcent|%)\b", t)
    if m:
        word = m.group(1).lower()
        if "-" in word:
            parts = word.split("-")
            total = 0
            for p in parts:
                if p in WORD_TO_NUM:
                    total += WORD_TO_NUM[p]
            if total:
                return total, m.group(0)
        elif word in WORD_TO_NUM:
            return WORD_TO_NUM[word], m.group(0)

    # Expression "à moitié"
    if re.search(r"\b\u00e0 moiti\u00e9\b|\bpartiellement\b|"
                 r"\bentre[- ]ouvert[s]?\b|\bmi[- ]partie\b", t):
        return 50, ""

    # Chiffres arabes — exige % (pas juste un chiffre seul)
    m = re.search(r"\b(\d{1,3})\s*%", t)
    if m:
        return int(m.group(1)), m.group(0)

    return None, None


def _extract_room(text_after_action: str) -> Optional[str]:
    """Extrait un nom de pièce complet (incluant le nom propre/numéro)."""
    # Mots qui terminent l'extraction
    stop_words = {"pour", "cent", "pourcent", "%",
                  "degr\u00e9", "degre", "environ", "\u00e0"}
    stop_words.update(WORD_TO_NUM.keys())
    # Articles à ignorer
    articles = {"de", "du", "des", "le", "la", "l", "les", "et"}

    for w in ROOM_WORDS:
        idx = text_after_action.find(w)
        if idx >= 0:
            chunk = text_after_action[idx:]
            parts = chunk.split()
            name_parts = []
            for p in parts:
                clean = re.sub(r"[^a-z\u00e9\u00e8\u00ea\u00e0\u00fb\u00f90-9-]", "", p.lower())
                if not clean:
                    continue
                if clean in stop_words:
                    break
                if clean in articles:
                    continue  # sauter tous les connecteurs (de, la, et...)
                if len(name_parts) < 4:
                    name_parts.append(p)
            if name_parts:
                return _clean_name(" ".join(name_parts))
    return None


def _has_shutter_context(t: str) -> bool:
    """Vérifie que la phrase parle bien de volets (mot-clé ou pièce connue)."""
    if "volet" in t:
        return True
    return any(w in t for w in ROOM_WORDS)


def dispatch(text: str) -> Optional[DispatchResult]:
    t = text.lower().strip()

    # Garde-fou : la phrase doit parler de volets
    if not _has_shutter_context(t):
        return None

    m_action = re.search(r"\b(ouvre|ouvrir|ferme|fermer|mets|mettre|baisse|monte)\b", t)
    if not m_action:
        return None
    action_word = m_action.group(1)

    rest = t[m_action.end():]

    # Position (pourcentage) ?
    percent, _ = _parse_percent(t)

    # Extraire la pièce
    room = _extract_room(rest)

    if percent is not None and room:
        return DispatchResult("shutters.set_position",
                              {"name": room, "percent": percent}, 1.0)

    if percent is not None and not room:
        return DispatchResult("shutters.set_position",
                              {"percent": percent}, 1.0)

    if room:
        action = "open" if action_word in ("ouvre", "ouvrir", "monte") else "close"
        return DispatchResult(f"shutters.{action}",
                              {"name": room}, 1.0)

    if action_word in ("ouvre", "ouvrir", "monte"):
        return DispatchResult("shutters.open_all", {}, 1.0)
    return DispatchResult("shutters.close_all", {}, 1.0)


if __name__ == "__main__":
    test_cases = [
        "Ouvre les volets",
        "Ferme tous les volets",
        "Ferme la chambre de fabian",
        "Ferme la baie vitr\u00e9e 2",
        "Ouvre les volets de la chambre de fabian \u00e0 trente pour cent",
        "Mets la cuisine \u00e0 50%",
        "Ouvre \u00e0 moiti\u00e9 les volets du bureau",
        "Ferme la t\u00e9l\u00e9",
        "Quelle est la m\u00e9t\u00e9o ?",
    ]
    for text in test_cases:
        result = dispatch(text)
        if result:
            print(f"\u2705 '{text}' -> {result.to_dict()}")
        else:
            print(f"\u274c '{text}' -> pas d'intent")
