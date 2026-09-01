"""
Réenregistrement ciblé des échantillons wake word trop faibles ou silencieux.
Identifie automatiquement les fichiers avec RMS < 300 et les réenregistre.
Usage : python voice/rerecord_weak_samples.py
"""
import sounddevice as sd
import numpy as np
import wave
from pathlib import Path

SAMPLE_RATE = 16000
DURATION = 1.5
POSITIVE_DIR = Path("voice/wake_samples")
RMS_THRESHOLD = 300  # Seuil minimal pour un bon échantillon


def get_rms(filepath):
    """Calcule le RMS d'un fichier WAV."""
    with wave.open(str(filepath), 'rb') as wf:
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    return np.sqrt(np.mean(audio.astype(np.float32) ** 2))


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
    # 1. Identifier les fichiers faibles
    weak_files = []
    for f in sorted(POSITIVE_DIR.glob("olympe_*.wav")):
        rms = get_rms(f)
        if rms < RMS_THRESHOLD:
            weak_files.append((f, rms))

    if not weak_files:
        print("Tous les échantillons sont de bonne qualité. Rien à réenregistrer.")
        return

    print("=" * 60)
    print("Réenregistrement ciblé des échantillons faibles")
    print("=" * 60)
    print(f"\n{len(weak_files)} fichiers à réenregistrer :")
    for f, rms in weak_files:
        statut = "SILENCIEUX" if rms < 100 else "TROP FAIBLE"
        print(f"  {f.name} (RMS={rms:.0f}, {statut})")

    print("\n" + "-" * 60)
    print("Conseils pour un bon niveau :")
    print("  - Parle à 15-20 cm du micro, pas plus loin")
    print("  - Prononce 'MJ' d'une voix claire et posée")
    print("  - Évite les bruits de fond (ventilo, musique, rue)")
    print("  - Chaque prise est vérifiée : si trop faible, on recommence")
    print("-" * 60)
    input("\nAppuie sur Entrée pour commencer (Ctrl+C pour annuler)...")

    # 2. Réenregistrer chaque fichier faible
    for i, (filepath, old_rms) in enumerate(weak_files, 1):
        print(f"\n[{i}/{len(weak_files)}] Réenregistrement de {filepath.name}")
        print(f"  (ancien RMS : {old_rms:.0f})")

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
                  f"Fichier conservé tel quel : {filepath.name}")

    # 3. Bilan final
    print("\n" + "=" * 60)
    print("Bilan après réenregistrement")
    print("=" * 60)
    good = 0
    for f in sorted(POSITIVE_DIR.glob("olympe_*.wav")):
        rms = get_rms(f)
        if rms >= RMS_THRESHOLD:
            good += 1
            print(f"  {f.name} : RMS={rms:.0f}")
        else:
            print(f"  {f.name} : RMS={rms:.0f} — ENCORE FAIBLE")

    print(f"\n{good}/15 échantillons utilisables")
    if good >= 10:
        print("L'entraînement peut être lancé.")
    else:
        print("Encore trop peu. Réenregistre les fichiers restants.")


if __name__ == "__main__":
    main()
