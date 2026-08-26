import sounddevice as sd
import numpy as np
import wave
from pathlib import Path
import time

SAMPLE_RATE = 16000
DURATION = 1.5
RMS_THRESHOLD = 300
TARGET = Path("voice/wake_samples/olympe_09.wav")

print("=" * 60)
print("Réenregistrement ciblé : olympe_09.wav")
print("=" * 60)
print("\nConseils :")
print("  - Parle à 15-20 cm du micro")
print("  - Prononce 'Olympe' clairement, voix posée")
print("  - Chaque prise est vérifiée : si trop faible, on recommence")
print("-" * 60)
print("\nDémarrage dans 3 secondes...")
time.sleep(3)

attempt = 0
max_attempts = 3

while attempt < max_attempts:
    attempt += 1
    print(f"\nPrise {attempt}/{max_attempts} — Prononce 'Olympe' dans 1 seconde...")
    time.sleep(1)

    audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                   channels=1, dtype='int16')
    sd.wait()

    rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
    print(f"  RMS mesuré : {rms:.0f}", end="")

    if rms >= RMS_THRESHOLD:
        with wave.open(str(TARGET), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        print(" — Sauvegardé")
        break
    else:
        print(" — Trop faible, on recommence")

else:
    print(f"\nÉCHEC après {max_attempts} tentatives. Fichier non modifié.")

# Bilan
with wave.open(str(TARGET), 'rb') as wf:
    final_audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
final_rms = np.sqrt(np.mean(final_audio.astype(np.float32) ** 2))
print(f"\nRMS final de {TARGET.name} : {final_rms:.0f}")
print(f"Statut : {'OK' if final_rms >= RMS_THRESHOLD else 'ENCORE FAIBLE'}")
