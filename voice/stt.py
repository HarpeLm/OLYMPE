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


class AudioRecorder:
    """Enregistreur audio avec buffer circulaire."""

    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.recording = False

    def callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Warning] {status}", file=sys.stderr)
        self.audio_queue.put(indata.copy())

    def start(self):
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.callback,
            blocksize=int(self.sample_rate * 0.1),
        )
        self.stream.start()

    def stop(self):
        self.recording = False
        if hasattr(self, "stream"):
            self.stream.stop()
            self.stream.close()

    def get_audio(self, duration_seconds):
        """Récupère l'audio accumulé pour une durée donnée."""
        num_frames = int(duration_seconds * self.sample_rate)
        audio_chunks = []
        frames_collected = 0

        while frames_collected < num_frames:
            try:
                chunk = self.audio_queue.get(timeout=1.0)
                audio_chunks.append(chunk)
                frames_collected += len(chunk)
            except queue.Empty:
                if not self.recording:
                    break

        if not audio_chunks:
            return None

        audio = np.concatenate(audio_chunks, axis=0)
        if len(audio) > num_frames:
            audio = audio[:num_frames]

        return audio.squeeze()


class STTEngine:
    """Moteur STT Qwen3-ASR avec chargement / déchargement à la demande."""

    def __init__(self, model_id=None):
        entry = get_role_entry("stt")
        if isinstance(entry, dict):
            self.model_id = model_id or entry["repo"]
            self.lang = entry.get("lang", "French")
            self.sample_rate = entry.get("sample_rate", 16000)
            self.hotwords = entry.get("hotwords", [])
        else:
            self.model_id = model_id or entry
            self.lang = "French"
            self.sample_rate = 16000
            self.hotwords = []
        self.model = None
        self.recorder = AudioRecorder(sample_rate=self.sample_rate)

    def load(self):
        if self.model is not None:
            return
        from mlx_audio.stt import load_model
        print(f"[STT] Chargement : {self.model_id}")
        self.model = load_model(self.model_id)
        print("[STT] Modele charge.")

    def unload(self):
        self.model = None
        try:
            import mlx.core as mx
            mx.clear_cache()
        except Exception:
            pass
        print("[STT] Modele decharge.")

    def transcribe_audio(self, audio):
        """
        Transcrit un tableau numpy float32 (16 kHz, mono).

        Args:
            audio: np.ndarray float32, valeurs dans [-1, 1]

        Returns:
            str: texte transcrit, ou None si silence/bruit
        """
        if self.model is None:
            self.load()

        if audio is None or len(audio) < self.sample_rate * 0.5:
            return None

        # Normaliser en float32 si nécessaire
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        kwargs = {
            "language": self.lang,
            "temperature": 0.0,
            "verbose": False,
        }
        if self.hotwords:
            kwargs["hotwords"] = self.hotwords

        result = self.model.generate(audio, **kwargs)

        # STTOutput a un attribut .text
        if hasattr(result, "text"):
            text = result.text.strip()
        elif isinstance(result, str):
            text = result.strip()
        else:
            text = str(result).strip()

        return text if text else None

    def transcribe_file(self, filepath):
        """Transcrit un fichier audio (WAV, MP3, etc.)."""
        if self.model is None:
            self.load()

        kwargs = {
            "language": self.lang,
            "temperature": 0.0,
            "verbose": False,
        }
        if self.hotwords:
            kwargs["hotwords"] = self.hotwords

        # Qwen3-ASR accepte directement un chemin fichier
        result = self.model.generate(str(filepath), **kwargs)

        if hasattr(result, "text"):
            return result.text.strip()
        elif isinstance(result, str):
            return result.strip()
        else:
            return str(result).strip()

    def listen(self, duration=5.0):
        """
        Capture l'audio du micro pendant `duration` secondes et transcrit.

        Returns:
            str: texte transcrit, ou None
        """
        print(f"[STT] Ecoute pendant {duration}s...")
        self.recorder.start()
        time.sleep(duration)
        self.recorder.stop()

        audio = self.recorder.get_audio(duration)
        if audio is None:
            print("[STT] Aucun audio capture.")
            return None

        return self.transcribe_audio(audio)

    def listen_continuous(self, chunk_duration=3.0):
        """
        Mode continu : transcrit par segments. Générateur.

        Yields:
            tuple: (timestamp, texte transcrit)
        """
        self.recorder.start()
        try:
            while True:
                audio = self.recorder.get_audio(chunk_duration)
                if audio is not None:
                    text = self.transcribe_audio(audio)
                    if text:
                        yield (time.strftime("%H:%M:%S"), text)
        finally:
            self.recorder.stop()


def main():
    parser = argparse.ArgumentParser(description="Transcription vocale OLYMPE")
    parser.add_argument("--duration", type=float,
                        help="Duree de capture en secondes (mode one-shot)")
    parser.add_argument("--file", "-f", help="Fichier audio a transcrire")
    parser.add_argument("--continuous", action="store_true",
                        help="Mode continu (Ctrl+C pour quitter)")
    parser.add_argument("--chunk", type=float, default=3.0,
                        help="Duree des segments en mode continu (defaut: 3s)")
    args = parser.parse_args()

    stt = STTEngine()
    stt.load()

    if args.file:
        # Mode fichier
        text = stt.transcribe_file(args.file)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(aucune transcription)")

    elif args.duration:
        # Mode one-shot
        text = stt.listen(duration=args.duration)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(silence ou bruit)")

    elif args.continuous:
        # Mode continu
        print("Transcription en continu (Ctrl+C pour quitter)")
        print("-" * 60)
        try:
            for timestamp, text in stt.listen_continuous(chunk_duration=args.chunk):
                print(f"[{timestamp}] {text}")
        except KeyboardInterrupt:
            print("\nArret.")

    else:
        # Par défaut : mode one-shot 5 secondes
        text = stt.listen(duration=5.0)
        if text:
            print(f"Transcription : {text}")
        else:
            print("(silence ou bruit)")

    stt.unload()


if __name__ == "__main__":
    main()
