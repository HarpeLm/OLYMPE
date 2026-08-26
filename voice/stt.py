"""
Transcription vocale — Palier 5

Capture l'audio du micro et transcrit avec Qwen3-ASR-1.7B via mlx-audio.

Usage :
    python voice/stt.py --duration 5   # mode one-shot, 5 secondes
    python voice/stt.py                # mode continu (Ctrl+C pour quitter)
"""
import argparse
import queue
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from mlx_audio.stt import load

ROOT = Path(__file__).resolve().parent.parent


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


def transcribe_chunk(model, audio, sample_rate=16000):
    if audio is None or len(audio) < sample_rate * 0.5:
        return None

    # Normaliser en float32 [-1, 1] si nécessaire
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    # Qwen3-ASR utilise une API différente de Whisper
    try:
        result = model.transcribe(audio, language="fr")
        return result.get("text", "").strip()
    except AttributeError:
        # Fallback si transcribe n'existe pas
        try:
            result = model.generate(audio, language="fr")
            if hasattr(result, "text"):
                return result.text.strip()
            elif isinstance(result, dict):
                return result.get("text", "").strip()
            else:
                return str(result).strip()
        except Exception as e:
            print(f"Erreur transcription: {e}", file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(description="Transcription vocale")
    parser.add_argument("--duration", type=float,
                        help="Durée de capture en secondes (mode one-shot)")
    parser.add_argument("--model",
                        default="mlx-community/Qwen3-ASR-1.7B-4bit",
                        help="Modèle ASR à utiliser")
    args = parser.parse_args()

    print(f"Chargement du modèle : {args.model}")
    model = load(args.model)
    print("Modèle chargé.")

    recorder = AudioRecorder(sample_rate=16000)

    if args.duration:
        print(f"Capture de {args.duration} secondes...")
        recorder.start()
        time.sleep(args.duration)
        recorder.stop()

        audio = recorder.get_audio(args.duration)
        if audio is not None:
            text = transcribe_chunk(model, audio)
            if text:
                print(f"Transcription : {text}")
            else:
                print("(silence ou bruit)")
        else:
            print("Erreur : aucun audio capturé")
    else:
        print("Transcription en continu (Ctrl+C pour quitter)")
        print("-" * 60)

        recorder.start()
        chunk_duration = 3.0

        try:
            while True:
                audio = recorder.get_audio(chunk_duration)
                if audio is not None:
                    text = transcribe_chunk(model, audio)
                    if text:
                        print(f"[{time.strftime('%H:%M:%S')}] {text}")
        except KeyboardInterrupt:
            print("\nArrêt.")
        finally:
            recorder.stop()


if __name__ == "__main__":
    main()
