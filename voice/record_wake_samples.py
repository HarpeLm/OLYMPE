"""
Enregistrement d'échantillons pour entraîner le wake word "MJ"
Usage : python voice/record_wake_samples.py
"""
import sounddevice as sd
import numpy as np
import wave
from pathlib import Path
import time

SAMPLE_RATE = 16000
DURATION = 1.5  # secondes
OUTPUT_DIR = Path("voice/wake_samples")

OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Enregistrement d'échantillons pour le wake word 'MJ'")
print("=" * 60)
print(f"\nTu vas enregistrer 15 échantillons de 1.5 secondes.")
print("À chaque signal, prononce 'MJ' clairement.")
print("Varie légèrement l'intonation et la vitesse entre chaque essai.")
print("\nAppuie sur Entrée pour commencer, ou Ctrl+C pour annuler.\n")

try:
    input()
except KeyboardInterrupt:
    print("\nAnnulé.")
    exit(0)

for i in range(15):
    print(f"\n[{i+1}/15] Prépare-toi...")
    time.sleep(1)
    print("🎤 PARLE MAINTENANT : 'MJ'")
    
    # Enregistrement
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    
    # Sauvegarde
    filename = OUTPUT_DIR / f"olympe_{i+1:02d}.wav"
    with wave.open(str(filename), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    
    print(f"✓ Sauvegardé : {filename}")
    
    if i < 14:
        time.sleep(0.5)

print("\n" + "=" * 60)
print("Enregistrement terminé !")
print(f"Échantillons dans : {OUTPUT_DIR}")
print("=" * 60)
