import json, sys
import yaml
from pathlib import Path
from mlx_lm import load, generate

CASES = [
    ("quelle heure est-il", "fallback"),
    ("on est quel jour aujourd'hui", "fallback"),
    ("quel temps fait-il à Paris", "get_weather"),
    ("mets un minuteur de 10 minutes", "fallback"),
    ("lance ma playlist détente", "play_music"),
    ("pause la musique", "pause_music"),
    ("qu'est-ce qui suit dans mon planning", "get_next_event"),
    ("mes documents récents", "list_recent_files"),
    ("allume le bluetooth", "toggle_bluetooth"),
    ("fais une capture d'écran", "take_screenshot"),
    ("ouvre le dossier téléchargements", "open_folder"),
    ("explique-moi comment fonctionne un trou noir", "fallback"),
    ("raconte-moi une blague", "fallback"),
    ("qui était Ada Lovelace", "fallback"),
    ("combien d'étapes a gagné Tadej Pogačar sur le Tour de France", "fallback"),
]

det = {i["name"] for i in yaml.safe_load(
    open("router/intents.yaml"))["deterministic_intents"]}

base = sys.argv[1] if len(sys.argv) > 1 else "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
adapter = sys.argv[2] if len(sys.argv) > 2 else "training/adapters/dispatcher-v6"
model, tok = load(base, adapter_path=adapter)

ok = 0
for phrase, expected in CASES:
    prompt = tok.apply_chat_template(
        [{"role": "user", "content": phrase}],
        add_generation_prompt=True, tokenize=False)
    raw = generate(model, tok, prompt=prompt, max_tokens=64, verbose=False)
    try:
        intent = json.loads(raw).get("intent")
    except Exception:
        intent = None
    got_fb = intent == "general_question" or intent not in det
    good = (expected == "fallback" and got_fb) or (expected == intent)
    ok += good
    print(f"{'✅' if good else '❌'} {phrase} -> {intent} (attendu {expected})")
print(f"\nScore v6 : {ok}/{len(CASES)}")
