"""
Test de latence pour le Palier 2.
Nettoie les blocs de raisonnement pour un affichage propre.
"""
import re
import sys
import time
from pathlib import Path

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"

# Regex pour retirer les blocs de raisonnement (ouverts ou fermés)
THINK_BLOCK = re.compile(r"<\s*think\b.*?(?:<\s*/\s*think\s*>|$)", re.IGNORECASE | re.DOTALL)
ANY_TAG = re.compile(r"<[^>]*>")

SYSTEM_PROMPT = """Tu es MJ, un assistant vocal local qui tourne sur un MacBook Air M5.
Tu réponds en français, de manière concise.
Tes réponses sont destinées à être lues à voix haute.
Tu privilégies des phrases courtes et naturelles."""


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"❌ Config introuvable : {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_for_voice(text):
    """Retire les blocs de raisonnement et les balises résiduelles."""
    if not text:
        return ""
    cleaned = THINK_BLOCK.sub("", text)
    cleaned = ANY_TAG.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def wait_for_server(client, attempts=20):
    for _ in range(attempts):
        try:
            client.models.list()
            return True
        except Exception:
            print("Serveur pas encore prêt, nouvelle tentative...")
            time.sleep(1)
    return False


def measure(client, model, label, messages):
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=256,
        temperature=0.3,
    )
    elapsed = time.perf_counter() - start
    message = response.choices[0].message

    answer = clean_for_voice(message.content or "")
    if not answer:
        answer = clean_for_voice(getattr(message, "reasoning_content", None) or "")
    if not answer:
        answer = "(réponse vide)"

    print(f"\n--- {label} ---")
    print(f"Temps : {elapsed:.2f}s")
    print(f"Réponse (nettoyée) : {answer[:200]}")
    return elapsed


def main():
    cfg = load_config()
    server_cfg = cfg.get("server", {})
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 8000)

    chat_cfg = cfg.get("roles", {}).get("chat") or {}
    model = chat_cfg.get("repo")
    if not model:
        sys.exit("❌ Aucun modèle 'chat' défini dans config/models.yaml")

    client = OpenAI(base_url=f"http://{host}:{port}/v1", api_key="local")

    print(f"Test de latence sur http://{host}:{port}")
    print(f"Modèle : {model}")

    if not wait_for_server(client):
        sys.exit("❌ Le serveur ne répond pas. Lance d'abord : python server/start.py")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Quelle est la capitale de la France ?"},
    ]

    t1 = measure(client, model, "Requête 1 - à froid", messages)
    t2 = measure(client, model, "Requête 2 - même préfixe", messages)
    t3 = measure(client, model, "Requête 3 - même préfixe", messages)
    t4 = measure(client, model, "Requête 4 - même préfixe", messages)

    average_cached = (t2 + t3 + t4) / 3

    print("\n" + "=" * 50)
    print(f"À froid : {t1:.2f}s")
    print(f"Moyenne avec même préfixe : {average_cached:.2f}s")
    if t1 > 0:
        gain = ((t1 - average_cached) / t1) * 100
        print(f"Gain estimé : {gain:.0f}%")


if __name__ == "__main__":
    main()
