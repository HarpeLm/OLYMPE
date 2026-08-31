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

ROOT = Path(__file__).resolve().parents[1]
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


def get_stt():
    global STT_ENGINE
    if STT_ENGINE is None:
        from voice.stt import STTEngine
        STT_ENGINE = STTEngine()
    return STT_ENGINE


def get_tts():
    global TTS_ENGINE
    if TTS_ENGINE is None:
        from voice.tts import TTSEngine
        TTS_ENGINE = TTSEngine()
    return TTS_ENGINE


def chat_response(text):
    """Orchestre une réponse : TaHoma (déterministe) ou LLM (fallback)."""
    from router.orchestrator import orchestrate
    
    # 1. Dispatcheur + orchestrateur
    result = orchestrate(text)
    
    if result["handled"]:
        # Intent TaHoma reconnue → réponse déterministe
        return result["result"]["message"]
    
    # 2. Fallback vers llama-server
    import requests
    try:
        resp = requests.post(
            "http://127.0.0.1:8000/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "Tu es Olympe, un assistant vocal local. Réponds brièvement et naturellement en français."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            },
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur LLM : {e}"


def speak(text):
    """Synthétise et joue directement avec TTSEngine.speak (voix serena)."""
    tts = get_tts()
    tts.speak(text)
    return "played"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "recording": RECORDER.is_recording()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/record/start":
            self._send(200, {"started": RECORDER.start()})
        
        elif self.path == "/record/stop":
            pcm = RECORDER.stop()
            if pcm is None:
                self._send(400, {"error": "aucun enregistrement"})
            else:
                path, dur = RECORDER.save_wav(pcm)
                t0 = time.time()
                stt = get_stt()
                text = stt.transcribe_file(str(path))
                t1 = time.time()
                self._send(200, {
                    "wav": str(path),
                    "duration": round(dur, 2),
                    "text": text or "",
                    "stt_time": round(t1 - t0, 2)
                })
        
        elif self.path == "/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            try:
                data = json.loads(body) if body else {}
            except:
                data = {}
            text = data.get("text", "")
            if not text:
                self._send(400, {"error": "text manquant"})
            else:
                t0 = time.time()
                response = chat_response(text)
                t1 = time.time()
                self._send(200, {
                    "response": response,
                    "chat_time": round(t1 - t0, 2)
                })
        
        elif self.path == "/speak":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            try:
                data = json.loads(body) if body else {}
            except:
                data = {}
            text = data.get("text", "")
            if not text:
                self._send(400, {"error": "text manquant"})
            else:
                try:
                    wav_path = speak(text)
                    self._send(200, {"wav": wav_path, "played": True})
                except Exception as e:
                    self._send(500, {"error": str(e)})
        
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8001), Handler)
    print(f"✅ bridge v3 sur http://127.0.0.1:8001")
    print("   /record/start, /record/stop, /chat, /speak")
    server.serve_forever()
