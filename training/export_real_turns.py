"""Exporte les vraies phrases loggees (agent.memory) vers JSONL dispatcher.
Labels par regles simples + validation humaine a l'ecran (roadmap P4 :
les corrections manuelles recalibrent le dataset, jamais de label 8B)."""
import json
import sqlite3
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "memory" / "mj.db"
OUT = ROOT / "data" / "dispatcher" / "real_turns.jsonl"

LABELS = [
    ("heure", "get_current_time"),
    ("tour de france", "web_search"),
    ("gagne", "web_search"),
    ("meteo", "get_weather"),
]

def norm(s):
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()

conn = sqlite3.connect(DB)
rows = conn.execute("SELECT user_text FROM turns ORDER BY ts").fetchall()
conn.close()

examples = []
for (text,) in rows:
    low = norm(text)
    intent = next((lab for key, lab in LABELS if key in low), "fallback")
    examples.append({"text": text, "intent": intent, "slots": {}})

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for ex in examples:
        f.write(json.dumps(ex, ensure_ascii=False) + "\n")

print(f"{len(examples)} tours exportes -> {OUT}")
for ex in examples:
    print(f"  {ex['intent']:16s} | {ex['text']}")
