import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""
Synthèse vocale (TTS) — Palier 5

Qwen3-TTS CustomVoice via mlx-audio.
Deux modes :
  1. Voix prédéfinie (voice="serena") — pour démarrer sans enregistrement
  2. Clonage zero-shot (ref_audio="chemin.wav" + ref_text) — pour la voix de la copine

Le modèle ET ses options (voix par défaut, langue, sample rate) sont résolus
depuis config/models.yaml (jamais codés en dur).
Chargement / déchargement à la demande pour préserver la RAM
(stratégie mémoire roadmap §7 : wake word + dispatcheur résidents,
STT/TTS chargés autour de chaque interaction).

Usage module :
    from voice.tts import TTSEngine
    tts = TTSEngine()
    tts.speak("Bonjour, je suis Olympe.")

Usage CLI :
    python voice/tts.py "Bonjour" --voice serena
    python voice/tts.py "Bonjour" --output /tmp/test.wav
    python voice/tts.py "Bonjour" --ref-audio /path/voix.wav --ref-text "texte exact"
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"




def get_role_entry(role):
    """Retourne l'entrée complète d'un rôle depuis config/models.yaml."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    roles = config.get("roles", {})
    entry = roles.get(role)
    if entry is None:
        raise KeyError(f"Role '{role}' absent ou non configure dans {CONFIG_PATH}")
    return entry


def get_model_id(role):
    """Résout l'identifiant HF du modèle pour un rôle depuis la config."""
    entry = get_role_entry(role)
    return entry["repo"] if isinstance(entry, dict) else entry


def save_wav(path, audio, sample_rate):
    """Sauvegarde en WAV 16-bit via la lib standard (pas de dépendance)."""
    import wave
    audio_int16 = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio_int16 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
