import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "dispatcher" / "dataset_v8"
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

# 2. Ajouter les échecs corrigés
if FAILURES.exists():
    for line in FAILURES.read_text().splitlines():
        try:
            f = json.loads(line)
            text, expected = f.get("text", "").strip(), f.get("expected", "")
            if text and expected:
                rows.append({"prompt": text, "completion": json.dumps({"intent": expected, "slots": {}}, ensure_ascii=False)})
        except json.JSONDecodeError:
            pass

# 3. Équilibrer : limiter play_music à 20 exemples max
play_music_count = sum(1 for r in rows if '"intent": "play_music"' in r.get("completion", ""))
if play_music_count > 20:
    rows = [r for r in rows if '"intent": "play_music"' not in r.get("completion", "")][:20] + \
           [r for r in rows if '"intent": "play_music"' not in r.get("completion", "")]
    print(f"play_music limité à 20 exemples (était {play_music_count})")

# 4. Ajouter des négatifs explicites (phrases qui NE SONT PAS play_music)
NEGATIVES = [
    ("qui était Ada Lovelace", "general_question"),
    ("explique-moi comment fonctionne un trou noir", "general_question"),
    ("raconte-moi une blague", "general_question"),
    ("pourquoi le ciel est bleu", "general_question"),
    ("15 pour cent de 80 ça fait combien", "general_question"),
    ("combien font 17 fois 23", "general_question"),
    ("qu'est-ce qui suit dans mon planning", "get_next_event"),
    ("mon prochain rendez-vous", "get_next_event"),
    ("j'ai quoi aujourd'hui", "get_events_today"),
    ("ajoute déjeuner avec Marie demain à midi", "create_event"),
    ("crée un rendez-vous dentiste mardi à 15h", "create_event"),
    ("suis-je libre mardi prochain", "check_availability"),
    ("reprends la musique", "resume_music"),
    ("chanson suivante", "next_track"),
    ("piste précédente", "previous_track"),
    ("c'est quoi cette chanson", "get_now_playing"),
    ("arrête la musique dans 20 minutes", "sleep_timer"),
    ("allume le bluetooth", "toggle_bluetooth"),
    ("augmente la luminosité", "set_brightness"),
    ("lance l'application Notes", "open_app"),
    ("ferme Musique", "close_app"),
    ("active airdrop", "toggle_airdrop"),
]
for text, intent in NEGATIVES:
    rows.append({"prompt": text, "completion": json.dumps({"intent": intent, "slots": {}}, ensure_ascii=False)})
print(f"Négatifs ajoutés : {len(NEGATIVES)} lignes")

# Dédup + split
seen, uniq = set(), []
for r in rows:
    if r["prompt"] not in seen:
        seen.add(r["prompt"])
        uniq.append(r)
random.seed(42)
random.shuffle(uniq)
cut = max(1, len(uniq) // 10)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "valid.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[:cut]) + "\n")
(OUT / "train.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in uniq[cut:]) + "\n")
print(f"✅ dataset_v8 : train={len(uniq) - cut}, valid={cut}")
