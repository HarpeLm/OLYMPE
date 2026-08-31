import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""Pont HTTP local entre l'app Tauri et la voix — Palier 5/7.
v3 : enregistrement + STT + orchestrateur + TTS.
Boucle complète : tu parles → transcription → orchestration → réponse vocale."""
import json
import sys
import threading
import time
import wave
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUDIO_DIR = ROOT / "data" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT))

CFG = yaml.safe_load((ROOT / "config" / "models.yaml").read_text())
SAMPLE_RATE = int(CFG["roles"]["stt"].get("sample_rate", 16000))




class Recorder:
    """Enregistrement micro en tâche de fond (16 kHz mono int16)."""

    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self._stream = None
        self._frames = []
        self._lock = threading.Lock()

    def is_recording(self):
        return self._stream is not None

    def start(self):
        with self._lock:
            if self._stream is not None:
                return False
            import sounddevice as sd
            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate, channels=1,
                dtype="int16", callback=self._callback)
            self._stream.start()
            return True

    def _callback(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def stop(self):
        with self._lock:
            if self._stream is None:
                return None
            self._stream.stop()
            self._stream.close()
            self._stream = None
            import numpy as np
            if not self._frames:
                return None
            return np.concatenate(self._frames).flatten()

    def save_wav(self, pcm):
        path = AUDIO_DIR / "last_question.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm.tobytes())
        return path, len(pcm) / self.sample_rate


RECORDER = Recorder(SAMPLE_RATE)
STT_ENGINE = None
TTS_ENGINE = None
