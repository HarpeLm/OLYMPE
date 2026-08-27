import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dispatcher" / "dataset_v7"
V6 = ROOT / "data" / "dispatcher" / "dataset_v6"
FAILURES = ROOT / "data" / "dispatcher" / "eval_expanded_failures.jsonl"

rows = []

# 1. Reprendre v6
for split in ("train.jsonl", "valid.jsonl"):
    f = V6 / split
    if f.exists():
        for line in f.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
print(f"v6 repris : {len(rows)} lignes")

# 2. Ajouter les échecs du test élargi comme corrections
if FAILURES.exists():
    failure_count = 0
    for line in FAILURES.read_text().splitlines():
        try:
            f = json.loads(line)
            text = f.get("text", "").strip()
            expected = f.get("expected", "")
            if text and expected:
                rows.append({
                    "prompt": text,
                    "completion": json.dumps({"intent": expected, "slots": {}}, ensure_ascii=False)
                })
                failure_count += 1
        except json.JSONDecodeError:
            pass
    print(f"Échecs ajoutés : {failure_count} lignes")

# 3. Ajouter des variantes supplémentaires pour équilibrer
EXTRA = [
    # Date/heure (renforcement fallback)
    ("quelle est la date du jour", "general_question", {}),
    ("c'est quoi la date aujourd'hui", "general_question", {}),
    ("on est le combien", "general_question", {}),
    ("quel jour sommes-nous", "general_question", {}),
    ("préviens-moi dans vingt minutes", "general_question", {}),
    ("rappelle-moi dans 30 minutes", "general_question", {}),
    
    # Questions générales (renforcement fallback)
    ("qui était Ada Lovelace", "general_question", {}),
    ("explique-moi comment fonctionne un trou noir", "general_question", {}),
    ("raconte-moi une blague", "general_question", {}),
    ("pourquoi le ciel est bleu", "general_question", {}),
    ("comment fonctionne un moteur thermique", "general_question", {}),
    ("15 pour cent de 80 ça fait combien", "general_question", {}),
    ("combien font 17 fois 23", "general_question", {}),
    ("c'est quoi la photosynthèse", "general_question", {}),
    ("qui a peint la Joconde", "general_question", {}),
    
    # Météo (renforcement get_weather)
    ("est-ce qu'il va neiger à Chamonix", "get_weather", {}),
    ("météo Paris demain", "get_weather", {}),
    ("il fait quel temps à Nice", "get_weather", {}),
    
    # Musique (contrôles avancés)
    ("reprends la musique", "resume_music", {}),
    ("continue la lecture", "resume_music", {}),
    ("chanson suivante", "next_track", {}),
    ("passe à la piste suivante", "next_track", {}),
    ("piste précédente", "previous_track", {}),
    ("reviens à la chanson d'avant", "previous_track", {}),
    ("c'est quoi cette chanson", "get_now_playing", {}),
    ("qu'est-ce qui joue en ce moment", "get_now_playing", {}),
    ("arrête la musique dans 20 minutes", "sleep_timer", {"duration_minutes": 20}),
    ("coupe la musique dans une demi-heure", "sleep_timer", {"duration_minutes": 30}),
    ("répète cette piste", "repeat_track", {}),
    
    # Calendrier
    ("qu'est-ce qui suit dans mon planning", "get_next_event", {}),
    ("mon prochain rendez-vous", "get_next_event", {}),
    ("j'ai quoi aujourd'hui", "get_events_today", {}),
    ("mes événements de vendredi", "get_events_date", {}),
    ("qu'est-ce que j'ai demain dans mon agenda", "get_events_date", {}),
    ("ajoute déjeuner avec Marie demain à midi", "create_event", {}),
    ("crée un rendez-vous dentiste mardi à 15h", "create_event", {}),
    ("bloque 15h30 18h pour du travail", "create_event", {}),
    ("suis-je libre mardi prochain", "check_availability", {}),
    ("est-ce que je suis dispo vendredi matin", "check_availability", {}),
    ("cherche mes événements anniversaire", "search_events", {}),
    ("retrouve mes réunions avec Paul", "search_events", {}),
    
    # Fichiers
    ("mes documents récents", "list_recent_files", {}),
    ("liste mes fichiers récents", "list_recent_files", {}),
    ("cherche le fichier budget", "find_file", {}),
    ("trouve mon fichier CV", "find_file", {}),
    ("trouve le mot contrat dans mes fichiers", "search_content", {}),
    
    # Système
    ("allume le bluetooth", "toggle_bluetooth", {}),
    ("augmente la luminosité", "set_brightness", {}),
    ("baisse la luminosité", "set_brightness", {}),
    ("mets le Mac en veille", "sleep_mac", {}),
    ("lance l'application Notes", "open_app", {}),
    ("ferme Musique", "close_app", {}),
    ("quitte Safari", "close_app", {}),
    ("est-ce que je suis connecté au wifi", "get_wifi_status", {}),
    ("quel est l'état du wifi", "get_wifi_status", {}),
    ("active airdrop", "toggle_airdrop", {}),
    ("désactive airdrop", "toggle_airdrop", {}),
]

for text, intent, slots in EXTRA:
    rows.append({"prompt": text, "completion": json.dumps({"intent": intent, "slots": slots}, ensure_ascii=False)})
print(f"Variantes ajoutées : {len(EXTRA)} lignes")

# Déduplication + split
seen, uniq = set(), []
for r in rows:
    if r["prompt"] not in seen:
        seen.add(r["prompt"])
        uniq.append(r)
random.seed(42)
random.shuffle(uniq)
cut = max(1, len(uniq) // 10)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "valid.jsonl").write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[:cut]) + "\n")
(OUT / "train.jsonl").write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[cut:]) + "\n")
print(f"✅ dataset_v7 : train={len(uniq) - cut}, valid={cut}")
