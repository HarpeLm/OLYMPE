"""
Boucle vocale complète OLYMPE — Palier 5

Orchestre : wake word -> bip -> STT -> dispatcheur -> [action | LLM] -> TTS

Stratégie mémoire (roadmap §7, adaptée après mesure) :
  - Résidents permanents : wake word + dispatcheur + STT + TTS
  - Raison : le chargement STT/TTS prend plusieurs secondes (mesuré),
    pas "quelques centaines de ms" comme supposé. Les garder résidents
    élimine et la latence par cycle et le bug de timing au démarrage.
  - Budget : ~5 Go pipeline + ~5 Go serveur LLM = ~10 Go sur 16.

Le modèle LLM de fallback et l'URL du serveur sont lus depuis
config/models.yaml (jamais codés en dur).

Usage :
    python voice/pipeline.py
    python voice/pipeline.py --listen-duration 6
"""
import argparse
import queue
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"
sys.path.insert(0, str(ROOT))

from voice.wake_word import WakeWordEngine
from voice.stt import STTEngine
from voice.tts import TTSEngine
from router.dispatcher import Dispatcher


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_server_endpoint():
    """Retourne (url_base, nom_modele_chat) depuis la config."""
    config = load_config()
    server = config.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", 8000)
    chat_entry = config.get("roles", {}).get("chat", {})
    model_name = chat_entry.get("repo") if isinstance(chat_entry, dict) else chat_entry
    return f"http://{host}:{port}", model_name


# ---------------------------------------------------------------------------
# Bip de confirmation
# ---------------------------------------------------------------------------

def beep(duration=0.18, freq=880, sample_rate=24000):
    """Petit bip de confirmation après détection du wake word."""
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    audio = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


# ---------------------------------------------------------------------------
# LLM de fallback (appel HTTP au serveur vllm-mlx)
# ---------------------------------------------------------------------------

def strip_think_tags(text):
    """Nettoie d'éventuelles balises de raisonnement résiduelles."""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def get_llm_response(text):
    """Appelle le serveur LLM de fallback et retourne la réponse texte."""
    try:
        import requests
    except ImportError:
        return "Le module requests n'est pas installé, impossible d'appeler le LLM."

    base_url, model_name = get_server_endpoint()

    system_prompt = (
        "Tu es OLYMPE, un assistant vocal local qui tourne sur le Mac de "
        "l'utilisateur. Réponds en français, de façon concise et naturelle, "
        "en une ou deux phrases adaptées à une lecture à voix haute. "
        "Évite les listes, les tableaux et le formatage markdown."
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }

    try:
        resp = requests.post(
            f"{base_url}/v1/chat/completions",
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return strip_think_tags(content)
    except Exception as e:
        return f"Désolé, je n'ai pas pu contacter mon cerveau principal : {e}"


# ---------------------------------------------------------------------------
# Actions déterministes (Palier 7 à venir)
# ---------------------------------------------------------------------------

def try_execute_handler(result):
    """
    Tente d'exécuter le handler déterministe s'il existe.
    Retourne la réponse texte, ou None si le handler n'est pas disponible.
    """
    handler = result.get("handler")
    if not handler or "::" not in handler:
        return None

    path_str, func_name = handler.split("::", 1)
    path = ROOT / path_str
    if not path.exists():
        return None

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("handler_module", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func = getattr(module, func_name)
        return str(func(**result.get("slots", {})))
    except Exception as e:
        print(f"[PIPELINE] Handler non exécutable ({handler}) : {e}")
        return None


def deterministic_response(result):
    """Réponse locale pour une action déterministe non implémentée."""
    intent = result.get("intent", "action")
    pretty = intent.replace("_", " ")
    return (
        f"J'ai bien compris, tu veux : {pretty}. "
        f"Cette action sera disponible au Palier 7."
    )


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

class VoicePipeline:
    def __init__(self, listen_duration=5.0):
        self.listen_duration = listen_duration

        print("[PIPELINE] Initialisation des composants résidents...")
        self.wake = WakeWordEngine()
        self.dispatcher = Dispatcher()
        self.stt = STTEngine()
        self.tts = TTSEngine()

        print("[PIPELINE] Préchargement STT + TTS (une fois)...")
        self.stt.load()
        self.tts.load()
        print("[PIPELINE] Prêt.")

    def wait_for_wake(self):
        """Bloque jusqu'à détection du wake word. Retourne le score."""
        audio_queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                print(f"[PIPELINE][Warning] {status}", file=sys.stderr)
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="int16",
            blocksize=1280,
            callback=callback,
        ):
            while True:
                block = audio_queue.get()
                score = self.wake.process_block(block.squeeze())
                if score > self.wake.threshold:
                    self.wake.reset()
                    return score

    def listen_command(self):
        """Enregistre et transcrit. Le STT est déjà chargé (résident)."""
        print(f"[PIPELINE] Parle maintenant ({self.listen_duration}s)...")
        return self.stt.listen(duration=self.listen_duration)

    def speak(self, text):
        """Synthétise et joue. Le TTS est déjà chargé (résident)."""
        if text:
            self.tts.speak(text)

    def handle_command(self, text):
        """Route la commande : déterministe ou fallback LLM."""
        result = self.dispatcher.route(text)
        intent = result.get("intent")
        action = result.get("action")
        confidence = result.get("confidence")
        print(f"[PIPELINE] Intent={intent} | action={action} | confiance={confidence}")

        if action == "deterministic":
            response = try_execute_handler(result)
            if response is None:
                response = deterministic_response(result)
        else:
            print("[PIPELINE] Fallback vers le LLM principal...")
            response = get_llm_response(text)

        return response

    def run(self):
        print("\n" + "=" * 60)
        print("BOUCLE VOCALE OLYMPE")
        print("Dis le mot d'activation, puis ta commande après le bip.")
        print("Ctrl+C pour quitter.")
        print("=" * 60 + "\n")

        try:
            while True:
                score = self.wait_for_wake()
                print(f"\n[PIPELINE] Wake word détecté (score={score:.2f})")

                # Le STT est déjà chargé : le bip sonne quand on est
                # réellement prêt, et l'enregistrement démarre aussitôt.
                beep()
                time.sleep(0.3)

                text = self.listen_command()
                if not text:
                    print("[PIPELINE] Aucune commande entendue.")
                    self.speak("Je n'ai rien entendu, redis-moi.")
                    continue

                print(f"[PIPELINE] Commande : {text}")
                response = self.handle_command(text)
                print(f"[PIPELINE] Réponse : {response}")
                self.speak(response)

        except KeyboardInterrupt:
            print("\n[PIPELINE] Arrêt.")


def main():
    parser = argparse.ArgumentParser(description="Boucle vocale OLYMPE")
    parser.add_argument("--listen-duration", type=float, default=5.0,
                        help="Durée d'écoute après le wake word (défaut 5s)")
    args = parser.parse_args()

    pipeline = VoicePipeline(listen_duration=args.listen_duration)
    pipeline.run()


if __name__ == "__main__":
    main()
