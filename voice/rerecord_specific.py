"""
Réenregistrement ciblé de fichiers spécifiques.
Usage : python voice/rerecord_specific.py
"""
import sounddevice as sd
import numpy as np
import wave
from pathlib import Path

SAMPLE_RATE = 16000
DURATION = 1.5
POSITIVE_DIR = Path("voice/wake_samples")
RMS_THRESHOLD = 300

# Fichiers à réenregistrer
TARGET_FILES = ["olympe_06.wav", "olympe_07.wav", "olympe_08.wav", "olympe_15.wav"]


def record_one(duration=DURATION):
    """Enregistre un clip audio et retourne le tableau numpy."""
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype='int16'
    )
    sd.wait()
    return audio


def save_wav(filepath, audio):
    """Sauvegarde un tableau numpy en WAV 16-bit mono."""
    with wave.open(str(filepath), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())


def main():
    print("=" * 60)
    print("Réenregistrement ciblé : fichiers 6, 7, 8, 15")
    print("=" * 60)
    print("\nConseils :")
    print("  - Parle à 15-20 cm du micro")
    print("  - Prononce 'MJ' clairement, voix posée")
    print("  - Chaque prise est vérifiée : si trop faible, on recommence")
    print("-" * 60)
    input("\nAppuie sur Entrée pour commencer (Ctrl+C pour annuler)...")

    for i, filename in enumerate(TARGET_FILES, 1):
        filepath = POSITIVE_DIR / filename
        print(f"\n[{i}/{len(TARGET_FILES)}] Réenregistrement de {filename}")

        attempt = 0
        max_attempts = 3

        while attempt < max_attempts:
            attempt += 1
            print(f"  Prise {attempt}/{max_attempts} — Prononce 'MJ' dans 1 seconde...")
            sd.sleep(1000)

            audio = record_one()
            rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))

            print(f"  RMS mesuré : {rms:.0f}", end="")

            if rms >= RMS_THRESHOLD:
                save_wav(filepath, audio)
                print(" — Sauvegardé")
                break
            else:
                print(" — Trop faible, on recommence")

        else:
            print(f"  ÉCHEC après {max_attempts} tentatives. "
                  f"Fichier conservé tel quel : {filename}")

    # Bilan final
    print("\n" + "=" * 60)
    print("Bilan après réenregistrement")
    print("=" * 60)
    
    for filename in TARGET_FILES:
        filepath = POSITIVE_DIR / filename
        with wave.open(str(filepath), 'rb') as wf:
            audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
        statut = "OK" if rms >= RMS_THRESHOLD else "ENCORE FAIBLE"
        print(f"  {filename} : RMS={rms:.0f} — {statut}")


if __name__ == "__main__":
    main()
