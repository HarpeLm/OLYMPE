"""
Filtre MASSIVE pour ne garder que les exemples de haute qualité.
Exclut : phrases mal traduites, conflits de taxonomie, patterns anglais.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Patterns à exclure (phrases mal traduites ou non naturelles)
EXCLUDE_PATTERNS = [
    "c. n. n.",
    "pawel",
    "brexit",
    "virginie",
    "californie",
    "jour du souvenir",
    "dites-moi des nouvellesdites-moi",
    "je l' aime",
    "je l'aime",
]

# Intents MASSIVE qui créent des conflits de taxonomie
EXCLUDE_INTENTS = [
    "general_question",  # trop de confusion avec get_events_date
    "web_search",        # trop de confusion avec general_question
]

# Nombre max d'exemples par intent après filtrage
MAX_PER_INTENT = 15


def is_valid_example(ex):
    """Vérifie si un exemple MASSIVE est de haute qualité."""
    text = ex["text"].lower()
    
    # Exclure les patterns problématiques
    for pattern in EXCLUDE_PATTERNS:
        if pattern.lower() in text:
            return False
    
    # Exclure les intents conflictuels
    if ex["intent"] in EXCLUDE_INTENTS:
        return False
    
    # Exclure les phrases trop courtes (< 3 mots)
    if len(text.split()) < 3:
        return False
    
    # Exclure les phrases avec des espaces doubles ou des doublons
    if "  " in text or text.count(text[:10]) > 1:
        return False
    
    return True


def filter_massive():
    """Filtre massive_fr.jsonl.bak et sauvegarde massive_fr_filtered.jsonl"""
    input_path = ROOT / "data" / "dispatcher" / "massive_fr.jsonl.bak"
    output_path = ROOT / "data" / "dispatcher" / "massive_fr_filtered.jsonl"
    
    if not input_path.exists():
        print(f"Erreur : {input_path} introuvable")
        return
    
    examples = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            ex = json.loads(line.strip())
            if is_valid_example(ex):
                examples.append(ex)
    
    # Limiter par intent
    intent_counts = {}
    filtered = []
    for ex in examples:
        intent = ex["intent"]
        if intent_counts.get(intent, 0) >= MAX_PER_INTENT:
            continue
        filtered.append(ex)
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    
    # Sauvegarde
    with open(output_path, 'w', encoding='utf-8') as f:
        for ex in filtered:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    # Rapport
    print(f"Filtrage MASSIVE terminé")
    print(f"Avant : 233 exemples")
    print(f"Après : {len(filtered)} exemples")
    print(f"\nRépartition par intent :")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"  {intent:25s} : {count}")


if __name__ == "__main__":
    filter_massive()
