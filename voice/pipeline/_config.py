import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""
Boucle vocale complète MJ — Palier 6

Orchestration : wake word -> bip -> STT -> dispatcheur -> [action | LLM + outils MCP] -> TTS

Stratégie mémoire (décision P5, documentée dans DECISIONS.md) :
  - Résidents permanents : wake word + dispatcheur + STT + TTS
  - LLM via API HTTP vllm-mlx (serveur persistant, cache KV préservé)
  - Tool-calling : vllm-mlx ne fait PAS la boucle (mesuré le 2026-08-27),
    donc la boucle est orchestrée ici ; les outils sont déclarés ET exécutés
    via le serveur MCP (agent/mcp_server.py), source de vérité unique.
"""
import argparse
import asyncio
import json
import queue
import sys
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
import time
import uuid
from pathlib import Path

import numpy as np
import sounddevice as sd
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "models.yaml"
MCP_SERVER_PATH = ROOT / "agent" / "mcp_server.py"
sys.path.insert(0, str(ROOT))

from voice.wake_word import WakeWordEngine
from voice.stt import STTEngine
from voice.tts import TTSEngine
from router.nlu import Dispatcher
from router.prefilter import FAMILIES, repair_calendar_slots, calendar_intent_hint
from agent.memory import Memory

SAMPLE_RATE = 16000
BLOCK_SIZE = 1280

# Construit par concaténation pour éviter tout problème de formatage
THINK_OPEN = "<" + "think>"
THINK_CLOSE = "</" + "think>"

SYSTEM_PROMPT = (
    "Tu es MJ, un assistant vocal local qui tourne sur le Mac de "
    "l'utilisateur. Réponds en français, de façon concise et naturelle, "
    "en une ou deux phrases adaptées à une lecture à voix haute. "
    "Évite les listes, les tableaux et le formatage markdown. "
    "Utilise les outils disponibles quand nécessaire. "
    "MÉMOIRE : si l'utilisateur te demande de te souvenir de quelque chose, "
    "appelle d'abord l'outil remember avec ce fait, puis confirme. "
    "Si on te demande ce dont tu te souviens, appelle recall et réponds "
    "uniquement à partir de son résultat, sans rien inventer."
)




def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_chat_model_name():
    """Lit le modèle chat depuis config/models.yaml (zéro codé en dur)."""
    cfg = load_config()
    chat = cfg.get("roles", {}).get("chat", {})
    name = chat.get("repo") if isinstance(chat, dict) else chat
    if not name:
        raise KeyError("Role 'chat' absent de config/models.yaml")
    return name


def get_server_endpoint():
    cfg = load_config()
    server = cfg.get("server", {})
    host = server.get("host", "127.0.0.1")
    port = server.get("port", 8000)
    return f"http://{host}:{port}"


def beep(duration=0.18, freq=880, sample_rate=24000):
    """Bip de confirmation après détection du wake word."""
    t = np.linspace(0, duration, int(duration * sample_rate), endpoint=False)
    audio = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    sd.play(audio, samplerate=sample_rate)
    sd.wait()