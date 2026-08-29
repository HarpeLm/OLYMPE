"""
Détection du mot d'activation — Palier 5

openWakeWord, léger, tourne sur CPU, résident en permanence
(stratégie mémoire roadmap §7 : wake word + dispatcheur résidents,
STT/TTS chargés à la demande).

Le modèle est résolu depuis config/models.yaml (jamais codé en dur).
Actuellement : hey_jarvis (modèle pré-entraîné provisoire).
Plus tard : olympe (modèle entraîné via pipeline officiel openWakeWord).

Usage module :
    from voice.wake_word import WakeWordEngine
    ww = WakeWordEngine()
    ww.listen_forever(callback=lambda score: print("Wake !"))

Usage CLI :
    python voice/wake_word.py
"""
import sys
import queue
import argparse
from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml
from openwakeword.model import Model

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"

SAMPLE_RATE = 16000
BLOCK_SIZE = 1280  # 80 ms à 16 kHz, taille standard openWakeWord


def get_wake_config():
    """Lit la config du wake word depuis config/models.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    roles = config.get("roles", {})
    entry = roles.get("wake_word")
    if entry is None:
        raise KeyError("Role 'wake_word' absent de config/models.yaml")
    return entry


class WakeWordEngine:
    """Moteur de détection du mot d'activation."""

    def __init__(self):
        cfg = get_wake_config()
        self.model_name = cfg.get("model", "hey_jarvis")
        self.threshold = cfg.get("threshold", 0.5)
        self.model = Model(
            wakeword_models=[self.model_name],
            inference_framework=cfg.get("inference_framework", "onnx"),
        )
        print(f"[WAKE] Modèle chargé : {self.model_name} "
              f"(seuil {self.threshold})")

    def reset(self):
        self.model.reset()

    def process_block(self, block):
        """Retourne le score de détection pour un bloc audio."""
        prediction = self.model.predict(block)
        return prediction[self.model_name]

    def listen_forever(self, callback):
        """
        Écoute le micro en continu et appelle callback(score) à chaque
        détection dépassant le seuil. Bloquant.
        """
        audio_queue = queue.Queue()

        def callback_audio(indata, frames, time_info, status):
            if status:
                print(f"[WAKE][Warning] {status}", file=sys.stderr)
            audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=BLOCK_SIZE,
            callback=callback_audio,
        ):
            print(f"[WAKE] En écoute — dis le mot d'activation. "
                  f"Ctrl+C pour quitter.")
            while True:
                block = audio_queue.get()
                score = self.process_block(block.squeeze())
                if score > self.threshold:
                    callback(score)
                    self.model.reset()


def main():
    parser = argparse.ArgumentParser(
        description="Test du wake word OLYMPE")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Seuil de détection (défaut : valeur config)")
    args = parser.parse_args()

    engine = WakeWordEngine()
    if args.threshold is not None:
        engine.threshold = args.threshold

    def on_wake(score):
        print(f"[WAKE DÉTECTÉ] score = {score:.2f}")

    try:
        engine.listen_forever(callback=on_wake)
    except KeyboardInterrupt:
        print("\nArrêt.")


if __name__ == "__main__":
    main()
