import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from http.server import BaseHTTPRequestHandler
from server.bridge._recorder import *
from server.bridge._engines import get_stt, get_tts, chat_response, speak


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
