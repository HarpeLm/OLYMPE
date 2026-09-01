"""Test voix de bout en bout : parle -> STT -> orchestre -> TTS.
8 s d'enregistrement automatique, puis MJ répond à voix haute."""
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


print("Enregistrement... PARLE MAINTENANT (8 s)")
post("/record/start")
time.sleep(8)
stop = post("/record/stop")
print("Transcription :", stop.get("text"))

chat = post("/chat", {"text": stop.get("text", "")})
print("Réponse       :", chat.get("response"))

print("Synthèse + lecture (1er appel lent : chargement TTS)...")
print(post("/speak", {"text": chat.get("response", "")}))
print("✅ Si tu as entendu la voix : boucle complète validée")
