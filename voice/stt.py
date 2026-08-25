"""
Transcription vocale en continu — Palier 5

Capture l'audio du micro et transcrit par segments de 3 secondes.
Utilise Whisper large-v3-turbo via mlx-audio.

Usage :
    python voice/stt.py              # transcription en continu (Ctrl+C pour quitter)
    python voice/stt.py --duration 5 # capturer 5 secondes puis transcrire
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
        """Callback appelé par sounddevice pour chaque chunk audio."""
        if status:
            print(f"[Warning] {status}", file=sys.stderr)
        self.audio_queue.put(indata.copy())
    
    def start(self):
        """Démarre l'enregistrement en continu."""
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.callback,
            blocksize=int(self.sample_rate * 0.1),  # 100ms chunks
        )
        self.stream.start()
    
    def stop(self):
        """Arrête l'enregistrement."""
        self.recording = False
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
    
    def get_audio(self, duration_seconds):
        """Récupère `duration_seconds` d'audio depuis le buffer."""
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
    """Transcrit un chunk audio avec Whisper."""
    if audio is None or len(audio) < sample_rate * 0.5:
        return None
    
    # Normaliser en float32 [-1, 1]
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    
    # Transcrire
    result = model.generate(audio, language="fr", temperature=0.0)
    return result.text.strip()


def main():
    parser = argparse.ArgumentParser(description="Transcription vocale en continu")
    parser.add_argument("--duration", type=float, help="Durée de capture en secondes (mode one-shot)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo",
                        help="Modèle Whisper à utiliser")
    args = parser.parse_args()
    
    print(f"Chargement du modèle : {args.model}")
    model = load(args.model)  # Utilise load au lieu de load_model
    print("Modèle chargé.")
    
    recorder = AudioRecorder(sample_rate=16000)
    
    if args.duration:
        # Mode one-shot : capturer N secondes puis transcrire
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
        # Mode continu : transcrire par segments de 3 secondes
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
