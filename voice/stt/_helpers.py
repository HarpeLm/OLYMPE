import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""
Transcription vocale (STT) — Palier 5

Qwen3-ASR-1.7B via mlx-audio.
Capture l'audio du micro et transcrit en français.

Le modèle est résolu depuis config/models.yaml (jamais codé en dur).
Chargement / déchargement à la demande pour préserver la RAM
(stratégie mémoire roadmap §7 : STT/TTS non résidents).

Usage module :
    from voice.stt import STTEngine
    stt = STTEngine()
    text = stt.transcribe_file("audio.wav")
    text = stt.listen(duration=5.0)

Usage CLI :
    python voice/stt.py --duration 5        # capture 5 secondes
    python voice/stt.py --file audio.wav    # transcrit un fichier
    python voice/stt.py                     # mode continu (Ctrl+C)
"""
import argparse
import queue
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml

ROOT = Path(__file__).resolve().parents[2]
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
